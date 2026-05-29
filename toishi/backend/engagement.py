import os
import json
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .connection import ConnectionManager
from . import db as db_mod
from . import settings as settings_mod


class EngagementManager:
    def __init__(self, conn_mgr: ConnectionManager):
        self.conn = conn_mgr

    def _data_dir(self) -> str:
        cfg = settings_mod.load_settings()
        return os.path.expandvars(cfg.get("data_dir", os.path.join(os.environ.get("APPDATA", ""), "Toishi")))

    def _engagements_dir(self) -> str:
        d = os.path.join(self._data_dir(), "engagements")
        os.makedirs(d, exist_ok=True)
        return d

    def remote_list(self) -> dict:
        return self.conn.api_get("/api/engagement/list")

    def remote_pack(self, session_name: str) -> dict:
        return self.conn.api_post("/api/engagement/pack", {"session": session_name})

    def remote_delete(self, session_name: str) -> dict:
        return self.conn.api_post("/api/engagement/delete", {"session": session_name})

    def pull(self, session_name: str, ftp_path: str) -> dict:
        engagements_dir = self._engagements_dir()
        local_archive = os.path.join(engagements_dir, f"{session_name}.tar.gz")

        ftp_client = self.conn.get_ftp_client()
        with ftp_client:
            ftp_client.download(ftp_path, local_archive)

        data_dir = self._data_dir()
        db_mod.init_db(data_dir)
        session_id = self._import_archive(local_archive, session_name, data_dir)
        return {"status": "ok", "session_id": session_id}

    def _import_archive(self, archive_path: str, session_name: str, data_dir: str) -> int:
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(tmpdir)

            meta = {}
            meta_path = os.path.join(tmpdir, "meta.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)

            imported_at = datetime.now(timezone.utc).isoformat()
            conn = db_mod.get_connection(data_dir)
            with conn:
                session_id = db_mod.insert_session(
                    conn,
                    name=meta.get("session_name", session_name),
                    source="onikiri",
                    imported_at=imported_at,
                    start_time=meta.get("start_time", ""),
                    end_time=meta.get("end_time", ""),
                    operator_notes=meta.get("operator_notes", ""),
                )

                hosts_path = os.path.join(tmpdir, "hosts.json")
                if os.path.exists(hosts_path):
                    with open(hosts_path) as f:
                        hosts_data = json.load(f)
                    for h in hosts_data:
                        host_id = db_mod.insert_host(
                            conn, session_id,
                            ip=h.get("ip", ""),
                            hostname=h.get("hostname", ""),
                            mac=h.get("mac", ""),
                            os_guess=h.get("os_guess", ""),
                            first_seen=h.get("first_seen", ""),
                        )
                        for p in h.get("open_ports", []):
                            db_mod.insert_port(
                                conn, host_id,
                                port=p.get("port", 0),
                                proto=p.get("proto", ""),
                                service=p.get("service", ""),
                            )

                wifi_path = os.path.join(tmpdir, "wifi.json")
                if os.path.exists(wifi_path):
                    with open(wifi_path) as f:
                        wifi_data = json.load(f)
                    for w in wifi_data:
                        db_mod.insert_wifi(
                            conn, session_id,
                            ssid=w.get("ssid", ""),
                            bssid=w.get("bssid", ""),
                            signal_dbm=w.get("signal_dbm", 0),
                            channel=w.get("channel", 0),
                            security=w.get("security", ""),
                            first_seen=w.get("first_seen", ""),
                        )

                ble_path = os.path.join(tmpdir, "ble.json")
                if os.path.exists(ble_path):
                    with open(ble_path) as f:
                        ble_data = json.load(f)
                    for b in ble_data:
                        services = json.dumps(b.get("services", []))
                        db_mod.insert_ble(
                            conn, session_id,
                            name=b.get("name", ""),
                            mac=b.get("mac", ""),
                            rssi=b.get("rssi", 0),
                            services=services,
                            first_seen=b.get("first_seen", ""),
                        )

                creds_path = os.path.join(tmpdir, "credentials.json")
                if os.path.exists(creds_path):
                    with open(creds_path) as f:
                        creds_data = json.load(f)
                    for c in creds_data:
                        db_mod.insert_credential(
                            conn, session_id,
                            protocol=c.get("protocol", ""),
                            host=c.get("host", ""),
                            username=c.get("username", ""),
                            password=c.get("password", ""),
                            hash_type=c.get("hash_type", ""),
                            timestamp=c.get("timestamp", ""),
                        )

                hid_path = os.path.join(tmpdir, "hid_log.json")
                if os.path.exists(hid_path):
                    with open(hid_path) as f:
                        hid_data = json.load(f)
                    for entry in hid_data:
                        db_mod.insert_hid_log(
                            conn, session_id,
                            timestamp=entry.get("timestamp", ""),
                            target=entry.get("target", ""),
                            sequence=entry.get("sequence", ""),
                            result=entry.get("result", ""),
                            duration_ms=entry.get("duration_ms", 0),
                        )

            conn.close()
            return session_id

    def local_list(self) -> list[dict]:
        return db_mod.list_sessions(self._data_dir())

    def local_get(self, session_id: int) -> dict | None:
        data = db_mod.get_session(self._data_dir(), session_id)
        if data is None:
            return None
        counts = db_mod.get_session_counts(self._data_dir(), session_id)
        data["counts"] = counts
        return data

    def export_csv(self, session_id: int) -> str:
        import csv
        import io
        data = db_mod.get_session(self._data_dir(), session_id)
        if data is None:
            return ""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["protocol", "host", "username", "password", "hash_type", "timestamp"])
        for c in data.get("credentials", []):
            writer.writerow([c.get("protocol"), c.get("host"), c.get("username"),
                             c.get("password"), c.get("hash_type"), c.get("timestamp")])
        return output.getvalue()
