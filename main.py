import asyncio
import calendar
import json
import os
import threading
import aiohttp_cors
import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import time
from pedalboard import Delay, Pedalboard, Convolution, PitchShift
import websockets
from aiohttp import web
import webview

sd.default.latency = 'low'


print(sd.query_devices())


q = queue.Queue()
recording = False
file_index = 0

recording_start_time = None
effects_status = []

input_rms = 0
output_rms = 0

def moving_average(values, window_size):
    """Calculate the moving average over a list of values."""
    if len(values) < window_size:
        # Not enough values to calculate a meaningful average
        return np.mean(values)
    return np.mean(values[-window_size:])

# Initialize lists to store RMS values
input_rms_values = []
output_rms_values = []

# Set your desired window size for smoothing
window_size = 50  # for example, average over the last 10 RMS values


# Setup the pedalboard with a Reverb effect
board = Pedalboard([
    Convolution("./impulse.wav", 0.5),
    Delay(
        delay_seconds=0.5,
        feedback=0.5,
        mix=0.4
    ),
])

async def handle_get(request):
    # Example GET handler
    return web.Response(text="This is a GET response!")

async def handle_post(request):
    global board

    data = await request.json()
    new_mix = data.get("mix")
    if new_mix is not None:
        # Обновление эффекта Delay с новым значением mix
        for effect in board:
            if isinstance(effect, Delay):
                effect.mix = new_mix
        return web.Response(text=f"Updated mix to: {new_mix}")
    return web.Response(text="Mix value not provided", status=400)

async def start_http_server(loop):
    app = web.Application()

    # Создание маршрутов
    app.router.add_get('/', handle_get)
    app.router.add_post('/', handle_post)

    # Настройка CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # Разрешение CORS на всех маршрутах
    for route in list(app.router.routes()):
        cors.add(route)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 666)
    await site.start()

    await asyncio.Event().wait()

# ... остальной код ...

def start_http_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_http_server(loop))

def serialize(obj):
    """
    Serialize any object to a JSON string.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return json.dumps(obj)  # Serialize basic types directly
    elif isinstance(obj, (list, tuple, set)):
        return json.dumps([serialize(item) for item in obj])  # Recursively serialize each item
    elif isinstance(obj, dict):
        return json.dumps({k: serialize(v) for k, v in obj.items()})  # Serialize dict items
    else:
        # Attempt to serialize custom objects
        try:
            data = {attr: serialize(getattr(obj, attr)) for attr in dir(obj) if not callable(getattr(obj, attr)) and not attr.startswith("__")}
            return json.dumps(data)
        except TypeError:
            return json.dumps(str(obj))  # As a last resort, convert to string

def update_effects_status():
    global board, effects_status
    effects_status = []
    for effect in board:
        effect_data = {'type': type(effect).__name__}

        effect_data['effect'] = json.loads(serialize(effect))

        effects_status.append(effect_data)

async def websocket_handler(websocket, path):
    global output_rms, recording, recording_start_time, effects_status, input_rms
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
        print("WebSocket connection closed normally")
    except Exception as e:
        print(f"WebSocket error: {e}")

# This is your modified callback function
def callback(indata, outdata, frames, time, status):
    global output_rms, input_rms, recording

    if status:
        print(status)

    # Assuming indata is a stereo signal
    # Process the input data with the pedalboard
    processed_data = board(indata, sample_rate=44100, reset=False)

    # Check if processed_data is not empty before assigning it to outdata
    if len(processed_data) > 0:
        outdata[:len(processed_data)] = processed_data
        input_rms_raw = np.sqrt(np.mean(np.square(indata)))
        output_rms_raw = np.sqrt(np.mean(np.square(processed_data)))  # Calculate RMS value

        input_rms_values.append(input_rms_raw)
        output_rms_values.append(output_rms_raw)
        
        # Apply the moving average for smoothing
        input_rms = moving_average(input_rms_values, window_size)
        output_rms = moving_average(output_rms_values, window_size)
    else:
        # If processed_data is empty, fill outdata with zeros to avoid the broadcasting error
        outdata.fill(0.0)

    # Write the processed data to the output buffer
    if recording:
        q.put(processed_data.copy())

async def websocket_server():
    async with websockets.serve(websocket_handler, 'localhost', 8765):
        await asyncio.Future()  # run forever

def start_websocket_server():
    asyncio.run(websocket_server())

def toggle_recording():
    global recording, recording_start_time, file_index
    recording = not recording
    if recording:
        print("Recording started...")
        recording_start_time = calendar.timegm(time.gmtime())
    else:
        print("Recording stopped. Saving file...")
        recording_start_time = None

        # gmt stores current gmtime
        gmt = time.gmtime()
        
        # ts stores timestamp
        timestamp = calendar.timegm(gmt)
        file_name = os.path.join('recordings', f'recording-{timestamp}.wav')
        file_index += 1

        data_to_save = []
        while not q.empty():
            data = q.get()
            normalized_data = data
            data_to_save.append(normalized_data)

        data_to_save = np.concatenate(data_to_save, axis=0)
        sf.write(file_name, data_to_save, 44100, subtype='PCM_24')
        print(f"File saved as '{file_name}'")

def on_ui_window_closed():
    print('pywebview window is closed')
    os._exit(1)

def audio_stream():
    try:
        with sd.Stream(device=(3, 2),
                       samplerate=44100, blocksize=128, latency=0,
                       channels=1, dtype=np.float32, callback=callback):
            print('#' * 80)
            print('Press Space to start/stop recording, ESC to quit')
            print('#' * 80)

            while True:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(type(e).__name__ + ': ' + str(e))

async def main():
    global recording, file_index

    update_effects_status()

    websocket_thread = threading.Thread(target=start_websocket_server)
    websocket_thread.start()

    http_server_thread = threading.Thread(target=start_http_server_in_thread)
    http_server_thread.start()

    audio_thread = threading.Thread(target=audio_stream)
    audio_thread.start()

    # URL you want to open
    url = 'http://localhost:2810'
    # Create a window that loads the URL
    window = webview.create_window('ResoBox', url)

    window.events.closed += on_ui_window_closed
    webview.start()

if __name__ == '__main__':
    asyncio.run(main())