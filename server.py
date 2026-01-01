import asyncio
import logging
from flask import Flask, jsonify, render_template_string
import pyautogui

# --- 1. SILENCE THE LOGS ---
# This turns off the spammy "GET /status 200" messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

# --- 2. WINDOWS MEDIA IMPORTS ---
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
from winrt.windows.storage.streams import DataReader

# --- 3. BACKEND: TALK TO WINDOWS ---
async def get_media_info():
    try:
        sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = sessions.get_current_session()
        if session:
            props = await session.try_get_media_properties_async()
            return {
                "title": props.title if props.title else "Unknown Title",
                "artist": props.artist if props.artist else "Unknown Artist",
                "album": props.album_title if props.album_title else ""
            }
    except:
        pass
    return {"title": "Nothing Playing", "artist": "Windows Media", "album": ""}

async def media_action(action):
    try:
        sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = sessions.get_current_session()
        if session:
            if action == 'play': await session.try_toggle_play_pause_async()
            elif action == 'next': await session.try_skip_next_async()
            elif action == 'prev': await session.try_skip_previous_async()
    except:
        pass

# --- 4. FRONTEND: CLEANER ICONS ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Remote</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0f172a; color: white; -webkit-tap-highlight-color: transparent; }
        button:active { transform: scale(0.95); opacity: 0.7; }
        button { transition: all 0.1s; touch-action: manipulation; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('t').innerText = data.title;
                document.getElementById('a').innerText = data.artist;
            } catch (e) {}
        }, 1000);

        function send(action) { fetch('/control/' + action); }
    </script>
</head>
<body class="flex flex-col items-center justify-center h-screen w-screen overflow-hidden select-none">
    
    <div class="text-center w-full px-8 mb-10">
        <h1 id="t" class="text-3xl font-bold text-white mb-2 truncate drop-shadow-lg">Loading...</h1>
        <h2 id="a" class="text-xl text-slate-400 font-medium truncate">Connecting</h2>
    </div>

    <div class="flex gap-8 mb-10">
        <button onclick="send('voldown')" class="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center shadow-lg border border-slate-700">
            <svg class="w-6 h-6 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4"/></svg>
        </button>
        <button onclick="send('volup')" class="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center shadow-lg border border-slate-700">
            <svg class="w-6 h-6 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
        </button>
    </div>

    <div class="flex items-center gap-6">
        <button onclick="send('prev')" class="p-4 text-slate-300 hover:text-white">
            <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11 19V5l-9 7 9 7zM20 19V5l-9 7 9 7z"></path>
            </svg>
        </button>

        <button onclick="send('play')" class="w-24 h-24 rounded-full bg-blue-500 shadow-blue-500/50 shadow-2xl flex items-center justify-center text-white">
            <svg class="w-10 h-10" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"></path>
            </svg>
        </button>

        <button onclick="send('next')" class="p-4 text-slate-300 hover:text-white">
            <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 24 24">
                <path d="M4 5v14l9-7-9-7zM13 5v14l9-7-9-7z"></path>
            </svg>
        </button>
    </div>

</body>
</html>
"""

# --- 5. ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status(): return jsonify(asyncio.run(get_media_info()))

@app.route('/control/<action>')
def control(action):
    if action in ['volup', 'voldown']:
        pyautogui.press('volumeup' if action == 'volup' else 'volumedown', presses=3)
    else:
        asyncio.run(media_action(action))
    return "", 204

if __name__ == '__main__':
    # Run server
    app.run(host='0.0.0.0', port=5000)