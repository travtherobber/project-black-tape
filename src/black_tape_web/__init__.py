from __future__ import annotations

import os
import secrets
from hmac import compare_digest

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from black_tape_web.blueprints.api import api_bp
from black_tape_web.blueprints.ui import ui_bp
from black_tape_web.services.vault_service import VaultService


def create_app() -> Flask:
    load_dotenv()

    instance_root = os.getenv("BLACKTAPE_INSTANCE_ROOT")
    if not instance_root:
        instance_root = "/tmp/black-tape-instance" if os.getenv("RENDER") else None

    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=instance_root,
        static_folder="static",
        template_folder="templates",
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("BLACKTAPE_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))
    app.config["UPLOAD_ROOT"] = os.path.join(app.instance_path, "uploads")
    app.config["CACHE_ROOT"] = os.path.join(app.instance_path, "vault_cache")
    app.config["BLACKTAPE_CACHE_TTL"] = int(os.getenv("BLACKTAPE_CACHE_TTL", "900"))
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    app.config["MAX_UPLOAD_FILES"] = int(os.getenv("BLACKTAPE_MAX_UPLOAD_FILES", "256"))
    app.config["MAX_ARCHIVE_JSON_BYTES"] = int(os.getenv("BLACKTAPE_MAX_ARCHIVE_JSON_BYTES", str(32 * 1024 * 1024)))
    app.config["MAX_ARCHIVE_TOTAL_BYTES"] = int(os.getenv("BLACKTAPE_MAX_ARCHIVE_TOTAL_BYTES", str(80 * 1024 * 1024)))
    app.config["BLACKTAPE_PASSWORD"] = os.getenv("BLACKTAPE_PASSWORD", "").strip()

    os.makedirs(app.config["UPLOAD_ROOT"], exist_ok=True)
    os.makedirs(app.config["CACHE_ROOT"], exist_ok=True)

    app.extensions["vault_service"] = VaultService(
        upload_root=app.config["UPLOAD_ROOT"],
        cache_root=app.config["CACHE_ROOT"],
        ttl_seconds=app.config["BLACKTAPE_CACHE_TTL"],
        max_upload_files=app.config["MAX_UPLOAD_FILES"],
        max_archive_json_bytes=app.config["MAX_ARCHIVE_JSON_BYTES"],
        max_archive_total_bytes=app.config["MAX_ARCHIVE_TOTAL_BYTES"],
    )

    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def require_password_gate():
        open_endpoints = {"ui.login", "ui.login_submit", "api.health", "static"}
        if not app.config.get("BLACKTAPE_PASSWORD"):
            return None
        if request.endpoint in open_endpoints:
            return None
        if request.endpoint and request.endpoint.startswith("static"):
            return None
        if session.get("authenticated"):
            return None
        return redirect(url_for("ui.login", next=request.path))

    @app.context_processor
    def inject_csrf_token():
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return {"csrf_token": token, "auth_required": bool(app.config.get("BLACKTAPE_PASSWORD"))}

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(_error: RequestEntityTooLarge):
        return {
            "status": "ERROR",
            "message": "Upload exceeds the server size limit.",
        }, 413

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        if request.path.startswith("/api/") or request.path == "/upload":
            return {
                "status": "ERROR",
                "message": error.description or "Request failed.",
            }, error.code
        return error

    app.extensions["blacktape_compare_digest"] = compare_digest
    return app
