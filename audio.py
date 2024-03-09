import os
import jack
import numpy
import asyncio

import config
import utils

async def audio_server():
    global config
    client = jack.Client("ResoBox")

    # Create two ports for stereo input and output
    input_port_l = client.inports.register("input_1")
    input_port_r = client.inports.register("input_2")
    output_port_l = client.outports.register("output_1")
    output_port_r = client.outports.register("output_2")

    @client.set_process_callback
    def process(buffer):
        sampleRate = client.samplerate

        # Convert input buffer to numpy array with appropriate type
        input_l = numpy.frombuffer(input_port_l.get_buffer(), dtype=numpy.float32)
        input_r = numpy.frombuffer(input_port_r.get_buffer(), dtype=numpy.float32)

        stereo_audio = numpy.stack([input_l, input_r], axis=-1)

        # Process audio through the pedalboard
        processed_audio = config.board(stereo_audio, sampleRate, 8192, False).astype(numpy.float32)

        config.input_rms_values.append(numpy.sqrt(numpy.mean(numpy.square(stereo_audio))))
        config.output_rms_values.append(numpy.sqrt(numpy.mean(numpy.square(processed_audio))))
        config.input_rms = utils.moving_average(config.input_rms_values, config.window_size)
        config.output_rms = utils.moving_average(config.output_rms_values, config.window_size)

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

    config.update_effects_status()


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
    
        await asyncio.Future()

    finally:
        # Deactivate and close the client properly
        client.deactivate()
        client.close()
        os._exit(1)
    

def start_audio_server():
    asyncio.run(audio_server())
