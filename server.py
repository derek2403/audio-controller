import asyncio
import logging
from flask import Flask, jsonify, render_template_string
import pyautogui

# --- 1. SILENCE LOGS ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

# --- 2. WINDOWS IMPORTS ---
from winrt.windows.media.control import \
    GlobalSystemMediaTransportControlsSessionManager, \
    GlobalSystemMediaTransportControlsSessionPlaybackStatus

# --- 3. BACKEND ---
async def get_media_info():
    try:
        sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = sessions.get_current_session()
        if session:
            props = await session.try_get_media_properties_async()
            
            # CHECK REAL PLAYBACK STATUS
            # 4 = Playing, 5 = Paused, etc.
            playback_info = session.get_playback_info()
            status = playback_info.playback_status
            is_playing = (status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)

            return {
                "title": props.title if props.title else "Unknown Title",
                "artist": props.artist if props.artist else "Unknown Artist",
                "is_playing": is_playing
            }
    except:
        pass
    # Default if nothing is running
    return {"title": "Nothing Playing", "artist": "Windows Media", "is_playing": False}

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

# --- 4. FRONTEND ---
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
        .hidden { display: none; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                
                // Update Text
                document.getElementById('t').innerText = data.title;
                document.getElementById('a').innerText = data.artist;

                // Update Play/Pause Icon
                const playIcon = document.getElementById('icon-play');
                const pauseIcon = document.getElementById('icon-pause');

                if (data.is_playing) {
                    playIcon.classList.add('hidden');
                    pauseIcon.classList.remove('hidden');
                } else {
                    playIcon.classList.remove('hidden');
                    pauseIcon.classList.add('hidden');
                }

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
            
            <svg id="icon-play" class="w-12 h-12 ml-1" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z"></path>
            </svg>

            <svg id="icon-pause" class="w-10 h-10 hidden" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"></path>
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

# --- 5. RUN ---
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
    app.run(host='0.0.0.0', port=5000)