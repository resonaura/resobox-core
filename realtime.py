import asyncio
import json
import websockets
import config

# WebSocket Handling
async def websocket_handler(websocket, path):
    global config
    try:
        while True:
            # Формируем данные для отправки, включая ID каждого эффекта
            data = {
                'audio': {
                    'input': None,
                    'output': None
                },
                'recording': None,
                'recording_start_time': None,
                'output_rms': str(config.output_rms),
                'input_rms': str(config.input_rms),
                'looper': None,
                'effects': config.effects_status
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(config.websocket_sleep_time)
    except websockets.exceptions.ConnectionClosedOK:
        print("🛑 WebSocket connection closed normally.")
    except Exception as e:
        print(f"🛑 WebSocket error: {e}")

async def websocket_server():
    print("\n✨ WebSocket started\n")
    async with websockets.serve(websocket_handler, '0.0.0.0', 8765):
        await asyncio.Future()  # Run forever

def start_websocket_server():
    asyncio.run(websocket_server())