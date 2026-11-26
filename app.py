from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

from server import HTML

@app.route("/")
def index():
    return render_template_string(HTML)

@socketio.on('ui_command')
def handle_ui_command(data):
    # Logujemy, żeby widzieć szybkość w konsoli
    print(f"Command: {data['action']}")
    # Wysyłamy natychmiast do rozszerzenia
    emit('command', data, broadcast=True)
    emit('hw_action', data, broadcast=True, include_self=False)

last_status = {}

current_media = {
    "title": "",
    "artist": "",
    "duration_sec": 0,
    "current_sec": 0,
    "cover_64x64": b"",
    "is_playing": False
}

@socketio.on('update_status')
def handle_status(data):
    global last_status
    last_status = data
    socketio.emit('status_update', data)
    #sendAllMetaData() gdy zmieni się stan

    current_media["current_sec"] = int(data.get("currentTime", 0))
    current_media["is_playing"] = bool(data.get("isPlaying", False))

    # Sprawdź, czy zmieniła się piosenka (porównanie tytułu i autora)
    new_title = data.get("title", "")
    new_artist = data.get("artist", "")

    if new_title != current_media["title"] or new_artist != current_media["artist"]:
        updateFullMetaData(data)
        sendAllMetaData()
#log przy łączeniu 

@socketio.on('connect')
def handle_connect():
    print("WS CLIENT CONNECTED")
    if last_status:
        emit('status_update', last_status)

import time
import serial
import struct
import urllib.request
import io
from PIL import Image

# Globalny uchwyt portu szeregowego, żeby funkcje TX mogły z niego korzystać
active_ser = None
IMG_SIZE = 40  # Zmień na 64, jeśli chcesz 64x64 (wtedy bitmapa ma 512 bajtów)

def calc_xor(data_bytes):
    """Liczy prostą sumę kontrolną XOR ze wszystkich bajtów."""
    checksum = 0
    for b in data_bytes:
        checksum ^= b
    return checksum

def compress_cover(url):
    """Pobiera obrazek z URL, zmniejsza do 40x40 i zamienia na 1-bitową bitmapę (200B)."""
    byte_len = (IMG_SIZE * IMG_SIZE) // 8
    if not url:
        return b'\x00' * byte_len
    try:
        req = urllib.request.urlopen(url, timeout=2)
        img = Image.open(io.BytesIO(req.read()))
        # Zmiana rozmiaru + zamiana na 1-bit (czarno-biały z ditheringiem pod OLED)
        img = img.resize((IMG_SIZE, IMG_SIZE)).convert("1")
        return img.tobytes()  # Zwraca dokładnie 200 bajtów (dla 40x40)
    except Exception as e:
        print(f"Błąd pobierania okładki: {e}")
        return b'\x00' * byte_len

def clean_str_bytes(text, length=32):
    """Koduje tekst do ASCII/UTF-8 i przycina/dopełnia zerami do stałej długości."""
    raw = text.encode('utf-8', errors='ignore')[:length]
    return raw.ljust(length, b'\x00')

def updateFullMetaData(data):
    global current_media
    current_media["title"] = data.get("title", "")
    current_media["artist"] = data.get("artist", "")
    current_media["duration_sec"] = int(data.get("duration", 0))
    current_media["current_sec"] = int(data.get("currentTime", 0))
    current_media["is_playing"] = bool(data.get("isPlaying", False))
    
    # Pobieramy URL miniaturki (zależnie jak nazywa się klucz w Twoim rozszerzeniu)
    thumb_url = data.get("thumbnail", "")
    current_media["cover_64x64"] = compress_cover(thumb_url)

def sync_loop():
    """Wysyła lekki pakiet czasu dokładnie co 1 sekundę, gdy odtwarzacz gra."""
    while True:
        socketio.sleep(1.0)
        if active_ser and active_ser.is_open and current_media["is_playing"]:
            sendQuickSync()

def sendAllMetaData():
    """Wysyła pełną ramkę (272 bajty) do STM32."""
    if active_ser and active_ser.is_open:
        title_b = clean_str_bytes(current_media["title"], 32)
        artist_b = clean_str_bytes(current_media["artist"], 32)
        cover_b = current_media["cover_64x64"]
        
        # '<' = Little Endian (standard w STM32 ARM!)
        # B=uint8, H=uint16, 32s=32 bajty tekstu, 200s=200 bajtów obrazka
        payload = struct.pack(
            f'<BBHHB32s32s{len(cover_b)}s',
            0xAA,                               # Bajt startu
            0x02,                               # Typ ramki: FULL
            current_media["duration_sec"],      # 2B
            current_media["current_sec"],       # 2B
            int(current_media["is_playing"]),   # 1B
            title_b,                            # 32B
            artist_b,                           # 32B
            cover_b                             # 200B
        )
        checksum = calc_xor(payload)
        packet = payload + struct.pack('<BB', checksum, 0x55)
        
        active_ser.write(packet)
        print(f"[UART TX FULL] Wysłano {len(packet)}B: {current_media['artist']} - {current_media['title']}")

def sendQuickSync():
    """Wysyła ultralekką ramkę synchronizacji czasu (7 bajtów) co sekundę."""
    if active_ser and active_ser.is_open:
        payload = struct.pack(
            '<BBHB',
            0xAA,                               # Bajt startu
            0x01,                               # Typ ramki: SYNC
            current_media["current_sec"],       # 2B
            int(current_media["is_playing"])    # 1B
        )
        checksum = calc_xor(payload)
        packet = payload + struct.pack('<BB', checksum, 0x55)
        
        active_ser.write(packet)
        # Odkomentuj poniżej tylko do debugowania, bo będzie wypisywać co sekundę:
        # print(f"[UART TX SYNC] {current_media['current_sec']}s")

ACTIONS = {
    "BTN_1": {"action": "next", "value": ""},
    "BTN_2": {"action": "pause", "value": ""},
    "BTN_3": {"action": "prev", "value": ""},
    "BTN_4": {"action": "shuffle", "value": ""},
    "BTN_5": {"action": "", "value": ""}, #przyszły sleep i wake up, w while dodać push requesta, po obudzeniu RF i wszystko będzie online więc jest to dobry moment aby zrobić pełnego refresha
    "BTN_6": {"action": "loop", "value": ""},
    "BTN_7": {"action": "volume", "value": 0.01},
    "BTN_8": {"action": "volume", "value": 0.05},
    "BTN_9": {"action": "volume", "value": 0.15}
}


def uart_listener():
    stm_connected = None  # None = stan początkowy, True = połączony, False = odłączony
    while True:
        try:
            global active_ser
            with serial.Serial('COM3', 115200, timeout=1) as ser:
                active_ser = ser
                if stm_connected is not True:
                    print("STM32 połączone na COM3")
                    stm_connected = True
                    sendAllMetaData()

                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        # Obsługa wybudzenia pilota ze sleepa (przycisk BTN_5 lub dedykowany komunikat)
                        if line == "WAKE_UP" or line == "BTN_5":
                            print("STM32 -> WAKE_UP! Wysyłam pełny resync...")
                            sendAllMetaData()
                            
                        elif line in ACTIONS:
                            print(f"STM32 -> {line} -> {ACTIONS[line]}")
                            socketio.emit('command', ACTIONS[line])
                            socketio.emit('hw_action', ACTIONS[line])

                    socketio.sleep(0.01)

        except serial.SerialException:
            active_ser = None
            # Wypisz komunikat tylko raz przy zmianie stanu na rozłączony
            if stm_connected is not False:
                print("STM32 odłączone (oczekiwanie na COM3...)")
                stm_connected = False
            time.sleep(2)

        except Exception as e:
            active_ser = None
            print(f"Nieoczekiwany błąd UART: {e}")
            stm_connected = False
            time.sleep(2)
if __name__ == "__main__":
    socketio.start_background_task(uart_listener)
    socketio.start_background_task(sync_loop)
    socketio.run(app, host="0.0.0.0", port=5000)
