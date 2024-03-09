import jack
import numpy
import threading
import argparse

import config

from ui.server import start_ui 
from realtime import start_websocket_server
from backend import start_http_server_in_thread
from graphics import start_graphics_server
from utils import moving_average

# Настроим парсер аргументов командной строки
parser = argparse.ArgumentParser(description="🎛 ResoBox Audio Processor")
parser.add_argument('--no-ui', action='store_true', help="Disable UI server startup")
parser.add_argument('--no-socket', action='store_true', help="Disable WebSocket backend startup")
parser.add_argument('--no-backend', action='store_true', help="Disable HTTP backend startup")
parser.add_argument('--no-graphics', action='store_true', help="Disable Graphics backend startup")
args = parser.parse_args()


client = jack.Client("ResoBox")

# Create two ports for stereo input and output
input_port_l = client.inports.register("input_1")
input_port_r = client.inports.register("input_2")
output_port_l = client.outports.register("output_1")
output_port_r = client.outports.register("output_2")

@client.set_process_callback
def process(buffer):
    global config  # Assuming 'board' is your Pedalboard instance
    sampleRate = client.samplerate

    # Convert input buffer to numpy array with appropriate type
    input_l = numpy.frombuffer(input_port_l.get_buffer(), dtype=numpy.float32)
    input_r = numpy.frombuffer(input_port_r.get_buffer(), dtype=numpy.float32)

    stereo_audio = numpy.stack([input_l, input_r], axis=-1)

    # Process audio through the pedalboard
    processed_audio = config.board(stereo_audio, sampleRate, 8192, False).astype(numpy.float32)

    config.input_rms_values.append(numpy.sqrt(numpy.mean(numpy.square(stereo_audio))))
    config.output_rms_values.append(numpy.sqrt(numpy.mean(numpy.square(processed_audio))))
    config.input_rms = moving_average(config.input_rms_values, config.window_size)
    config.output_rms = moving_average(config.output_rms_values, config.window_size)

    # Output processed audio
    output_port_l.get_buffer()[:] = processed_audio[:, 0].tobytes()
    output_port_r.get_buffer()[:] = processed_audio[:, 1].tobytes()


@client.set_xrun_callback
def xrun(delay):

    print(f"🔮 XRUN: Delay of {delay} microseconds")


@client.set_shutdown_callback
def shutdown(status, reason):

    print(f"🚽 JACK shutdown: {reason}, status: {status}")


# Activate the client

client.activate()


# Automatically connect the input ports to the system capture ports

# and the output ports to the system playback ports, if available.

try:

    capture_ports = client.get_ports(is_physical=True, is_output=True)
    playback_ports = client.get_ports(is_physical=True, is_input=True)

    if len(capture_ports) >= 1 and len(playback_ports) >= 2:

        client.connect(capture_ports[0], input_port_l.name)

        if len(capture_ports) >= 2:
            client.connect(capture_ports[1], input_port_r.name)
        else:
            client.connect(capture_ports[0], input_port_r.name)

        client.connect(output_port_l.name, playback_ports[0])
        client.connect(output_port_r.name, playback_ports[1])

    else:

        print("🛑 Not enough capture or playback ports available")


    
    config.update_effects_status()

    if not args.no_ui:
        threading.Thread(target=start_ui).start()
    
    if not args.no_socket:
        threading.Thread(target=start_websocket_server).start()

    if not args.no_backend:
        threading.Thread(target=start_http_server_in_thread).start()

    if not args.no_graphics:
        threading.Thread(target=start_graphics_server).start()

    # Keep the client running
    input("\n🤍 Press Enter to stop...\n")

finally:

    # Deactivate and close the client properly
    client.deactivate()
    client.close()