import asyncio
import json
import time
import websockets
import config
import base64
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

disp = None

try:
    disp = Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_address=0x3C) # Адрес дисплея - в конкретном случае 0x3C
    disp.begin()
    disp.clear()
    disp.display()
except:
    print('🐦 Failed to connect display (shit)')

displayImage = Image.new('1', (config.screen_width, config.screen_height), 0)
displayDraw = ImageDraw.Draw(displayImage)


safeText = '5Y2N5Y2N5Y2NIEnQlEkg0J3QkNCl0KPQmSDljY3ljY3ljY0='
# Параметры
decoded_bytes = base64.b64decode(safeText)
text = decoded_bytes.decode("utf-8")
font_path = "assets/fonts/noto.ttf"
font_size = 16
x, y = 0, 4  # Начальные координаты

# Инициализация шрифта и создание изображения один раз
font = ImageFont.truetype(font_path, font_size)
image = Image.new('1', (config.screen_width, config.screen_height), 0)
draw = ImageDraw.Draw(image)

# Глобальная переменная для хранения матрицы пикселей
global_matrix = []

def update_matrix():
    global x, y, global_matrix
    while True:
        if disp != None:
            fps = config.screen_fps
        else:
            fps = config.screen_fps / 2
            
        draw.rectangle((0, 0, image.width, image.height), fill=0)  # Очистка изображения
        draw.text((x, y), text, 1, font=font)  # Рисование текста
        pixels = image.load()
        global_matrix = [(x, y) for y in range(image.height) for x in range(image.width) if pixels[x, y] == 1]
        x = (x + 1) % (image.width + 30)  # Обновление положения текста для создания анимации
        time.sleep(1 / fps)

        if disp != None:
            displayDraw.rectangle((0, 0, image.width, image.height), fill=0)
            displayDraw.point(global_matrix, fill=255)
            disp.image(displayImage)
            disp.display()

async def websocket_handler(websocket, path):
    try:
        while True:
            # Отправка текущего состояния матрицы
            await websocket.send(json.dumps(global_matrix))
            await asyncio.sleep(1/24)  # Ожидание для синхронизации с частотой обновления матрицы
    except websockets.exceptions.ConnectionClosedOK:
        print("🛑 WebSocket connection closed normally.")
    except Exception as e:
        print(f"🛑 WebSocket error: {e}")

def start_update_matrix_thread():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.submit(update_matrix)

async def graphics_server():
    print("\n📺 Graphics server started\n")
    start_update_matrix_thread()  # Запуск потока для обновления матрицы

    if disp == None:
        async with websockets.serve(websocket_handler, '0.0.0.0', 8767):
            await asyncio.Future()  # Бесконечный цикл

def start_graphics_server():
    try:
        asyncio.run(graphics_server())
    except KeyboardInterrupt:
        print("\n🛑 Graphics server stopped by keyboard interrupt")
        # Здесь можно добавить дополнительную логику для корректного завершения работы, если это необходимо

# Теперь запускаем сервер
if __name__ == "__main__":
    start_graphics_server()
