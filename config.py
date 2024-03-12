import json

import config

from pedalboard import Pedalboard, Convolution, Chorus, Reverb, Delay
from utils import create_effect, serialize

# Global variables
effects_status = []
input_rms = 0
output_rms = 0

window_size = 50  # Window size for RMS moving average

fxchain = [
    create_effect(Convolution, 'assets/impulses/masonic.wav', 0.5),
    create_effect(Chorus),
    create_effect(Delay, delay_seconds=0.5, feedback=0.5, mix=0.5),
    create_effect(Reverb, room_size=1, wet_level=0.1)
]
fxchain_ids = [id for _, id in fxchain]
board = Pedalboard([fx for fx, _ in fxchain])

input_rms_values = []
output_rms_values = []

# Global constants
websocket_sleep_time = 0.02
screen_fps = 40
screen_width = 128
screen_height = 32


# Main Flow and Entry Point
def update_effects_status():
    global board, fxchain_ids, effects_status

    config.effects_status = []
    for index, effect in enumerate(board):
        id = fxchain_ids[index]
        effects_status.append({'id': id, 'type': type(effect).__name__, 'state': json.loads(serialize(effect))} )
