import os
import time
import uuid
import logging
import threading
import diskcache
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Core Project Modules
from core.orchestrator import Orchestrator
from core.search_engine import SignalSearch

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BLACK-TAPE")

# 1. Load local .env (if it exists)
load_dotenv()

app = Flask(__name__)

# 2. Priority Handshake: Looks for Render Env, then .env, then Falls back
# This replaces the 3 conflicting lines from your previous snippet.
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'blacktape_industrial_99')

# 3. File & Upload Limits
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- STABILITY LAYER: DISKCACHE ---
# Ensure .vault_cache exists and is configured for production
cache_dir = os.path.join(os.getcwd(), '.vault_cache')
os.makedirs(cache_dir, exist_ok=True)
vault_cache = diskcache.Cache(cache_dir)
TTL_SECONDS = int(os.getenv("BLACKTAPE_CACHE_TTL", 3600))

# Initialize the engine
orchestrator = Orchestrator()

def background_ingestion(job_id, filename, file_path):
    """
    The 'Siphon' - Processes data and preserves counts for the UI.
    """
    try:
        logger.info(f"[Job {job_id}] Initializing background protocol for {filename}")
        results = orchestrator.process_file(job_id, filename, file_path)

        if results:
            # 1. Store the heavy data
            vault_cache.set(f"{job_id}_data", results, expire=TTL_SECONDS)

            # 2. Update status to COMPLETE but KEEP the counts for the Dashboard bars
            msg_count = sum(len(msgs) for msgs in results.get("chats", {}).values())
            gps_count = len(results.get("gps", []))

            final_status = {
                "status": "COMPLETE",
                "messages_found": msg_count,
                "gps_found": gps_count,
                "last_update": time.time()
            }
            vault_cache.set(f"{job_id}_status", final_status, expire=TTL_SECONDS)

            logger.info(f"[Job {job_id}] Signal alignment verified. {msg_count} MSGS // {gps_count} GPS.")
        else:
            vault_cache.set(f"{job_id}_status", {"status": "FAILED"}, expire=TTL_SECONDS)

    except Exception as e:
        logger.error(f"[Job {job_id}] Critical failure: {str(e)}", exc_info=True)
        vault_cache.set(f"{job_id}_status", {"status": "ERROR", "message": str(e)}, expire=TTL_SECONDS)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- UI ROUTES ---
@app.route('/')
def welcome(): return render_template('welcome.html')

@app.route('/dashboard')
def dashboard(): return render_template('pages/home.html')

@app.route('/chats')
def chat_view(): return render_template('pages/chat.html')

@app.route('/map')
def map_view(): return render_template('pages/map.html')

# --- API: INGESTION PROTOCOL ---
@app.route('/upload', methods=['POST'])
def upload_signal():
    if 'file' not in request.files:
        return jsonify({"status": "ERROR", "message": "No signal packets found"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "ERROR", "message": "Null filename"}), 400

    job_id = str(uuid.uuid4())
    session['current_job'] = job_id

    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    file.save(temp_path)

    vault_cache.set(f"{job_id}_status", "PROCESSING", expire=TTL_SECONDS)

    thread = threading.Thread(target=background_ingestion, args=(job_id, filename, temp_path))
    thread.start()

    return jsonify({
        "status": "ACCEPTED",
        "job_id": job_id,
        "message": "Ingestion protocol initiated."
    }), 202

@app.route('/api/vault/status')
def get_ingestion_status():
    job_id = request.args.get('job_id') or session.get('current_job')
    if not job_id:
        return jsonify({"status": "INACTIVE"})

    status_data = vault_cache.get(f"{job_id}_status", "UNKNOWN")
    if isinstance(status_data, dict):
        return jsonify(status_data)

    return jsonify({"status": status_data, "job_id": job_id})

# --- API: DATA RETRIEVAL ---

@app.route('/api/conversations')
def list_conversations():
    job_id = request.args.get('job_id') or session.get('current_job')
    if not job_id:
        return jsonify({"status": "EMPTY", "payload": []})

    data = vault_cache.get(f"{job_id}_data")
    if not data:
        status_info = vault_cache.get(f"{job_id}_status", "UNKNOWN")
        current_status = status_info.get('status') if isinstance(status_info, dict) else status_info
        if current_status == "PROCESSING":
            return jsonify({"status": "PROCESSING", "payload": []})
        return jsonify({"status": "EXPIRED", "message": "Vault empty"}), 401

    payload = []
    chats = data.get("chats", {})
    for cid, messages in chats.items():
        if not messages: continue
        payload.append({
            "id": cid,
            "count": len(messages),
            "last_message": messages[-1].get("Created", "N/A")
        })

    logger.info(f"[Job {job_id}] Dispatching {len(payload)} chat clusters to UI.")
    return jsonify({"status": "SUCCESS", "payload": payload})

@app.route('/api/conversations/<path:convo_id>')
def get_conversation_details(convo_id):
    job_id = request.args.get('job_id') or session.get('current_job')
    data = vault_cache.get(f"{job_id}_data")

    if not data or "chats" not in data or convo_id not in data["chats"]:
        return jsonify({"status": "ERROR", "message": "Conversation not found"}), 404

    return jsonify({"status": "SUCCESS", "payload": data["chats"][convo_id]})

@app.route('/api/gps')
def get_gps_data():
    job_id = request.args.get('job_id') or session.get('current_job')
    data = vault_cache.get(f"{job_id}_data")

    if not data or "gps" not in data:
        return jsonify({"status": "SUCCESS", "payload": []})

    return jsonify({"status": "SUCCESS", "payload": data["gps"]})

@app.route('/api/search')
def perform_search():
    query = request.args.get('q', '').strip()
    job_id = request.args.get('job_id') or session.get('current_job')

    data = vault_cache.get(f"{job_id}_data")
    if not data or "chats" not in data:
        return jsonify({"status": "ERROR", "message": "Vault expired"}), 401

    engine = SignalSearch(data["chats"])
    results = engine.execute(query)
    return jsonify({"status": "SUCCESS", "results": results})

@app.route('/api/clear', methods=['POST'])
def clear_session():
    job_id = session.get('current_job')
    if job_id:
        vault_cache.delete(f"{job_id}_data")
        vault_cache.delete(f"{job_id}_status")
    session.clear()
    return jsonify({"status": "SUCCESS", "message": "Vault purged"})

@app.route('/health')
def health():
    return jsonify({"status": "ONLINE", "timestamp": time.time()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
