import os
import base64
from pathlib import Path

from .connection import ConnectionManager
from . import settings as settings_mod


class PayloadManager:
    def __init__(self, conn_mgr: ConnectionManager):
        self.conn = conn_mgr

    def _data_dir(self) -> str:
        cfg = settings_mod.load_settings()
        return os.path.expandvars(cfg.get("data_dir", os.path.join(os.environ.get("APPDATA", ""), "Toishi")))

    def _staging_dir(self) -> str:
        d = os.path.join(self._data_dir(), "payloads")
        os.makedirs(d, exist_ok=True)
        return d

    def remote_list(self) -> dict:
        return self.conn.api_get("/api/payload/list")

    def remote_push(self, filename: str, data_b64: str) -> dict:
        data = base64.b64decode(data_b64)
        ftp_client = self.conn.get_ftp_client()
        with ftp_client:
            import io
            buf = io.BytesIO(data)
            ftp_client._ftp.storbinary(f"STOR /userdata/payloads/{filename}", buf)
        return {"status": "ok", "filename": filename}

    def remote_pull(self, filename: str) -> dict:
        downloads = os.path.join(os.path.expandvars("%USERPROFILE%"), "Downloads") \
            if os.name == "nt" else os.path.expanduser("~/Downloads")
        os.makedirs(downloads, exist_ok=True)
        local_path = os.path.join(downloads, filename)
        ftp_client = self.conn.get_ftp_client()
        with ftp_client:
            ftp_client.download(f"/userdata/payloads/{filename}", local_path)
        return {"status": "ok", "saved_to": local_path}

    def remote_create(self, size_mb: int) -> dict:
        return self.conn.api_post("/api/payload/create", {"size_mb": size_mb})

    def remote_clear(self) -> dict:
        return self.conn.api_post("/api/payload/clear", {})

    def local_list(self) -> list[dict]:
        staging = self._staging_dir()
        files = []
        for name in os.listdir(staging):
            full = os.path.join(staging, name)
            if os.path.isfile(full):
                files.append({"name": name, "size_bytes": os.path.getsize(full)})
        return files

    def local_add(self, filename: str, data_b64: str) -> dict:
        data = base64.b64decode(data_b64)
        dest = os.path.join(self._staging_dir(), Path(filename).name)
        with open(dest, "wb") as f:
            f.write(data)
        return {"status": "ok", "filename": Path(filename).name}

    def local_clear(self) -> dict:
        staging = self._staging_dir()
        removed = []
        for name in os.listdir(staging):
            full = os.path.join(staging, name)
            if os.path.isfile(full):
                os.remove(full)
                removed.append(name)
        return {"status": "ok", "removed": removed}

    def push_all_to_device(self) -> dict:
        staging = self._staging_dir()
        pushed = []
        ftp_client = self.conn.get_ftp_client()
        with ftp_client:
            for name in os.listdir(staging):
                full = os.path.join(staging, name)
                if os.path.isfile(full):
                    ftp_client.upload(full, f"/userdata/payloads/{name}")
                    pushed.append(name)
        return {"status": "ok", "pushed": pushed}
