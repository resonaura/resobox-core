import numpy as np
import types
from pedalboard_native import Plugin

class Pan():
    is_effect = True
    is_instrument = False

    @classmethod
    def __instancecheck__(cls, instance):
        return isinstance(instance, Plugin)

    @property
    def __class__(self):
        return Plugin

    def __init__(self, balance=0.5):  # Balance: 0 (left) to 1 (right), with 0.5 being center
        self.balance = balance

    def process(self, audio, sample_rate):
        # Pan law adjustment: -3dB at center
        center_attenuation = np.sqrt(1/2)
        
        # Calculate gains for L and R channels using a cosine and sine law for smooth panning
        left_gain = np.cos(self.balance * np.pi / 2) * center_attenuation
        right_gain = np.sin(self.balance * np.pi / 2) * center_attenuation
        
        # Apply calculated gains to the audio channels
        audio[:, 0] *= left_gain  # Apply gain to the left channel
        audio[:, 1] *= right_gain  # Apply gain to the right channel
        return audio

    def set_balance(self, balance):
        # Ensure the balance is within the range [0, 1]
        self.balance = np.clip(balance, 0, 1)
        

print(isinstance(Pan(), Plugin))