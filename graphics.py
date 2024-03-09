import asyncio
import json
from PIL import Image, ImageDraw, ImageFont
import websockets

# Параметры
text = "Привет, мир!"
font_path = "assets/fonts/font.ttf"
font_size = 24

# Инициализация шрифта и создание изображения один раз
font = ImageFont.truetype(font_path, font_size)
image = Image.new('1', (256, 128), 0)
draw = ImageDraw.Draw(image)

async def update_matrix(frequency=24):
    x, y = 0, 0  # Начальные координаты
    while True:
        draw.rectangle((0, 0, image.width, image.height), fill=0)  # Очистка изображения
        draw.text((x, y), text, 1, font=font)  # Рисование текста
        pixels = image.load()
        matrix = [[pixels[x, y] for x in range(image.width)] for y in range(image.height)]
        x = (x + 1) % image.width  # Обновление положения текста для создания анимации
        await asyncio.sleep(1/frequency)  # Ограничение частоты обновления
        yield matrix  # Генерация новой матрицы

async def wwebsocket_handler(websocket, path):
    async for matrix in update_matrix():
        await websocket.send(json.dumps(matrix))
        await asyncio.sleep(1/24)  # Синхронизация с частотой обновления матрицы

async def graphics_server():
    print("\n📺 Graphics server started\n")
    async with websockets.serve(wwebsocket_handler, '0.0.0.0', 8767):
        await asyncio.Future()  # Бесконечный цикл

def start_graphics_server():
    asyncio.run(graphics_server())
