import json

import config

from pedalboard import Pedalboard, Gain, Convolution, Chorus, Reverb, Delay, Compressor, Distortion, LowpassFilter, Limiter, Chain, HighpassFilter, Mix, NoiseGate
from utils import create_effect, serialize

from plugins.pan import Pan

# Global variables
effects_status = []
input_rms = 0
output_rms = 0

window_size = 50  # Window size for RMS moving average

# fxchain = [
#    create_effect(Distortion),
#    create_effect(Convolution, 'assets/impulses/masonic.wav', 0.5),
#    create_effect(Delay, delay_seconds=0.5, feedback=0.5, mix=0),
#    create_effect(Reverb, room_size=1, wet_level=0.1)
#]
fxchain_ids = []
board = Pedalboard([
    NoiseGate(),
    Mix(
        [
            Chain([
                HighpassFilter(cutoff_frequency_hz=1000), # Обрезает частоты ниже 1000 Гц
                LowpassFilter(cutoff_frequency_hz=5000), # Обрезает частоты выше 5000 Гц
                Distortion(50),
                Gain(-20)
            ])
        ]
    ),
    Convolution('assets/impulses/cab.wav', 1),
    Mix([
        Chain([
            Delay(0.5, 0.1, 1),
            LowpassFilter(cutoff_frequency_hz=500),
            Reverb(1, 1, 0.1),
        ]),
        Chain()
    ]),
    Limiter(),
])

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
    #for index, effect in enumerate(board):
    #    #id = fxchain_ids[index]
    #    #effects_status.append({'id': id, 'type': type(effect).__name__, 'state': json.loads(serialize(effect))} )
