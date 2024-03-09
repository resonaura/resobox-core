import os
import signal
import threading
import argparse
from multiprocessing import freeze_support, Process, current_process

# Предполагаем, что эти модули у вас есть
import config
from ui.server import start_ui 
from realtime import start_websocket_server
from backend import start_http_server_in_thread
from graphics import start_graphics_server
from audio import start_audio_server

threads = []
servers = []
stop_event = threading.Event()

os.environ['RESOBOX_MAIN_PID'] = str(os.getpid())

def controlled_start_thread(target):
    def wrapper():
        while not stop_event.is_set():
            target()
    t = threading.Thread(target=wrapper)
    t.start()
    threads.append(t)

def start_servers(args):
    global threads, servers

    controlled_start_thread(start_audio_server)

    if not args.no_ui:
        ui_server = Process(target=start_ui)
        servers.append(ui_server)

    if not args.no_socket:
        controlled_start_thread(start_websocket_server)

    if not args.no_backend:
        controlled_start_thread(start_http_server_in_thread)

    if not args.no_graphics:
        graphics_server = Process(target=start_graphics_server)
        servers.append(graphics_server)

    for server in servers:
        server.start()

def stop_servers():
    stop_event.set() # Signal threads to stop
    for thread in threads:
        thread.join(timeout=1) # Wait a bit for threads to exit

    for server in servers:
        if server.is_alive():
            server.terminate()
            server.join(timeout=1)

def signal_handler(signum, frame):
    print("\n💀 Closing...")
    stop_servers()
    os._exit(0)

if __name__ == '__main__':
    freeze_support()

    parser = argparse.ArgumentParser(description="🎛 ResoBox Audio Processor")
    parser.add_argument('--no-ui', action='store_true', help="Disable UI server startup")
    parser.add_argument('--no-socket', action='store_true', help="Disable WebSocket backend startup")
    parser.add_argument('--no-backend', action='store_true', help="Disable HTTP backend startup")
    parser.add_argument('--no-graphics', action='store_true', help="Disable Graphics backend startup")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    start_servers(args)
    input("\n🤍 Press Ctrl+C to stop...\n")
    stop_servers()
