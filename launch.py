"""Music Agent - Standalone Window Launcher.

Starts the FastAPI server in a background thread and opens
a native window (no browser needed).
"""

import sys
import os
import threading
import time
import socket

# Add server dir to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(SCRIPT_DIR, "server")
sys.path.insert(0, SERVER_DIR)

# Find a free port
def find_free_port(start=8000):
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start

PORT = find_free_port()

def run_server():
    """Run uvicorn server in background thread."""
    import uvicorn
    os.chdir(SERVER_DIR)
    config = uvicorn.Config(
        "app:app",
        host="127.0.0.1",
        port=PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server.run()

# Start server thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for server to be ready
url = f"http://127.0.0.1:{PORT}"
print(f"Starting server on {url} ...")

import urllib.request
for i in range(30):
    try:
        urllib.request.urlopen(f"{url}/api/health", timeout=1)
        print("Server ready!")
        break
    except Exception:
        time.sleep(0.5)
else:
    print("Server startup timeout, trying to open anyway...")

# Open native window
import webview

window = webview.create_window(
    title="Music Agent - AI 编曲工作站",
    url=url,
    width=1400,
    height=900,
    min_size=(1000, 600),
    resizable=True,
    text_select=True,
)

webview.start(gui="edgechromium", debug=False)
