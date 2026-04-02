from flask import Blueprint, current_app, jsonify, request, session


api_bp = Blueprint("api", __name__)
ALLOWED_UPLOAD_EXTENSIONS = {".zip", ".json"}


def vault_service():
    return current_app.extensions["vault_service"]


@api_bp.before_request
def protect_mutations():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None

    csrf_token = session.get("_csrf_token")
    request_token = request.headers.get("X-CSRF-Token")
    if not csrf_token or not request_token or csrf_token != request_token:
        return jsonify({"status": "ERROR", "message": "CSRF validation failed"}), 403
    return None


@api_bp.post("/upload")
def upload_signal():
    uploaded_files = [item for item in request.files.getlist("file") if item and item.filename]
    if not uploaded_files:
        return jsonify({"status": "ERROR", "message": "No file provided"}), 400
    for uploaded_file in uploaded_files:
        extension = f".{uploaded_file.filename.rsplit('.', 1)[-1].lower()}" if "." in uploaded_file.filename else ""
        if extension not in ALLOWED_UPLOAD_EXTENSIONS:
            return jsonify({"status": "ERROR", "message": "Unsupported file type"}), 400

    job_id = vault_service().create_job(uploaded_files)
    session["current_job"] = job_id
    return jsonify(
        {
            "status": "ACCEPTED",
            "job_id": job_id,
            "file_count": len(uploaded_files),
            "message": "Ingestion protocol initiated.",
        }
    ), 202


@api_bp.get("/api/vault/status")
def get_ingestion_status():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "IDLE"})
    return jsonify(vault_service().get_status(job_id))


@api_bp.get("/api/conversations")
def list_conversations():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "EMPTY", "payload": []})

    status = vault_service().get_status(job_id)
    if status.get("status") == "PROCESSING":
        return jsonify({"status": "PROCESSING", "payload": []})

    payload = vault_service().list_conversations(job_id)
    return jsonify({"status": "SUCCESS", "payload": payload})


@api_bp.get("/api/conversations/<path:convo_id>")
def get_conversation_details(convo_id: str):
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "ERROR", "message": "No active vault"}), 400
    payload = vault_service().get_conversation(job_id, convo_id)
    if payload is None:
        return jsonify({"status": "ERROR", "message": "Conversation not found"}), 404
    return jsonify({"status": "SUCCESS", "payload": payload})


@api_bp.get("/api/gps")
def get_gps():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "SUCCESS", "payload": []})
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_gps(job_id)})


@api_bp.get("/api/friends")
def get_friends():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "SUCCESS", "payload": {"categories": {}, "summary": {}, "ranking": {}}})
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_friends(job_id)})


@api_bp.get("/api/timeline")
def get_timeline():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "SUCCESS", "payload": []})
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_timeline(job_id)})


@api_bp.get("/api/analytics")
def get_analytics():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "SUCCESS", "payload": {"overview": {}, "chat": {}, "gps": {}, "friends": {}, "google": {}}})
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_analytics(job_id)})


@api_bp.get("/api/explore")
def get_explore():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "SUCCESS", "payload": {"sources": [], "identity": [], "google_signals": [], "other": []}})
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_explore(job_id)})


@api_bp.get("/api/search")
def search():
    job_id = request.args.get("job_id") or session.get("current_job")
    query = request.args.get("q", "").strip()
    if not job_id:
        return jsonify({"status": "ERROR", "message": "No active vault"}), 400
    return jsonify({"status": "SUCCESS", "results": vault_service().search(job_id, query)})


@api_bp.post("/api/clear")
def clear():
    job_id = session.get("current_job")
    if job_id:
        vault_service().clear(job_id)
    session.clear()
    return jsonify({"status": "SUCCESS", "message": "Vault purged"})


@api_bp.post("/api/vault/reset-expiry")
def reset_expiry():
    job_id = request.args.get("job_id") or session.get("current_job")
    if not job_id:
        return jsonify({"status": "ERROR", "message": "No active vault"}), 400
    if not vault_service().reset_expiry(job_id):
        return jsonify({"status": "ERROR", "message": "Vault not found or already expired"}), 404
    return jsonify({"status": "SUCCESS", "payload": vault_service().get_status(job_id)})


@api_bp.get("/health")
def health():
    return jsonify({"status": "ONLINE", "app": "black-tape-overhaul"})
