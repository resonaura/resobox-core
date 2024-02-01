import sounddevice as sd
import soundfile as sf
import numpy as np
import keyboard
import queue
import time
from pedalboard import Delay, Pedalboard, Convolution, PitchShift

sd.default.latency = 'low'


print(sd.query_devices())


q = queue.Queue()
recording = False
file_index = 0

# Setup the pedalboard with a Reverb effect
board = Pedalboard([
    Convolution("./impulse.wav", 0.5),
    Delay(
        delay_seconds=0.5,
        feedback=0.5,
        mix=0.4
    ),
])

# This is your modified callback function
def callback(indata, outdata, frames, time, status):
    if status:
        print(status)

    # Assuming indata is a stereo signal
    # Process the input data with the pedalboard
    processed_data = board(indata, sample_rate=44100, reset=False)

    # Check if processed_data is not empty before assigning it to outdata
    if len(processed_data) > 0:
        outdata[:len(processed_data)] = processed_data
    else:
        # If processed_data is empty, fill outdata with zeros to avoid the broadcasting error
        outdata.fill(0.0)

    # Write the processed data to the output buffer
    if recording:
        q.put(processed_data.copy())


def record_audio():
    global recording, file_index

    try:
        with sd.Stream(device=(0, 0),
                       samplerate=44100, blocksize=128, latency=0,
                       channels=2, dtype=np.float32, callback=callback):
            print('#' * 80)
            print('Press Space to start/stop recording, ESC to quit')
            print('#' * 80)

            while True:
                if keyboard.is_pressed('space'):
                    recording = not recording
                    if recording:
                        print("Recording started...")
                    else:
                        print("Recording stopped. Saving file...")

                        file_name = f'recording-{file_index}.wav'
                        file_index += 1

                        data_to_save = []
                        while not q.empty():
                            data = q.get()
                            normalized_data = data
                            data_to_save.append(normalized_data)
                        
                        data_to_save = np.concatenate(data_to_save, axis=0)
                        sf.write(file_name, data_to_save, 44100, subtype='PCM_24')


                        print(f"File saved as '{file_name}'")

                    
                    while keyboard.is_pressed('space'):
                        pass

                if keyboard.is_pressed('esc'):
                    print("Exiting...")
                    break
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(type(e).__name__ + ': ' + str(e))

if __name__ == '__main__':
    record_audio()