import requests
from .ftp_client import FTPClient
from . import settings as settings_mod


class ConnectionManager:
    def __init__(self):
        self.mode: str = "disconnected"
        self.host: str = ""
        self.http_base: str = ""
        self._ftp_host: str = ""
        self._ftp_port: int = 2121
        self._ftp_user: str = ""
        self._ftp_password: str = ""

    def auto_detect(self) -> bool:
        try:
            resp = requests.get("http://192.168.7.1:8171/api/state", timeout=1.5)
            if resp.status_code == 200:
                self.mode = "usb"
                self.host = "192.168.7.1"
                self.http_base = "http://192.168.7.1:8171"
                cfg = settings_mod.load_settings()
                self._ftp_host = self.host
                self._ftp_port = int(cfg.get("ftp_port", 2121))
                self._ftp_user = cfg.get("ftp_user", "onikiri")
                self._ftp_password = cfg.get("ftp_password", "onikiri")
                return True
        except Exception:
            pass
        return False

    def connect_ftp(self, host: str, port: int, user: str, password: str) -> bool:
        try:
            client = FTPClient(host, port, user, password)
            with client:
                pass
            self.mode = "ftp"
            self.host = host
            self.http_base = f"http://{host}:8171"
            self._ftp_host = host
            self._ftp_port = port
            self._ftp_user = user
            self._ftp_password = password
            return True
        except Exception:
            return False

    def disconnect(self):
        self.mode = "disconnected"
        self.host = ""
        self.http_base = ""
        self._ftp_host = ""
        self._ftp_port = 2121
        self._ftp_user = ""
        self._ftp_password = ""

    def api_get(self, path: str) -> dict:
        if self.mode == "disconnected":
            raise ConnectionError("Not connected")
        resp = requests.get(f"{self.http_base}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()

    def api_post(self, path: str, body: dict) -> dict:
        if self.mode == "disconnected":
            raise ConnectionError("Not connected")
        resp = requests.post(f"{self.http_base}{path}", json=body, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_ftp_client(self) -> FTPClient:
        return FTPClient(self._ftp_host, self._ftp_port, self._ftp_user, self._ftp_password)

    def status_dict(self) -> dict:
        return {
            "connected": self.mode != "disconnected",
            "mode": self.mode,
            "host": self.host,
            "http_base": self.http_base,
            "ftp_host": self._ftp_host,
            "ftp_port": self._ftp_port,
        }
