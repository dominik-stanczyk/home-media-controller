from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YT Remote Control</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.5/socket.io.min.js"></script>
<style>
  body {
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #000; /* Głęboka czerń */
    color: white;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
    height: 80vh;
    box-sizing: border-box;
  }

  /* --- SEKCJA MINI ODTWARZACZA --- */
  #player-bar {
    width: 90%;
    max-width: 400px;
    background: #1e1e1e;
    margin-top:40px;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 30px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    border: 1px solid #333;
  }

  /* Pasek postępu na samej górze boxa */
  .progress-bg {
    width: 100%;
    height: 4px;
    background: #333;
  }
  .progress-fill {
    width: 0%; /* Tu JS będzie zmieniać szerokość */
    transition: width 1s linear;
    height: 100%;
    background: #ff0000; 
    box-shadow: 0 0 8px #ff0000;
  }
  .player-info {
    display: flex;
    align-items: center;
    padding: 12px;
    gap: 15px;
  }

  /* Miejsce na miniaturkę */
  .thumb-placeholder {
    width: 50px;
    height: 50px;
    border-radius: 8px;
    background: linear-gradient(45deg, #444, #222); /* Przykładowe kolory */
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
  }

  .text-container {
    overflow: hidden;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }

  #track-title {
    font-weight: bold;
    font-size: 15px;
    margin: 0;
    text-overflow: ellipsis;
    overflow: hidden;
  }

  .author-time-row {
    display: flex;
    justify-content: space-between; /* To wypchnie czas na prawą stronę */
    align-items: center;
    margin-top: 2px;
  }

  #track-author, #track-time {
    font-size: 12px;
    color: #aaa;
    margin: 0;
  }

  /* Zapobiega nachodzeniu tekstu na siebie */
  #track-author {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-right: 10px;
  }

  /* --- PRZYCISKI --- */
  .main-controls {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  button {
    width: 280px;
    height: 55px;
    border: none;
    border-radius: 12px;
    background: #fff;
    color: #000;
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.2s;
    touch-action: manipulation;
  }

  button:active {
    transform: scale(0.96);
  }

  .btn-secondary {
    background: #282828;
    color: white;
    border: 1px solid #444;
  }
  button {
    -webkit-tap-highlight-color: transparent; /* usuwa niebieskie podświetlenie na mobile */
    outline: none; /* usuwa obramowanie focus */
  }

  button:focus {
    outline: none;
  }

  button:focus-visible {
    outline: none;
  }
  .volume{
    display:flex;
    justify-content: space-around;

  }
  .volume button{
    width:50px;
    height:50px;
    background-color: #444;
    border-radius:50%;
    color:white;
  }

   #play-icon polygon {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }
</style>
</head>

<body>

  <!-- MINI ODTWARZACZ -->
  <div id="player-bar">
    <div class="progress-bg">
      <div id="progress-bar" class="progress-fill"></div>
    </div>
    <div class="player-info">
      <div id="track-art" class="thumb-placeholder"> </div>
      <div class="text-container">
        <p id="track-title">Tytuł utworu...</p>
        <div class="author-time-row">
          <p id="track-author">Kanał / Autor</p>
          <p id="track-time">0:00 / 0:00</p>
        </div>
      </div>
    </div>
  </div>

  <div class="main-controls">

    <!-- GŁÓWNE STEROWANIE -->
    <div style="display:flex; gap:10px; align-items:center; justify-content:center;">
      <button id="btn-shuffle" onclick="send('shuffle')" style="width:60px; height:60px; background-color:#000; color: white; border-radius:50%; border:none;">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">

          <path d="M4 17h2c2 0 3-1 5-5s3-5 5-5h4"/>
          <path d="M18 4l3 3-3 3"/>

          <path d="M4 7h2c1.5 0 2.5 0.8 3.5 2.5"/>
          <path d="M12.5 14.5c1 1.7 2 2.5 3.5 2.5h5"/>
          <path d="M18 14l3 3-3 3"/>

        </svg>
      </button>
      <!-- PREV -->
      <button class="btn-secondary" onclick="send('prev')" style="width:60px; height:60px; background-color:#000; border: none;">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
          <path d="M18 6l-8 6 8 6V6z"/>
          <rect x="8" y="6" width="2" height="12"/>
        </svg>
      </button>

      <!-- PLAY / PAUSE -->
      <button id="btn-play" onclick="send('pause')" style="width:80px; height:80px; border-radius:50%;">
        <span id="play-icon" style="display:flex; align-items:center; justify-content:center;">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
            <!-- Lewa połówka -->
            <polygon id="poly-left" points="6,5 10,5 10,19 6,19" />
            <!-- Prawa połówka -->
            <polygon id="poly-right" points="14,5 18,5 18,19 14,19" />
          </svg>
        </span>
      </button>
      <!-- NEXT -->
      <button class="btn-secondary" onclick="send('next')" style="width:60px; height:60px; background-color:#000; border: none;">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
          <path d="M6 6l8 6-8 6V6z"/>
          <rect x="14" y="6" width="2" height="12"/>
        </svg>
      </button>

      <button id="btn-loop" onclick="send('loop')" style="width:60px; height:60px; background-color:#000; color: white; border-radius:50%; border:none; display:flex; align-items:center; justify-content:center; cursor:pointer;">
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <!-- Górna strzałka: przesunięta wyżej (y=5.5) -->
          <path d="M4.5 11.5v-2a4 4 0 0 1 4-4h11" />
          <path d="M16.5 2.5l3 3-3 3" />

          <!-- Dolna strzałka: przesunięta niżej (y=18.5) -->
          <path d="M19.5 12.5v2a4 4 0 0 1-4 4h-11" />
          <path d="M7.5 15.5l-3 3 3 3" />
        </svg>
      </button>

    </div>

    <div class="volume">
      <button onclick="send('volume', 0.01)">1%</button>
      <button onclick="send('volume', 0.05)">5%</button>
      <button onclick="send('volume', 0.15)">15%</button>
    </div>

  </div>
     <script>
      const socket = io();

        let isPlaying = true;
  let isShuffle = false;
  let isLoop = false;

  function setPlayIcon(playing) {
    if (isPlaying === playing) return;
    isPlaying = playing;

    const left = document.getElementById('poly-left');
    const right = document.getElementById('poly-right');

    if (!left || !right) return;

    if (isPlaying) {
      left.setAttribute('points', '6,5 10,5 10,19 6,19');
      right.setAttribute('points', '14,5 18,5 18,19 14,19');
    } else {
      left.setAttribute('points', '8,5 13.5,8.5 13.5,15.5 8,19');
      right.setAttribute('points', '13.5,8.5 19,12 19,12 13.5,15.5');
    }
  }

  function applyOptimisticAction(action) {
    if (action === 'pause') {
      setPlayIcon(!isPlaying);
    } else if (action === 'shuffle') {
      isShuffle = !isShuffle;
      document.getElementById('btn-shuffle').style.color = isShuffle ? "#ff0000" : "white";
    } else if (action === 'loop') {
      isLoop = !isLoop;
      document.getElementById('btn-loop').style.color = isLoop ? "#ff0000" : "white";
    }
  }

  function send(action, value="") {
    applyOptimisticAction(action);
    socket.emit('ui_command', {action: action, value: value});
  }

  socket.on('hw_action', function(data) {
    applyOptimisticAction(data.action);
  });


  socket.on('status_update', function(data) {
      if (typeof data.paused !== 'undefined') {
          setPlayIcon(!data.paused);
      } else if (typeof data.isPlaying !== 'undefined') {
          setPlayIcon(data.isPlaying);
      }

      isShuffle = Boolean(data.shuffle);
      const sBtn = document.getElementById('btn-shuffle');
      sBtn.style.color = isShuffle ? "#ff0000" : "white";

      isLoop = Boolean(data.loop);
      const lBtn = document.getElementById('btn-loop');
      lBtn.style.color = isLoop ? "#ff0000" : "white";
      
      document.getElementById('track-title').innerText = data.title || "Brak utworu";
      document.getElementById('track-author').innerText = data.author || "";

      // Zabezpieczenie paska postępu (pilnuje zakresu 0% - 100%)
      const progress = Math.max(0, Math.min(100, Number(data.progress) || 0));
      document.getElementById('progress-bar').style.width = progress + "%";
      
      document.getElementById('track-time').innerText = data.timeStr || "0:00 / 0:00";

      if (data.thumbnail) {
          const art = document.getElementById('track-art');
          const img = new Image();
          img.onload = function() {
              art.style.backgroundImage = `url(${data.thumbnail})`;
              art.style.backgroundSize = "cover";
              art.style.backgroundPosition = "center";
              art.innerText = ""; 
          };
          img.src = data.thumbnail;
      }
  });
  
  </script>

</body>
</html>

"""

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

@socketio.on('update_status')
def handle_status(data):
    global last_status
    last_status = data
    socketio.emit('status_update', data)

#log przy łączeniu 

@socketio.on('connect')
def handle_connect():
    print("WS CLIENT CONNECTED")
    if last_status:
        emit('status_update', last_status)

import time
import serial

def uart_listener():
    stm_connected = None  # None = stan początkowy, True = połączony, False = odłączony

    while True:
        try:
            with serial.Serial('COM5', 115200, timeout=1) as ser:
                if stm_connected is not True:
                    print("STM32 połączone na COM5")
                    stm_connected = True

                while True:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            print(f"Odebrano z STM32: {line}")
                            socketio.emit('command', {'action': line, 'value': ""})
                            socketio.emit('hw_action', {'action': line})
                    time.sleep(0.01)

        except serial.SerialException:
            # Wypisz komunikat tylko raz przy zmianie stanu na rozłączony
            if stm_connected is not False:
                print("STM32 odłączone (oczekiwanie na COM5...)")
                stm_connected = False
            time.sleep(2)

        except Exception as e:
            print(f"Nieoczekiwany błąd UART: {e}")
            stm_connected = False
            time.sleep(2)
if __name__ == "__main__":
    socketio.start_background_task(uart_listener)
    socketio.run(app, host="0.0.0.0", port=5000)
