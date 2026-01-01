import asyncio
import logging
from flask import Flask, jsonify, render_template_string
import pyautogui
import comtypes # Needed for the threading fix

# Audio Imports
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- 1. SETUP ---
pyautogui.FAILSAFE = False
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__)

# --- 2. WINDOWS MEDIA IMPORTS ---
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

# --- 3. AUDIO CONTROL (Thread-Safe Version) ---
def change_volume(amount):
    """
    Changes volume directly via Audio Driver.
    Includes CoInitialize to fix the 'AttributeError' in threads.
    """
    try:
        # 1. Initialize COM library for this specific thread
        comtypes.CoInitialize()
        
        # 2. Get Speakers
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # 3. Adjust Volume
        current = volume.GetMasterVolumeLevelScalar()
        new_vol = max(0.0, min(1.0, current + amount))
        volume.SetMasterVolumeLevelScalar(new_vol, None)
        
    except Exception as e:
        print(f"Volume Error: {e}")
    finally:
        # 4. Clean up (Optional but good practice)
        try:
            comtypes.CoUninitialize()
        except:
            pass

# --- 4. BACKEND: GET INFO ---
async def get_media_info():
    info = {
        "title": "Nothing Playing", 
        "artist": "Windows Media", 
        "album": "",
        "is_playing": False
    }
    try:
        sessions = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        session = sessions.get_current_session()
        if session:
            props = await session.try_get_media_properties_async()
            info["title"] = props.title if props.title else "Unknown Title"
            info["artist"] = props.artist if props.artist else "Unknown Artist"
            
            # Check Playback Status
            playback_info = session.get_playback_info()
            if playback_info:
                info["is_playing"] = (playback_info.playback_status == 4)
    except:
        pass
    return info

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

# --- 5. FRONTEND ---
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
        button:active { transform: scale(0.95); opacity: 0.8; }
        button { transition: all 0.1s; touch-action: manipulation; }
        .hidden { display: none; }
    </style>
    <script>
        setInterval(async () => {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                document.getElementById('t').innerText = data.title;
                document.getElementById('a').innerText = data.artist;

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

    <div class="flex gap-8 mb-12">
        <button onclick="send('voldown')" class="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center shadow-lg border border-slate-700">
            <svg class="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M20 12H4"/></svg>
        </button>
        <button onclick="send('volup')" class="w-20 h-20 rounded-full bg-slate-800 flex items-center justify-center shadow-lg border border-slate-700">
            <svg class="w-8 h-8 text-slate-300" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
        </button>
    </div>

    <div class="flex items-center gap-6">
        <button onclick="send('prev')" class="p-4 text-slate-300 hover:text-white">
            <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M11 19V5l-9 7 9 7zM20 19V5l-9 7 9 7z"/></svg>
        </button>

        <button onclick="send('play')" class="w-24 h-24 rounded-full bg-blue-500 shadow-blue-500/50 shadow-2xl flex items-center justify-center text-white">
            <svg id="icon-play" class="w-10 h-10" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
            <svg id="icon-pause" class="w-10 h-10 hidden" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"></path></svg>
        </button>

        <button onclick="send('next')" class="p-4 text-slate-300 hover:text-white">
            <svg class="w-12 h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M4 5v14l9-7-9-7zM13 5v14l9-7-9-7z"/></svg>
        </button>
    </div>

</body>
</html>
"""

# --- 6. ROUTES ---
@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/status')
def status(): return jsonify(asyncio.run(get_media_info()))

@app.route('/control/<action>')
def control(action):
    # DIRECT VOLUME CONTROL (Bypasses Screensaver)
    if action == 'volup':
        change_volume(0.10) # Up 10%
    elif action == 'voldown':
        change_volume(-0.10) # Down 10%
    else:
        asyncio.run(media_action(action))
    return "", 204

if __name__ == '__main__':
    # Using 0.0.0.0 to allow access from iPhone
    app.run(host='0.0.0.0', port=5000)