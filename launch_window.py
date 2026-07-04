"""Launch Music Agent in a standalone desktop window using pywebview.

Starts the FastAPI backend server and opens a native window pointing to it.
Portable: auto-detects Python environment across devices.
"""

import sys
import os
import time
import threading
import socket

def _setup_paths():
    """Auto-detect and add venv site-packages to path."""
    here = os.path.dirname(os.path.abspath(__file__))
    
    # Strategy 1: project-local .venv
    local_venv = os.path.join(here, '.venv', 'Lib', 'site-packages')
    if os.path.isdir(local_venv):
        sys.path.insert(0, local_venv)
        return

    # Strategy 2: read pyvenv.cfg from nearby venvs
    candidates = [
        os.path.join(here, '.venv'),
        os.path.join(os.path.dirname(here), 'jieshi10', '.venv'),
        os.path.join(os.path.dirname(here), '.venv'),
    ]
    for venv_dir in candidates:
        cfg_path = os.path.join(venv_dir, 'pyvenv.cfg')
        sp_path = os.path.join(venv_dir, 'Lib', 'site-packages')
        if os.path.isfile(cfg_path) and os.path.isdir(sp_path):
            sys.path.insert(0, sp_path)
            return

def find_free_port(start=8000, end=9000):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 8000

def run_server(port):
    """Run the FastAPI server in a background thread."""
    import uvicorn
    server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
    sys.path.insert(0, server_dir)
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )

def main():
    _setup_paths()
    port = find_free_port(8000)
    print(f"[Launcher] Starting server on port {port}")

    # Start server in background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    print("[Launcher] Waiting for server to start...")
    for i in range(30):
        try:
            import httpx
            r = httpx.get(f"http://127.0.0.1:{port}/api/health", timeout=2)
            if r.status_code == 200:
                print(f"[Launcher] Server ready on port {port}")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        print("[Launcher] Server may not be ready, opening window anyway...")

    # Open native window
    import webview
    window = webview.create_window(
        "Music Agent - AI 编曲工作站",
        f"http://127.0.0.1:{port}",
        width=1400,
        height=900,
        min_size=(1000, 700),
        resizable=True,
        text_select=True,
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()
