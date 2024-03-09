import asyncio
import shutil
import signal
import subprocess
import threading
import time
from aiohttp import web
import aiohttp_cors
import os

from utils import check_port

# Assuming your React app's build directory is copied to "webui" within your project directory
async def handle_get(request):
    # Serve the index.html for any GET request
    with open('build/index.html', 'rb') as f:
        return web.Response(body=f.read(), content_type='text/html')

async def handle_static(request):
    # Extract the requested file path from the URL
    file_path = request.match_info['filename']
    full_path = os.path.join('build', file_path)

    # Determine content type based on file extension
    content_type = 'application/octet-stream'  # Default content type
    if full_path.endswith('.css'):
        content_type = 'text/css'
    elif full_path.endswith('.js'):
        content_type = 'application/javascript'
    elif full_path.endswith('.html'):
        content_type = 'text/html'
    elif full_path.endswith('.json'):
        content_type = 'application/json'
    elif full_path.endswith('.png'):
        content_type = 'image/png'
    elif full_path.endswith('.jpg') or full_path.endswith('.jpeg'):
        content_type = 'image/jpeg'
    elif full_path.endswith('.svg'):
        content_type = 'image/svg+xml'
    # Add other file types as needed

    # Check if the file exists, and if so, serve it
    if os.path.exists(full_path) and os.path.isfile(full_path):
        with open(full_path, 'rb') as f:
            return web.Response(body=f.read(), content_type=content_type)
    else:
        return web.Response(status=404)
    
async def host():
    app = web.Application()
    app.router.add_get('/', handle_get)
    app.router.add_get('/{filename:.*}', handle_static)
    
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True, expose_headers="*",
            allow_headers="*",
        )
    })
    for route in list(app.router.routes()):
        cors.add(route)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 2811)
    await site.start()
    await asyncio.Event().wait()

async def start_ui_server(loop):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    print("🧬 UI dev server not started, using production build\n")

    build_path = os.path.join(dname, 'build')

    if os.path.exists('build'):
        await host()
    else:
        print("🎈 UI build directory does not exist, attempting to build...\n")
        ui_project_path = os.path.join(dname, '../../ui/')  # Adjust the path to your UI project
        try:
            # Navigate to the UI project directory and run npm build
            os.chdir(ui_project_path)
            subprocess.check_call(['npm', 'install'])  # Ensure dependencies are installed
            subprocess.check_call(['npm', 'run', 'build'])  # Replace 'npm build' with 'npm run build' if needed
            # Copy build directory to the desired location
            shutil.copytree(os.path.join(ui_project_path, 'build'), build_path)
            print("✅ Successfully built and copied the UI build directory.\n")
            await host()
        except Exception as e:
            print(f"🛑 Failed to build the UI: {e}\n")
            os._exit(1)
        finally:
            # Change back to the original directory
            os.chdir(dname)

def run_electron(port='2811'):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    # Start the Electron app as a subprocess
    # Pass the port as an environment variable
    process = subprocess.Popen(f'npm run electron --port {port}', shell=True)

    # Wait for the Electron process to terminate
    process.wait()
    main_pid = os.getenv('RESOBOX_MAIN_PID')
    print(main_pid)
    os.kill(int(main_pid), signal.SIGTERM)
    os._exit(1)

def start_ui_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_ui_server(loop))

def start_ui():
    # Check if React app is running on port 2810
    if check_port(2810):
        ui_dev_mode = True
    else:
        ui_dev_mode = False
        
    if not ui_dev_mode:
        target_port = 2811
    else:
        target_port = 2810

    if not ui_dev_mode:
        threading.Thread(target=start_ui_server_in_thread).start()

    need_retry = True
    while need_retry:
        port_exists = check_port(target_port)
        if port_exists:
            need_retry = False
        else:
            time.sleep(1)
        
    run_electron(target_port)

    while True:
        time.sleep(5)