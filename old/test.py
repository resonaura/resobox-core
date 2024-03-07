import jack
from pedalboard import Pedalboard, Reverb
import numpy


client = jack.Client("InputToOutputRouter")

# Создание Pedalboard с эффектами
board = Pedalboard([Reverb(room_size=1, wet_level=0.1)])

# Create two ports for stereo input and output

inport1 = client.inports.register("input_1")

inport2 = client.inports.register("input_2")

outport1 = client.outports.register("output_1")

outport2 = client.outports.register("output_2")


@client.set_process_callback

def process(frames):
    global board  # Assuming 'board' is your Pedalboard instance
    sample_rate = client.samplerate

    # Convert input buffer to numpy array with appropriate type
    in1 = numpy.frombuffer(inport1.get_buffer(), dtype=numpy.float32)
    in2 = numpy.frombuffer(inport2.get_buffer(), dtype=numpy.float32)
    stereo_audio = numpy.stack([in1, in2], axis=-1)

    # Process audio through the pedalboard
    processed_audio = board(stereo_audio, sample_rate, 8192, False).astype(numpy.float32)

    # Output processed audio
    outport1.get_buffer()[:] = processed_audio[:, 0].tobytes()
    outport2.get_buffer()[:] = processed_audio[:, 1].tobytes()


@client.set_xrun_callback

def xrun(delay):

    print(f"XRUN: Delay of {delay} microseconds")


@client.set_shutdown_callback

def shutdown(status, reason):

    print(f"JACK shutdown: {reason}, status: {status}")


# Activate the client

client.activate()


# Automatically connect the input ports to the system capture ports

# and the output ports to the system playback ports, if available.

try:

    capture_ports = client.get_ports(is_physical=True, is_output=True)

    playback_ports = client.get_ports(is_physical=True, is_input=True)

    

    if len(capture_ports) >= 1 and len(playback_ports) >= 2:

        client.connect(capture_ports[0], inport1.name)

        client.connect(capture_ports[0], inport2.name)

        client.connect(outport1.name, playback_ports[0])

        client.connect(outport2.name, playback_ports[1])

    else:

        print("Not enough capture or playback ports available")


    # Keep the client running

    input("Press Enter to stop...")

finally:

    # Deactivate and close the client properly

    client.deactivate()

    client.close()