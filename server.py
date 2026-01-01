import asyncio
import base64
from flask import Flask, jsonify, render_template_string
import pyautogui
# The library to talk to Windows Media Controls
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
from winsdk.windows.storage.streams import DataReader

app = Flask(__name__)

# --- BACKEND: WINDOWS CONTROLS ---

async def get_media_info():
    """Gets the current song Title, Artist, and status."""
    sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = sessions.get_current_session()
    
    if session:
        props = await session.try_get_media_properties_async()
        info = {
            "status": "playing", # Simplification; actual status requires more parsing
            "title": props.title if props.title else "Unknown Title",
            "artist": props.artist if props.artist else "Unknown Artist",
            "album": props.album_title if props.album_title else ""
        }
        return info
    else:
        return {"status": "paused", "title": "Nothing Playing", "artist": "Windows Media", "album": ""}

async def media_action(action):
    """Sends Play/Pause/Next/Prev commands to Windows."""
    sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = sessions.get_current_session()
    if session:
        if action == 'play':
            await session.try_toggle_play_pause_async()
        elif action == 'next':
            await session.try_skip_next_async()
        elif action == 'prev':
            await session.try_skip_previous_async()

# --- FRONTEND: HTML + TAILWIND CSS ---
# We embed the HTML here so you only need one file.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Music Remote</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: white; }
        /* Disable double-tap zoom on mobile */
        button { touch-action: manipulation; }
    </style>
    <script>
        // Update Song Info every 1 second
        setInterval(async () => {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                document.getElementById('title').innerText = data.title;
                document.getElementById('artist').innerText = data.artist;
                document.getElementById('album').innerText = data.album;
            } catch (e) { console.log("Connection lost"); }
        }, 1000);

        // Send Command
        async function send(action) {
            // Visual feedback
            const btn = event.currentTarget;
            btn.classList.add('scale-95', 'opacity-80');
            setTimeout(() => btn.classList.remove('scale-95', 'opacity-80'), 100);
            
            await fetch('/control/' + action);
        }
    </script>
</head>
<body class="flex items-center justify-center h-screen select-none">

    <div class="w-full max-w-md p-6 bg-slate-800 rounded-3xl shadow-2xl border border-slate-700 text-center mx-4">
        
        <div class="mb-8 mt-2">
            <p class="text-slate-400 text-xs uppercase tracking-widest mb-4">Now Playing</p>
            <h1 id="title" class="text-3xl font-bold text-white mb-2 truncate leading-tight">Waiting...</h1>
            <h2 id="artist" class="text-xl text-sky-400 font-medium truncate">Connect to PC</h2>
            <p id="album" class="text-slate-500 text-sm mt-1 truncate"></p>
        </div>

        <div class="flex justify-center gap-6 mb-8">
            <button onclick="send('voldown')" class="w-16 h-16 rounded-full bg-slate-700 hover:bg-slate-600 active:bg-slate-500 flex items-center justify-center transition-all shadow-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
                </svg>
            </button>
            <button onclick="send('volup')" class="w-16 h-16 rounded-full bg-slate-700 hover:bg-slate-600 active:bg-slate-500 flex items-center justify-center transition-all shadow-lg">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
            </button>
        </div>

        <div class="h-px bg-slate-700 w-full mb-8"></div>

        <div class="flex justify-between items-center px-2">
            <button onclick="send('prev')" class="transform transition-transform active:scale-90 text-slate-300 hover:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z" />
                </svg>
            </button>

            <button onclick="send('play')" class="w-20 h-20 rounded-full bg-sky-500 hover:bg-sky-400 shadow-lg shadow-sky-500/50 flex items-center justify-center transform transition-transform active:scale-90 text-white">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                </svg>
            </button>

            <button onclick="send('next')" class="transform transition-transform active:scale-90 text-slate-300 hover:text-white">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M4.555 14.832l-1.566.835A1 1 0 003 16V4a1 1 0 001.555-.832L10 6.798v2.798L9 8.333V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z" />
                    <path d="M14.555 14.832A1 1 0 0016 14V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z" />
                </svg>
            </button>
        </div>

    </div>
</body>
</html>
"""

# --- FLASK ROUTES ---

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status():
    # Run the async Windows function
    info = asyncio.run(get_media_info())
    return jsonify(info)

@app.route('/control/<action>')
def control(action):
    if action in ['volup', 'voldown']:
        # Use PyAutoGUI for volume (simulates physical key press)
        # Pressing 5 times makes the change noticeable
        key = 'volumeup' if action == 'volup' else 'volumedown'
        pyautogui.press(key, presses=5)
    else:
        # Use WinSDK for Media (works in background)
        asyncio.run(media_action(action))
    return "OK"

if __name__ == '__main__':
    # Host 0.0.0.0 makes it accessible to your iPhone
    app.run(host='0.0.0.0', port=5000)