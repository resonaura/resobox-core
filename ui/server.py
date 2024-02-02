import asyncio
from aiohttp import web
import aiohttp_cors
import os

# Assuming your React app's build directory is copied to "webui" within your project directory
async def handle_get(request):
    # Serve the index.html for any GET request
    with open('build/index.html', 'rb') as f:
        return web.Response(body=f.read(), content_type='text/html')

async def handle_static(request):
    # Extract the requested file path from the URL
    file_path = request.match_info['filename']
    full_path = os.path.join('build', file_path)

    # Check if the file exists, and if so, serve it
    if os.path.exists(full_path) and os.path.isfile(full_path):
        with open(full_path, 'rb') as f:
            return web.Response(body=f.read(), content_type='application/octet-stream')
    else:
        return web.Response(status=404)

async def start_ui_server(loop):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    print("UI dev server not started, using production build")

    if os.path.exists('build'):
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
    else:
        print("UI build directory does not exists")
        os._exit(1)


def start_ui_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_ui_server(loop))
