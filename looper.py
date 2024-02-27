import json
import threading
import numpy as np
import time

from utils import serialize

class Layer:
    def __init__(self, sample_rate=48000, is_recording=False, initial_samples=[], elapsed=None, buffer_size=128):
        self.samples = []  # Samples for this layer
        self.is_recording = is_recording  # Is this layer currently recording
        self.record_start_time = elapsed  # Time when recording started for this layer
        self.sample_rate = sample_rate  # Sample rate to calculate time offsets
        self.is_first_record = True
        self.modified = False

        if elapsed is not None:
            self.record(initial_samples, elapsed, buffer_size)

    def start_recording(self):
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False

    def record(self, new_samples, elapsed, buffer_size):
        if self.is_first_record:
            # Рассчитываем количество тишины, которое нужно добавить
            silence_length = max(0, int(elapsed * self.sample_rate))
            # Создаем массив numpy тишины для стерео аудио
            silence = np.zeros((silence_length, 2), dtype=new_samples.dtype)
            # Добавляем тишину в начало записи
            self.samples.append(silence)
            self.is_first_record = False

        # Добавляем новые сэмплы после тишины
        self.samples.append(new_samples)
        self.modified = True

    def check_and_reset_modified(self):
        was_modified = self.modified
        self.modified = False
        return was_modified

    def get_samples(self):
        """Get samples from this layer."""
        if len(self.samples) > 0:
            return np.concatenate(self.samples, axis=0)
        else:
            return np.zeros((0, 2))
        
    def get_samples_len(self):
        return sum([len(samples) for samples in self.samples])

class Track:
    def __init__(self, sample_rate):
        self.sample_rate = sample_rate
        self.is_playing = False  # Playback state flag
        self.is_recording = False  # Recording state flag
        self.layers = []
        self.audio_len = 0
        self.audio_duration = 0
        self.calculation_lock = threading.Lock()  # Lock for thread-safe operations on the mixed_samples_buffer
        self.calculation_thread = threading.Thread(target=self.calculation_audio_len, daemon=True)  # Separate thread 
        self.calculation_thread.start()

    def play(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False

    def add_layer(self, is_recording, sample_rate, initial_samples=[], elapsed=None, buffer_size=128):
        # Now passing sample_rate to Layer
        self.layers.append(Layer(sample_rate, is_recording, initial_samples, elapsed, buffer_size))

    def calculation_audio_len(self):
        while True:
            with self.calculation_lock:
                max_len = 0

                for layer in self.layers:
                    if not layer.is_recording:
                        current_samples_len = layer.get_samples_len()

                        if current_samples_len > max_len:
                            max_len = current_samples_len

               
                self.audio_len = max_len
                self.audio_duration = max_len / self.sample_rate

                time.sleep(0.01)


    def record(self, new_samples, buffer_size, elapsed):
        for layer in self.layers:
            if layer.is_recording:
                
                new_len = layer.get_samples_len() + len(new_samples)

                # Лупа за пупу
                if new_len <= self.audio_len or self.audio_len == 0:
                    layer.record(new_samples, elapsed, buffer_size)
                # А пупа - залупу
                else:
                    layer.stop_recording()
                    self.add_layer(is_recording=True, sample_rate=self.sample_rate, initial_samples=new_samples, elapsed=elapsed, buffer_size=buffer_size)
                    break

    # Add a method to check if any layer is currently recording
    def is_any_layer_recording(self):
        return any(layer.is_recording for layer in self.layers)

    # Add a method to check if the track needs mixing (i.e., any layer has been modified)
    def needs_mixing(self):
        return any(layer.check_and_reset_modified() for layer in self.layers)

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.add_layer(is_recording=True, sample_rate=self.sample_rate)

    def stop_recording(self):
        self.is_recording = False

        if len(self.layers) > 0:
            for layer in self.layers:
                layer.is_recording = False

    def clear_all_layers(self):
        """Полная очистка всех слоёв."""
        with self.calculation_lock:
            self.layers = []  # Просто очищаем список слоёв

    def remove_last_layer(self):
        """Удаление последнего слоя. Если он записывает, остановить запись."""
        with self.calculation_lock:
            if len(self.layers) > 0:
                # Проверяем, идет ли запись на последнем слое
                if self.layers[-1].is_recording:
                    self.layers[-1].stop_recording()  # Останавливаем запись
                self.layers.pop()  # Удаляем последний слой

class Looper:
    def __init__(self, sample_rate=48000, tracks=1):
        self.sample_rate = sample_rate
        self.is_playing = False  # Playback state flag
        self.start_time = None
        self.tracks = [Track(sample_rate) for _ in range(tracks)]
        self.mixed_samples_buffer = []
        self.mixing_lock = threading.Lock()  # Lock for thread-safe operations on the mixed_samples_buffer
        self.mixing_thread = threading.Thread(target=self.mix_samples, daemon=True)  # Separate thread for mixing samples
        self.mixing_thread.start()  # Start the mixing thread
        self.wav_index = 0
        self.audio_len = 0
        self.audio_duration = 0
        self.elapsed = 0

    def clear_all_layers(self, track_index):
        """Полная очистка всех слоёв."""

        if track_index < len(self.tracks):
            self.tracks[track_index].clear_all_layers()

    def remove_last_layer(self, track_index):
        """Удаление последнего слоя. Если он записывает, остановить запись."""
        if track_index < len(self.tracks):
            self.tracks[track_index].remove_last_layer()

    def mix_samples(self):
        """Mix samples in a separate thread."""
        while True:
           with self.mixing_lock:
                layers_samples = []
                max_len = 0
                needs_mixing = False

                # Determine if mixing is needed
                for track in self.tracks:
                    if track.is_playing and track.needs_mixing() and not track.is_any_layer_recording():
                        needs_mixing = True
                        break

                if not needs_mixing:
                    time.sleep(0.1)  # Sleep if no mixing is needed
                    continue

                # Step 1: Determine the maximum length among all tracks.
                for track in self.tracks:
                    if track.is_playing:
                        for layer in track.layers:
                            if not layer.is_recording:
                                current_samples_len = layer.get_samples_len()
                                if current_samples_len > max_len:
                                    max_len = current_samples_len

                # Initialize the mixing buffer with zeros (assuming stereo samples).
                tmpbuffer = np.zeros((int(max_len), 2))

                # Step 2: Loop or directly add each track based on its length.
                for track in self.tracks:
                    if track.is_playing:
                        for layer in track.layers:
                            if not layer.is_recording:
                                current_samples = layer.get_samples()
                                current_samples_len = layer.get_samples_len()

                                # If the track is shorter, loop it; if it's longer or equal, add as is.
                                if current_samples_len < max_len:
                                    repeat_factor = int(np.ceil(max_len / current_samples_len))
                                    repeated_samples = np.tile(current_samples, (repeat_factor, 1))[:int(max_len), :]
                                    tmpbuffer += repeated_samples
                                else:
                                    # For the track that is longer or exactly max_len, add without looping.
                                    tmpbuffer += current_samples[:int(max_len), :]

                self.mixed_samples_buffer = tmpbuffer
                self.audio_len = max_len
                self.audio_duration = max_len / self.sample_rate

                time.sleep(0.1)

    def get_state(self):
        # Serialize the Looper state to a dictionary
        state = {
            "sample_rate": self.sample_rate,
            "is_playing": self.is_playing,
            "start_time": self.start_time,
            "tracks": [],
            "audio_len": self.audio_len,
            "audio_duration": self.audio_duration,
            "elapsed": self.elapsed
        }

        # Serialize each track in the Looper
        for track in self.tracks:
            track_state = {
                "sample_rate": track.sample_rate,
                "is_playing": track.is_playing,
                "is_recording": track.is_recording,
                "audio_len": track.audio_len,
                "audio_duration": track.audio_duration,
                "layers": []
            }

            # Serialize each layer in the track
            for layer in track.layers:
                layer_state = {
                    "is_recording": layer.is_recording,
                    "record_start_time": layer.record_start_time,
                    "sample_rate": layer.sample_rate,
                    "samples_len": layer.get_samples_len()
                }
                track_state["layers"].append(layer_state)

            state["tracks"].append(track_state)

        # Use the serialize function to handle non-standard types
        # Note: You will need to define the `serialize` function based on your needs,
        # especially for any custom objects or those that are not JSON serializable by default.
        return json.dumps(state, default=serialize)

    # Пупа и лупа пришли получать зарплату
    def record(self, new_samples, buffer_size):
        for track in self.tracks:
            if track.is_recording:
                track.record(new_samples, buffer_size, self.elapsed)

    def play(self):
        self.is_playing = True

    def stop(self):
        self.is_playing = False

    def start_recording(self, track_index):
        if track_index < len(self.tracks):
            self.tracks[track_index].start_recording()

    def stop_recording(self, track_index):
        if track_index < len(self.tracks):
            self.tracks[track_index].stop_recording()

    def get_next_samples(self, frames, indata_shape):
        if not self.is_playing:
            return np.zeros((frames, 2))
        
        current_time = time.time()
        seconds_from_play_start = current_time - self.start_time

        if self.audio_duration == 0:
            self.wav_index = 0
            self.start_time = time.time()
    
        if self.audio_duration > 0:
            self.elapsed = seconds_from_play_start % self.audio_duration
        else:
            self.elapsed = 0
    
        if not self.is_playing or self.start_time is None or len(self.mixed_samples_buffer) == 0:
            return np.zeros((frames, 2))
    
        sound = self.mixed_samples_buffer
        sound_length = len(self.mixed_samples_buffer)
        
        # Создание зацикленного sound для текущего фрейма
        end_index = self.wav_index + frames
        if end_index > sound_length:
            # Если достигли конца файла, начинаем с начала
            looped_sound = np.concatenate((sound[self.wav_index:], sound[:end_index % sound_length]))
        else:
            looped_sound = sound[self.wav_index:end_index]
        self.wav_index = end_index % sound_length

        # Подгонка размера looped_sound под stereo_indata, если необходимо
        if looped_sound.shape[0] < indata_shape[0]:
            looped_sound = np.resize(looped_sound, indata_shape)

        # Смешивание аудио сигнала с sound.wav
        return looped_sound[:indata_shape[0], :indata_shape[1]]


