import sys
import socket
import threading
import time
import subprocess
from pathlib import Path

import requests
import webview
from flask import Flask, send_from_directory

BASE = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).parent
FRONTEND = BASE / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND), static_url_path="")


@app.route("/")
def index():
    return send_from_directory(str(FRONTEND), "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(FRONTEND), filename)


from toishi.backend.routes import bp  # noqa: E402
app.register_blueprint(bp)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_flask(port: int, attempts: int = 10, delay: float = 0.1) -> bool:
    url = f"http://127.0.0.1:{port}/api/connection/status"
    for _ in range(attempts):
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


class ToishiAPI:
    def open_file_dialog(self, title: str = "Open File", multiple: bool = False):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=multiple,
            file_types=("All files (*.*)",),
        )
        if result is None:
            return []
        return list(result)

    def save_file_dialog(self, title: str = "Save File", filename: str = ""):
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=filename,
        )
        if result is None:
            return None
        return result if isinstance(result, str) else result[0]

    def open_folder(self, path: str):
        if sys.platform == "win32":
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["xdg-open", path])


def main():
    port = _find_free_port()

    flask_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()

    _wait_for_flask(port)

    api = ToishiAPI()
    window = webview.create_window(
        "TOISHI — ONIKIRI COMPANION",
        f"http://127.0.0.1:{port}",
        width=1200,
        height=750,
        min_size=(900, 600),
        js_api=api,
    )
    webview.start()


if __name__ == "__main__":
    main()
