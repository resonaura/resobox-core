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
import aiohttp_cors
import websockets

from pedalboard import Limiter, Pedalboard, Convolution, Delay
from aiohttp import web
from looper import Looper
from utils import create_effect, moving_average, serialize
from ui.server import start_ui 


print(sd.query_devices())
print("\n")

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Global Variables and Defaults
sd.default.latency = 'low'
default_input = sd.default.device[0]
default_output = sd.default.device[0]

# Get device information
input_info = sd.query_devices(default_input)
output_info = sd.query_devices(default_output)

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

fxchain = [
    create_effect(Convolution, "./impulse.wav", 0),
    create_effect(Delay, delay_seconds=0.5, feedback=0.5, mix=0),
    create_effect(Limiter)
]
fxchain_ids = [id for _, id in fxchain]
board = Pedalboard([fx for fx, _ in fxchain])

looper = Looper(tracks=2)

def callback(indata, outdata, frames, _time, status):
    global input_rms, output_rms, looper

    # Handle mono to stereo conversion or ensure only two channels are used
    if indata.shape[1] == 1:  # Mono input
        stereo_indata = np.hstack((indata, indata))
    elif indata.shape[1] > 2:  # More than two input channels
        stereo_indata = indata[:, :2]  # Use only the first two channels
    else:
        stereo_indata = indata  # Two channels, use as is

    processed_data = board(stereo_indata, sample_rate=48000, reset=False)

    looper.record(processed_data.copy(), frames)

    looped_sound = looper.get_next_samples(frames, processed_data.shape)

    # Смешивание аудио сигнала с sound.wav
    mixed_data =  processed_data + looped_sound

    # Ensure mixed_data is compatible with outdata shape
    if mixed_data.shape[0] > outdata.shape[0]:
        # If mixed_data has more frames than outdata can handle, truncate it
        mixed_data = mixed_data[:outdata.shape[0], :]
    if mixed_data.shape[1] != outdata.shape[1]:
        # If the channel count doesn't match, adjust it.
        # Assuming outdata requires stereo output (2 channels)
        if mixed_data.shape[1] == 1:  # Mono to Stereo
            mixed_data = np.tile(mixed_data, (1, 2))
        else:  # If mixed_data has more than 2 channels, use only the first two
            mixed_data = mixed_data[:, :2]

    outdata[:mixed_data.shape[0], :mixed_data.shape[1]] = mixed_data

    # Append RMS values and compute moving averages
    if len(mixed_data) > 0:
        input_rms_values.append(np.sqrt(np.mean(np.square(stereo_indata))))
        output_rms_values.append(np.sqrt(np.mean(np.square(mixed_data))))
        input_rms = moving_average(input_rms_values, window_size)
        output_rms = moving_average(output_rms_values, window_size)
    else:
        outdata.fill(0.0)

    if recording:
        q.put(mixed_data.copy())

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
    sf.write(file_name, data_to_save, 48000, subtype='PCM_24')
    print(f"File saved as '{file_name}'")

# WebSocket Handling
async def websocket_handler(websocket, path):
    global recording, recording_start_time, effects_status, input_rms, output_rms, looper
    try:
        while True:
            # Формируем данные для отправки, включая ID каждого эффекта
            data = {
                'audio': {
                    'input': input_info,
                    'output': output_info
                },
                'recording': recording,
                'recording_start_time': recording_start_time,
                'output_rms': str(output_rms),
                'input_rms': str(input_rms),
                'looper': json.loads(looper.get_state()),
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
    global looper
    looper.toggle_playback()
    return web.Response(text="Hi from ResoBox, i'm alive!")

async def handle_post(request):
    global board

    data = await request.json()

    action = data.get("action")
    effect_id = data.get("effect_id")
    new_mix = data.get("mix")

    if action is not None:
        if action == "update_plugin_state":
            if new_mix is not None and effect_id:
                for index, effect in enumerate(board):
                    current_id = fxchain_ids[index]
                    if current_id == effect_id and hasattr(effect, 'mix'):
                        effect.mix = new_mix
                update_effects_status()
                return web.Response(text=f"Updated {current_id} mix to: {new_mix}")
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
    global effects_status, fxchain_ids

    effects_status = []
    for index, effect in enumerate(board):
        id = fxchain_ids[index]
        effects_status.append({'id': id, 'type': type(effect).__name__, 'state': json.loads(serialize(effect))} )


async def main():
    update_effects_status()
    threading.Thread(target=start_websocket_server).start()
    threading.Thread(target=start_http_server_in_thread).start()

    threading.Thread(target=start_ui).start()
    
    try:
        with sd.Stream(callback=callback, latency=0, blocksize=128, samplerate=48000, device=(0,0)):
            while True:
                time.sleep(10000)
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    asyncio.run(main())
