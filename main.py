import asyncio
import calendar
import json
import os
import queue
import subprocess
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pedalboard import Limiter, Pedalboard, Convolution, Delay
from aiohttp import web
import aiohttp_cors
import websockets
import socket
from ui.server import start_ui_server_in_thread 


print(sd.query_devices())

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Global Variables and Defaults
sd.default.latency = 'low'

q = queue.Queue()
recording = False
file_index = 0
recording_start_time = None
effects_status = []
input_rms = 0
output_rms = 0
input_rms_values = []
output_rms_values = []
window_size = 50  # Window size for RMS moving average

board = Pedalboard([
    Convolution("./impulse.wav", 0.5),
    Delay(delay_seconds=0.5, feedback=0.5, mix=0.4),
    Limiter()
])

# Utility Functions
def moving_average(values, window_size):
    if len(values) < window_size:
        return np.mean(values)
    return np.mean(values[-window_size:])

def serialize(obj):
    if isinstance(obj, (str, int, float, bool, type(None))):
        return json.dumps(obj)
    elif isinstance(obj, (list, tuple, set)):
        return json.dumps([serialize(item) for item in obj])
    elif isinstance(obj, dict):
        return json.dumps({k: serialize(v) for k, v in obj.items()})
    else:
        try:
            data = {attr: serialize(getattr(obj, attr)) for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("__")}
            return json.dumps(data)
        except TypeError:
            return json.dumps(str(obj))

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def run_electron(port='2811'):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    # Start the Electron app as a subprocess
    # Pass the port as an environment variable
    process = subprocess.Popen(f'npm run electron --port {port}', shell=True)

    # Wait for the Electron process to terminate
    process.wait()
    os._exit(1)

# Check if React app is running on port 2810
if check_port(2810):
    ui_dev_mode = True
else:
    ui_dev_mode = False

def callback(indata, outdata, frames, time, status):
    global input_rms, output_rms

    # Handle mono to stereo conversion or ensure only two channels are used
    if indata.shape[1] == 1:  # Mono input
        stereo_indata = np.hstack((indata, indata))
    elif indata.shape[1] > 2:  # More than two input channels
        stereo_indata = indata[:, :2]  # Use only the first two channels
    else:
        stereo_indata = indata  # Two channels, use as is

    processed_data = board(stereo_indata, sample_rate=44100, reset=False)

    # Ensure processed_data is compatible with outdata shape
    if processed_data.shape[0] > outdata.shape[0]:
        # If processed_data has more frames than outdata can handle, truncate it
        processed_data = processed_data[:outdata.shape[0], :]
    if processed_data.shape[1] != outdata.shape[1]:
        # If the channel count doesn't match, adjust it.
        # Assuming outdata requires stereo output (2 channels)
        if processed_data.shape[1] == 1:  # Mono to Stereo
            processed_data = np.tile(processed_data, (1, 2))
        else:  # If processed_data has more than 2 channels, use only the first two
            processed_data = processed_data[:, :2]

    outdata[:processed_data.shape[0], :processed_data.shape[1]] = processed_data

    # Append RMS values and compute moving averages
    if len(processed_data) > 0:
        input_rms_values.append(np.sqrt(np.mean(np.square(stereo_indata))))
        output_rms_values.append(np.sqrt(np.mean(np.square(processed_data))))
        input_rms = moving_average(input_rms_values, window_size)
        output_rms = moving_average(output_rms_values, window_size)
    else:
        outdata.fill(0.0)

    if recording:
        q.put(processed_data.copy())

def toggle_recording():
    global recording, recording_start_time, file_index
    recording = not recording
    if recording:
        print("Recording started...")
        recording_start_time = calendar.timegm(time.gmtime())
    else:
        print("Recording stopped. Saving file...")
        save_recording()

def save_recording():
    global file_index, recording_start_time
    recording_start_time = None
    timestamp = calendar.timegm(time.gmtime())
    file_name = os.path.join('recordings', f'recording-{timestamp}.wav')
    file_index += 1
    data_to_save = []
    while not q.empty():
        data_to_save.append(q.get())
    data_to_save = np.concatenate(data_to_save, axis=0)
    sf.write(file_name, data_to_save, 44100, subtype='PCM_24')
    print(f"File saved as '{file_name}'")

# WebSocket Handling
async def websocket_handler(websocket, path):
    global recording, recording_start_time, effects_status, input_rms, output_rms
    try:
        while True:
            data = {
                'recording': recording,
                'recording_start_time': recording_start_time,
                'output_rms': str(output_rms),
                'input_rms': str(input_rms),
                'effects': effects_status
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(0.01)
    except websockets.exceptions.ConnectionClosedOK:
        print("WebSocket connection closed normally.")
    except Exception as e:
        print(f"WebSocket error: {e}")

async def websocket_server():
    async with websockets.serve(websocket_handler, 'localhost', 8765):
        await asyncio.Future()  # Run forever

def start_websocket_server():
    asyncio.run(websocket_server())

# HTTP Server Setup
async def handle_get(request):
    return web.Response(text="Hi from ResoBox, i'm alive!")

async def handle_post(request):
    global board
    data = await request.json()

    action = data.get("action")
    effect_type = data.get("effect_type")
    new_mix = data.get("mix")

    if action is not None:
        if action == "update_plugin_state":
            if new_mix is not None and effect_type:
                for effect in board:
                    if effect.__class__.__name__ == effect_type and hasattr(effect, 'mix'):
                        effect.mix = new_mix
                update_effects_status()
                return web.Response(text=f"Updated {effect_type} mix to: {new_mix}")
            return web.Response(text="Effect type or mix value not provided", status=400)
        elif action == "toggle_recording":
           toggle_recording()
        else:
            return web.Response(text="Action not recognized", status=400)
    else:
        return web.Response(text="Action not provided", status=400)


async def start_http_server(loop):
    app = web.Application()
    app.router.add_get('/', handle_get)
    app.router.add_post('/', handle_post)
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8766)
    await site.start()
    await asyncio.Event().wait()

def start_http_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_http_server(loop))

# Main Flow and Entry Point
def update_effects_status():
    global effects_status
    effects_status = [{'type': type(effect).__name__, 'state': json.loads(serialize(effect))} for effect in board]

def audio_stream():
    try:
        with sd.Stream(callback=callback, latency=0, blocksize=128, samplerate=44100):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    update_effects_status()
    threading.Thread(target=start_websocket_server).start()
    threading.Thread(target=start_http_server_in_thread).start()

    if not ui_dev_mode:
        threading.Thread(target=start_ui_server_in_thread).start()
    
    threading.Thread(target=audio_stream).start()
    
    if not ui_dev_mode:
        target_port = 2811
    else:
        target_port = 2810

    need_retry = True
    while need_retry:
        port_exists = check_port(target_port)
        if port_exists:
            need_retry = False
        else:
            time.sleep(1)
        
    run_electron(target_port)

    while True:
        time.sleep(0.1)

if __name__ == '__main__':
    asyncio.run(main())
