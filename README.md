# Toishi 砥石

**Toishi** ("whetstone") is the Windows companion desktop application for the **Onikiri Mk.I** field toolkit. It is the operator's workstation for reviewing engagement data, staging payloads, and communicating with a connected Onikiri device over USB-RNDIS or FTP.

---

## Features

| Module | What it does |
|--------|-------------|
| **Connect** | Auto-detects Onikiri via USB-RNDIS (`192.168.7.1`) or connects manually via FTP. Shows live device info (uptime, modules, firmware). |
| **Engagement** | Lists, packs, and pulls session archives from the device. Extracts and imports hosts, ports, Wi-Fi, BLE, credentials, and HID run logs into a local SQLite database. Provides sortable tables, a channel congestion strip, and CSV export. |
| **Payload** | Pushes and pulls payload files to/from the Onikiri device. Manages a local staging folder. Supports single-file push, pull-to-Downloads, create a 64 MB image, and full staging clear. |
| **Settings** | Encrypted settings file (AES-128 Fernet, machine-stable key). Configures FTP credentials, data directory, auto-connect, and theme. Includes a database wipe option. |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.12 |
| UI engine | [pywebview](https://pywebview.flowrl.com/) — native OS window wrapping a local webview |
| HTTP server | Flask (loopback, dynamic port) |
| File transfer | `ftplib` (stdlib) |
| Database | `sqlite3` (stdlib) |
| Encryption | `cryptography` — Fernet / AES-128 |
| Packaging | PyInstaller `--onefile --noconsole` → `Toishi.exe` |

---

## Project Structure

```
Toishi/
├── toishi/
│   ├── main.py                  # Entry: Flask thread → pywebview window
│   ├── backend/
│   │   ├── connection.py        # ConnectionManager (USB-RNDIS + FTP)
│   │   ├── engagement.py        # EngagementManager (pack/pull/import)
│   │   ├── payload.py           # PayloadManager (push/pull/stage)
│   │   ├── db.py                # SQLite schema + parameterised CRUD
│   │   ├── settings.py          # Fernet-encrypted settings
│   │   ├── ftp_client.py        # ftplib context-manager wrapper
│   │   └── routes.py            # All Flask Blueprint routes
│   └── frontend/
│       ├── index.html           # Single-page app
│       ├── app.js               # All view logic, API calls, rendering
│       └── styles.css           # Onikiri Mk.I dark theme
├── Icon.ico                     # Application icon (window, taskbar, exe)
├── toishi.spec                  # PyInstaller build spec
├── requirements.txt
└── .github/workflows/
    └── build-release.yml        # CI: build exe → GitHub prerelease
```

---

## Getting Started (development)

### Prerequisites

- Python 3.12
- Windows (pywebview's WinForms backend) — or Linux/macOS for dev with a compatible pywebview backend

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
cd /path/to/Toishi
python -m toishi.main
```

### Build `.exe`

```bash
pyinstaller toishi.spec
# Output: dist/Toishi.exe
```

---

## Releases

Every push to `main` triggers a GitHub Actions build on `windows-latest` that produces a single-file `Toishi.exe` (~20 MB, zero runtime dependencies) and publishes it as a prerelease tagged `prerelease-YYYYMMDD-HHMMSS`.

Download the latest build from the [Releases](../../releases) page.

---

## Connecting to Onikiri

### USB (recommended)

1. Connect the Onikiri device via USB.
2. Open the **CONNECT** view and press **AUTO-DETECT USB**.
3. If found, status changes to `● CONNECTED (USB)`.

### FTP (network)

1. Enter the device IP, port (`2121`), username (`onikiri`), and password.
2. Press **CONNECT VIA FTP**.

---

## Local Database

Engagement data is stored in `%APPDATA%\Toishi\toishi.db` (SQLite). The schema covers:

- `sessions` — top-level engagement metadata
- `hosts` + `ports` — discovered hosts and their open ports
- `wifi` — scanned SSIDs with signal, channel, and security
- `ble` — Bluetooth LE devices
- `credentials` — captured protocol credentials / hashes
- `hid_log` — HID payload run results

---

## Settings

Settings are stored encrypted at `%APPDATA%\Toishi\settings.json`. The encryption key is derived from the machine's hardware UUID via PBKDF2-SHA256, so the file is not portable between machines.

| Setting | Default |
|---------|---------|
| FTP Host | `192.168.7.1` |
| FTP Port | `2121` |
| FTP Username | `onikiri` |
| FTP Password | `onikiri` |
| Data Directory | `%APPDATA%\Toishi` |
| Auto-Connect | `true` |
| Theme | `dark` |

---

## Security Notes

- FTP credentials are stored encrypted at rest; the password is never returned in plaintext by the API (`••••••••` is returned for display).
- All SQLite queries use parameterised statements — no string interpolation.
- The Flask server binds to `127.0.0.1` only; it is not reachable from the network.
- The pywebview window has no browser chrome and cannot navigate away from the local server.

---

## License

Private / operational use only. Not for public distribution.
