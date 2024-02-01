import asyncio
import calendar
import json
import os
import queue
import threading
import time
import numpy as np
import sounddevice as sd
import soundfile as sf
from pedalboard import Pedalboard, Convolution, Delay
from aiohttp import web
import aiohttp_cors
import websockets
import webview

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

# Audio Processing
def callback(indata, outdata, frames, time, status):
    global input_rms, output_rms
    if status:
        print(status)
    processed_data = board(indata, sample_rate=44100, reset=False)
    if len(processed_data) > 0:
        outdata[:len(processed_data)] = processed_data
        input_rms_values.append(np.sqrt(np.mean(np.square(indata))))
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
    global file_index
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
    effect_type = data.get("effect_type")
    new_mix = data.get("mix")
    if new_mix is not None and effect_type:
        for effect in board:
            if effect.__class__.__name__ == effect_type and hasattr(effect, 'mix'):
                effect.mix = new_mix
        update_effects_status()
        return web.Response(text=f"Updated {effect_type} mix to: {new_mix}")
    return web.Response(text="Effect type or mix value not provided", status=400)


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
    effects_status = [{'type': type(effect).__name__, 'effect': json.loads(serialize(effect))} for effect in board]

def audio_stream():
    try:
        with sd.Stream(callback=callback):
            print("Press Space to start/stop recording, ESC to quit")
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
    threading.Thread(target=audio_stream).start()
    url = 'http://localhost:2810'
    window = webview.create_window('ResoBox', url)
    window.events.closed += lambda: os._exit(1)
    webview.start()

if __name__ == '__main__':
    asyncio.run(main())
