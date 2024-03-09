# HTTP Server Setup
import asyncio
import aiohttp_cors
import config

from aiohttp import web

async def handle_get(request):
    return web.Response(text="🎛 Hi from ResoBox, i'm alive! (maybe)")

async def handle_post(request):
    global board

    data = await request.json()

    action = data.get("action")
    effect_id = data.get("effect_id")
    new_mix = data.get("mix")

    if action is not None:
        if action == "update_plugin_state":
            if new_mix is not None and effect_id:
                for index, effect in enumerate(config.board):
                    current_id = config.fxchain_ids[index]
                    if current_id == effect_id and hasattr(effect, 'mix'):
                        effect.mix = new_mix
                config.update_effects_status()
                return web.Response(text=f"Updated {current_id} mix to: {new_mix}")
            return web.Response(text="Effect type or mix value not provided", status=400)
        elif action == "toggle_recording":
           print('🛑 Not available yet')
        else:
            return web.Response(text="Action not recognized", status=400)
    else:
        return web.Response(text="Action not provided", status=400)


async def start_http_server(loop):
    app = web.Application()
    app.router.add_get('/', handle_get)
    app.router.add_post('/', handle_post)
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
    site = web.TCPSite(runner, '0.0.0.0', 8766)
    await site.start()
    await asyncio.Event().wait()

def start_http_server_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_http_server(loop))
