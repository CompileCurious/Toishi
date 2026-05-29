import sqlite3
import os
from pathlib import Path


def get_db_path(data_dir: str) -> str:
    return str(Path(data_dir) / "toishi.db")


def get_connection(data_dir: str) -> sqlite3.Connection:
    db_path = get_db_path(data_dir)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(data_dir: str):
    conn = get_connection(data_dir)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source TEXT,
                imported_at TEXT,
                start_time TEXT,
                end_time TEXT,
                operator_notes TEXT
            );

            CREATE TABLE IF NOT EXISTS hosts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                ip TEXT,
                hostname TEXT,
                mac TEXT,
                os_guess TEXT,
                first_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS ports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                host_id INTEGER REFERENCES hosts(id) ON DELETE CASCADE,
                port INTEGER,
                proto TEXT,
                service TEXT
            );

            CREATE TABLE IF NOT EXISTS wifi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                ssid TEXT,
                bssid TEXT,
                signal_dbm INTEGER,
                channel INTEGER,
                security TEXT,
                first_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS ble (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                name TEXT,
                mac TEXT,
                rssi INTEGER,
                services TEXT,
                first_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                protocol TEXT,
                host TEXT,
                username TEXT,
                password TEXT,
                hash_type TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS hid_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
                timestamp TEXT,
                target TEXT,
                sequence TEXT,
                result TEXT,
                duration_ms INTEGER
            );
        """)
    conn.close()


def clear_all(data_dir: str):
    conn = get_connection(data_dir)
    with conn:
        conn.executescript("""
            DELETE FROM hid_log;
            DELETE FROM credentials;
            DELETE FROM ble;
            DELETE FROM wifi;
            DELETE FROM ports;
            DELETE FROM hosts;
            DELETE FROM sessions;
        """)
    conn.close()


def insert_session(conn: sqlite3.Connection, name: str, source: str, imported_at: str,
                   start_time: str, end_time: str, operator_notes: str) -> int:
    cur = conn.execute(
        "INSERT INTO sessions (name, source, imported_at, start_time, end_time, operator_notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, source, imported_at, start_time, end_time, operator_notes)
    )
    return cur.lastrowid


def insert_host(conn: sqlite3.Connection, session_id: int, ip: str, hostname: str,
                mac: str, os_guess: str, first_seen: str) -> int:
    cur = conn.execute(
        "INSERT INTO hosts (session_id, ip, hostname, mac, os_guess, first_seen) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, ip, hostname, mac, os_guess, first_seen)
    )
    return cur.lastrowid


def insert_port(conn: sqlite3.Connection, host_id: int, port: int, proto: str, service: str):
    conn.execute(
        "INSERT INTO ports (host_id, port, proto, service) VALUES (?, ?, ?, ?)",
        (host_id, port, proto, service)
    )


def insert_wifi(conn: sqlite3.Connection, session_id: int, ssid: str, bssid: str,
                signal_dbm: int, channel: int, security: str, first_seen: str):
    conn.execute(
        "INSERT INTO wifi (session_id, ssid, bssid, signal_dbm, channel, security, first_seen) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, ssid, bssid, signal_dbm, channel, security, first_seen)
    )


def insert_ble(conn: sqlite3.Connection, session_id: int, name: str, mac: str,
               rssi: int, services: str, first_seen: str):
    conn.execute(
        "INSERT INTO ble (session_id, name, mac, rssi, services, first_seen) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, name, mac, rssi, services, first_seen)
    )


def insert_credential(conn: sqlite3.Connection, session_id: int, protocol: str, host: str,
                      username: str, password: str, hash_type: str, timestamp: str):
    conn.execute(
        "INSERT INTO credentials (session_id, protocol, host, username, password, hash_type, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, protocol, host, username, password, hash_type, timestamp)
    )


def insert_hid_log(conn: sqlite3.Connection, session_id: int, timestamp: str, target: str,
                   sequence: str, result: str, duration_ms: int):
    conn.execute(
        "INSERT INTO hid_log (session_id, timestamp, target, sequence, result, duration_ms) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, timestamp, target, sequence, result, duration_ms)
    )


def list_sessions(data_dir: str) -> list[dict]:
    conn = get_connection(data_dir)
    rows = conn.execute("SELECT * FROM sessions ORDER BY imported_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(data_dir: str, session_id: int) -> dict | None:
    conn = get_connection(data_dir)
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        conn.close()
        return None

    sid = row["id"]

    hosts_rows = conn.execute("SELECT * FROM hosts WHERE session_id = ?", (sid,)).fetchall()
    hosts = []
    for h in hosts_rows:
        hd = dict(h)
        ports = conn.execute("SELECT * FROM ports WHERE host_id = ?", (h["id"],)).fetchall()
        hd["ports"] = [dict(p) for p in ports]
        hosts.append(hd)

    wifi_rows = conn.execute("SELECT * FROM wifi WHERE session_id = ?", (sid,)).fetchall()
    ble_rows = conn.execute("SELECT * FROM ble WHERE session_id = ?", (sid,)).fetchall()
    cred_rows = conn.execute("SELECT * FROM credentials WHERE session_id = ?", (sid,)).fetchall()
    hid_rows = conn.execute("SELECT * FROM hid_log WHERE session_id = ?", (sid,)).fetchall()

    conn.close()

    return {
        **dict(row),
        "hosts": hosts,
        "wifi": [dict(r) for r in wifi_rows],
        "ble": [dict(r) for r in ble_rows],
        "credentials": [dict(r) for r in cred_rows],
        "hid_log": [dict(r) for r in hid_rows],
    }


def get_session_counts(data_dir: str, session_id: int) -> dict:
    conn = get_connection(data_dir)
    sid = session_id
    hosts_count = conn.execute("SELECT COUNT(*) FROM hosts WHERE session_id = ?", (sid,)).fetchone()[0]
    ports_count = conn.execute(
        "SELECT COUNT(*) FROM ports WHERE host_id IN (SELECT id FROM hosts WHERE session_id = ?)", (sid,)
    ).fetchone()[0]
    wifi_count = conn.execute("SELECT COUNT(*) FROM wifi WHERE session_id = ?", (sid,)).fetchone()[0]
    ble_count = conn.execute("SELECT COUNT(*) FROM ble WHERE session_id = ?", (sid,)).fetchone()[0]
    cred_count = conn.execute("SELECT COUNT(*) FROM credentials WHERE session_id = ?", (sid,)).fetchone()[0]
    hid_count = conn.execute("SELECT COUNT(*) FROM hid_log WHERE session_id = ?", (sid,)).fetchone()[0]
    conn.close()
    return {
        "hosts": hosts_count,
        "open_ports": ports_count,
        "ssids": wifi_count,
        "ble_devices": ble_count,
        "credentials": cred_count,
        "hid_runs": hid_count,
    }
