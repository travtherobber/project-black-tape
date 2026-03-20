# ===============================
# PROJECT BLACK-TAPE
# server.py (Local Test Runner)
# ===============================

import os
from flask import Flask, request, jsonify, render_template
from core.orchestrator import Orchestrator

# Initialize Flask with paths pointing to your tree structure
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# Initialize the Brain
dark_ops = Orchestrator()

# --- ROUTES ---

@app.route('/')
def index():
    """Renders the main dashboard."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def handle_upload():
    """
    Handles file uploads, passes them to the orchestrator,
    and returns JSON results to the frontend.
    """
    if 'file' not in request.files:
        return jsonify({"status": "ERROR", "message": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"status": "ERROR", "message": "No selected file"}), 400

    try:
        # The orchestrator handles the Scan -> Process -> Export flow
        # It returns a dictionary of processed data
        results = dark_ops.process_file(file.filename, file)

        return jsonify({
            "status": "SUCCESS",
            "filename": file.filename,
            "payload": results
        })

    except Exception as e:
        print(f"[!] SERVER ERROR: {str(e)}")
        return jsonify({"status": "SERVER_ERROR", "message": str(e)}), 500

# --- DEVELOPMENT RUNNER ---

if __name__ == '__main__':
    # Ensure uploads directory exists locally
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    print("""
    =========================================
    PROJECT BLACK-TAPE : TACTICAL SERVER
    =========================================
    STATUS: LOCAL_TEST_MODE
    HOST: http://127.0.0.1:5000
    INTEL: Monitoring for ingest...
    =========================================
    """)

    # debug=True is essential for your dev work; it auto-reloads
    # the server when you change your Python code.
    app.run(host='127.0.0.1', port=5000, debug=True)
