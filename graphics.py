import asyncio
import json
import websockets
from PIL import Image, ImageDraw, ImageFont

# Параметры
text = "Привет, мир!"  # Текст для рисования
font_path = "assets/fonts/font.ttf"  # Путь к шрифту
font_size = 24  # Размер шрифта
x, y = 0, 0  # Начальное положение текста

font = ImageFont.truetype(font_path, font_size)
image = Image.new('1', (256, 128), 0)  # Создание черно-белого изображения один раз
draw = ImageDraw.Draw(image)  # Создание объекта для рисования один раз


def create_image(x, y):
    draw.rectangle((0, 0, image.width, image.height), fill=0)  # Очистка изображения
    draw.text((x, y), text, 1, font=font)  # Рисование текста
    return image

async def websocket_handler(websocket, path):
    global x, y
    while True:
        image = create_image(x, y)
        pixels = image.load()
        matrix = [[pixels[x, y] for x in range(image.width)] for y in range(image.height)]
        await websocket.send(json.dumps(matrix))
        x = (x + 1) % image.width  # Обновление положения текста для создания анимации
        await asyncio.sleep(0.033)  # Контроль скорости анимации

async def graphics_server():
    print("\n📺 Graphics server started\n")
    async with websockets.serve(websocket_handler, '0.0.0.0', 8767):
        await asyncio.Future()  # Run forever

def start_graphics_server():
    asyncio.run(graphics_server())