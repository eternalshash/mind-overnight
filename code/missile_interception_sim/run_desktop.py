#!/usr/bin/env python3
"""
================================================================================
IAMD GLOBAL DEFENSE SIMULATOR: ONE-COMMAND DESKTOP LAUNCHER
File: run_desktop.py
================================================================================
One-command native desktop deployment providing an isolated desktop application
window via `pywebview` (using macOS native Cocoa/WebKit window) wrapping the tactical
HUD with OpenStreetMap and CartoDB Dark Matter tiles (100% open-source, zero API keys).

Does NOT require the user to manage a separate web browser or cloud environment:
simply execute:
    python run_desktop.py

Command-line options:
    --native           : Launch native CustomTkinter + TkinterMapView GUI directly (desktop_gui.py)
    --port <port>      : Local HTTP port for the embedded engine (default: 8050 or auto-discovered)
    --theater <name>   : Initial tactical theater (eastern_europe, persian_gulf, taiwan_strait, conus_homeland)
    --fullscreen       : Launch in fullscreen desktop mode
    --headless-check   : Verify embedded server startup and tile layer access without opening GUI
================================================================================
"""

import argparse
import os
import socket
import sys
import threading
import time
import urllib.request
from typing import Optional

try:
    import webview
except ImportError:
    print("[ERROR] 'pywebview' is required for standalone desktop mode. Install via 'pip install pywebview'.")
    sys.exit(1)


# ==============================================================================
# 1. NETWORK & PORT UTILITIES
# ==============================================================================

def find_available_port(preferred_port: int = 8050, host: str = "127.0.0.1") -> int:
    """Finds an open TCP port starting from preferred_port."""
    port = preferred_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                port += 1
    return preferred_port


def wait_for_server(url: str, timeout: float = 12.0) -> bool:
    """Polls the local server endpoint until HTTP 200 is received or timeout expires."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


# ==============================================================================
# 2. EMBEDDED DASH SERVER BACKGROUND THREAD
# ==============================================================================

def start_embedded_server(host: str, port: int) -> threading.Thread:
    """Launches the Dash application in a daemon background thread."""
    # Ensure current working directory is on sys.path
    cwd = os.path.dirname(os.path.abspath(__file__))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    import app as dash_app

    def run():
        # Run Flask/Dash without reloader so it doesn't try to spawn child processes
        dash_app.app.run(host=host, port=port, debug=False, use_reloader=False)

    server_thread = threading.Thread(target=run, daemon=True)
    server_thread.start()
    return server_thread


# ==============================================================================
# 3. MAIN LAUNCHER ENTRYPOINT
# ==============================================================================

def launch_desktop(
    port: Optional[int] = None,
    host: str = "127.0.0.1",
    fullscreen: bool = False,
    headless_check: bool = False,
    theater: str = "eastern_europe"
) -> int:
    """Spawns embedded server and opens macOS Cocoa/WebKit desktop window."""
    target_port = find_available_port(port if port else 8050, host=host)
    app_url = f"http://{host}:{target_port}/"

    print("=" * 80)
    print("IAMD GLOBAL DEFENSE SIMULATOR: NATIVE DESKTOP DEPLOYMENT")
    print(f"Server Target: {app_url}")
    print(f"Active Theater: {theater}")
    print("Map Engine: Open-Source Zero-API-Key (CartoDB Dark Matter / OpenStreetMap)")
    print("=" * 80)

    # Launch embedded server daemon
    print(f"[LAUNCHER] Starting embedded tactical simulation server on {host}:{target_port}...")
    start_embedded_server(host=host, port=target_port)

    # Wait for server readiness
    print("[LAUNCHER] Waiting for tactical HUD engine to initialize...")
    if not wait_for_server(app_url, timeout=15.0):
        print("[ERROR] Embedded server failed to respond within timeout window.")
        return 1

    print("✓ Tactical HUD engine online and ready.")

    if headless_check:
        print("[HEADLESS CHECK] Server verified successfully on HTTP 200. Exiting cleanly.")
        return 0

    # Create native standalone desktop window via pywebview (macOS Cocoa / WebKit)
    print("[LAUNCHER] Initializing native Cocoa/WebKit desktop window...")
    window = webview.create_window(
        title="IAMD GLOBAL DEFENSE SIMULATOR - TACTICAL COMMAND & CONTROL",
        url=app_url,
        width=1480,
        height=920,
        min_size=(1024, 720),
        resizable=True,
        text_select=True,
        fullscreen=fullscreen,
        confirm_close=False,
    )

    print("[LAUNCHER] Running desktop window event loop. Close window to exit.")
    webview.start(debug=False)
    print("[LAUNCHER] Desktop application terminated cleanly.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="IAMD Global Defense Simulator Standalone Desktop Application"
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Launch the native CustomTkinter/TkinterMapView GUI (desktop_gui.py) directly"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Local HTTP port for the embedded engine (default: 8050 or auto-discovered)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Local interface to bind (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--theater",
        type=str,
        default="eastern_europe",
        choices=["eastern_europe", "persian_gulf", "taiwan_strait", "conus_homeland"],
        help="Initial theater preset"
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Launch window in fullscreen mode"
    )
    parser.add_argument(
        "--headless-check",
        action="store_true",
        help="Verify embedded server boots, returns HTTP 200, and exits cleanly"
    )

    args = parser.parse_args()

    if args.native:
        import desktop_gui
        app_inst = desktop_gui.TacticalDesktopApp(headless=False, theater_key=args.theater)
        app_inst.run()
        return 0

    return launch_desktop(
        port=args.port,
        host=args.host,
        fullscreen=args.fullscreen,
        headless_check=args.headless_check,
        theater=args.theater
    )


if __name__ == "__main__":
    sys.exit(main())
