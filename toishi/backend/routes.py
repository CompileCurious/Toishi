from flask import Blueprint, request, jsonify, Response

from .connection import ConnectionManager
from .engagement import EngagementManager
from .payload import PayloadManager
from . import settings as settings_mod
from . import db as db_mod

bp = Blueprint("api", __name__)

_conn_mgr = ConnectionManager()
_eng_mgr = EngagementManager(_conn_mgr)
_pay_mgr = PayloadManager(_conn_mgr)


def _err(msg: str, code: int = 400):
    return jsonify({"error": msg}), code


# ─── Connection ───────────────────────────────────────────────────────────────

@bp.get("/api/connection/status")
def connection_status():
    return jsonify(_conn_mgr.status_dict())


@bp.post("/api/connection/auto_detect")
def connection_auto_detect():
    found = _conn_mgr.auto_detect()
    return jsonify({"found": found, "host": _conn_mgr.host if found else None})


@bp.post("/api/connection/connect_ftp")
def connection_connect_ftp():
    body = request.get_json(force=True) or {}
    host = body.get("host", "")
    port = int(body.get("port", 2121))
    user = body.get("user", "")
    password = body.get("password", "")
    if not host or not user:
        return _err("host and user are required")
    ok = _conn_mgr.connect_ftp(host, port, user, password)
    return jsonify({"connected": ok, "mode": _conn_mgr.mode})


@bp.post("/api/connection/disconnect")
def connection_disconnect():
    _conn_mgr.disconnect()
    return jsonify({"status": "ok"})


@bp.get("/api/connection/device_info")
def connection_device_info():
    try:
        data = _conn_mgr.api_get("/api/state")
        return jsonify(data)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 502)


# ─── Engagement ───────────────────────────────────────────────────────────────

@bp.get("/api/engagement/remote/list")
def engagement_remote_list():
    try:
        data = _eng_mgr.remote_list()
        return jsonify(data)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 502)


@bp.post("/api/engagement/remote/pack")
def engagement_remote_pack():
    body = request.get_json(force=True) or {}
    session = body.get("session", "")
    if not session:
        return _err("session required")
    try:
        data = _eng_mgr.remote_pack(session)
        return jsonify(data)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 502)


@bp.post("/api/engagement/remote/delete")
def engagement_remote_delete():
    body = request.get_json(force=True) or {}
    session = body.get("session", "")
    if not session:
        return _err("session required")
    try:
        data = _eng_mgr.remote_delete(session)
        return jsonify(data)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 502)


@bp.post("/api/engagement/pull")
def engagement_pull():
    body = request.get_json(force=True) or {}
    session = body.get("session", "")
    ftp_path = body.get("ftp_path", "")
    if not session or not ftp_path:
        return _err("session and ftp_path required")
    try:
        result = _eng_mgr.pull(session, ftp_path)
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


@bp.get("/api/engagement/local/list")
def engagement_local_list():
    return jsonify(_eng_mgr.local_list())


@bp.get("/api/engagement/local/<int:session_id>")
def engagement_local_get(session_id: int):
    data = _eng_mgr.local_get(session_id)
    if data is None:
        return _err("not found", 404)
    return jsonify(data)


@bp.post("/api/engagement/export_csv")
def engagement_export_csv():
    body = request.get_json(force=True) or {}
    session_id = body.get("session_id")
    if session_id is None:
        return _err("session_id required")
    csv_content = _eng_mgr.export_csv(int(session_id))
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=credentials_{session_id}.csv"},
    )


# ─── Payload ──────────────────────────────────────────────────────────────────

@bp.get("/api/payload/remote/list")
def payload_remote_list():
    try:
        data = _pay_mgr.remote_list()
        return jsonify(data)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 502)


@bp.post("/api/payload/remote/push")
def payload_remote_push():
    body = request.get_json(force=True) or {}
    filename = body.get("filename", "")
    data_b64 = body.get("data_b64", "")
    if not filename or not data_b64:
        return _err("filename and data_b64 required")
    try:
        result = _pay_mgr.remote_push(filename, data_b64)
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/payload/remote/pull")
def payload_remote_pull():
    body = request.get_json(force=True) or {}
    filename = body.get("filename", "")
    if not filename:
        return _err("filename required")
    try:
        result = _pay_mgr.remote_pull(filename)
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/payload/remote/create")
def payload_remote_create():
    body = request.get_json(force=True) or {}
    size_mb = int(body.get("size_mb", 64))
    try:
        result = _pay_mgr.remote_create(size_mb)
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/payload/remote/clear")
def payload_remote_clear():
    try:
        result = _pay_mgr.remote_clear()
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


@bp.get("/api/payload/local/list")
def payload_local_list():
    return jsonify(_pay_mgr.local_list())


@bp.post("/api/payload/local/add")
def payload_local_add():
    body = request.get_json(force=True) or {}
    filename = body.get("filename", "")
    data_b64 = body.get("data_b64", "")
    if not filename or not data_b64:
        return _err("filename and data_b64 required")
    try:
        result = _pay_mgr.local_add(filename, data_b64)
        return jsonify(result)
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/payload/local/clear")
def payload_local_clear():
    try:
        result = _pay_mgr.local_clear()
        return jsonify(result)
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/payload/remote/push_all")
def payload_remote_push_all():
    try:
        result = _pay_mgr.push_all_to_device()
        return jsonify(result)
    except ConnectionError as e:
        return _err(str(e), 503)
    except Exception as e:
        return _err(str(e), 500)


# ─── Settings ─────────────────────────────────────────────────────────────────

@bp.get("/api/settings")
def settings_get():
    return jsonify(settings_mod.get_public_settings())


@bp.post("/api/settings")
def settings_post():
    body = request.get_json(force=True) or {}
    try:
        settings_mod.save_settings(body)
        return jsonify({"status": "ok"})
    except Exception as e:
        return _err(str(e), 500)


@bp.post("/api/settings/clear_db")
def settings_clear_db():
    cfg = settings_mod.load_settings()
    import os
    data_dir = os.path.expandvars(cfg.get("data_dir", ""))
    try:
        db_mod.clear_all(data_dir)
        return jsonify({"status": "ok"})
    except Exception as e:
        return _err(str(e), 500)
