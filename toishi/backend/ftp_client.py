import ftplib
from pathlib import Path


class FTPClient:
    def __init__(self, host: str, port: int, user: str, password: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self._ftp: ftplib.FTP | None = None

    def __enter__(self) -> "FTPClient":
        self._ftp = ftplib.FTP()
        self._ftp.connect(self.host, self.port, timeout=10)
        self._ftp.login(self.user, self.password)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                pass
            self._ftp = None

    def download(self, remote_path: str, local_path: str):
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            self._ftp.retrbinary(f"RETR {remote_path}", f.write)

    def upload(self, local_path: str, remote_path: str):
        with open(local_path, "rb") as f:
            self._ftp.storbinary(f"STOR {remote_path}", f)

    def listdir(self, remote_path: str) -> list[str]:
        return self._ftp.nlst(remote_path)
