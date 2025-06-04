import os
import subprocess
import uuid
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Allow all origins for development; adjust for production

# ── CONFIG ─────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Where Piper will cache/download its ONNX (.onnx + .onnx.json).
PIPER_DATA_DIR = os.path.join(BASE_DIR, "piper_data")
os.makedirs(PIPER_DATA_DIR, exist_ok=True)

# Where synthesized WAV files go:
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Default high-quality voices
DEFAULT_VOICES = [
    {
        "id": "en_US-lessac-high",
        "name": "Lessac (Female)",
        "lang": "en_US",
        "description": "Clear, professional female voice"
    },
    {
        "id": "en_US-amy-high", 
        "name": "Amy (Female)",
        "lang": "en_US",
        "description": "Warm, friendly female voice"
    },
    {
        "id": "en_GB-alba-high",
        "name": "Alba (Female)", 
        "lang": "en_GB",
        "description": "British accent, clear female voice"
    },
    {
        "id": "es_ES-maragda-high",
        "name": "Maragda (Female)",
        "lang": "es_ES", 
        "description": "European Spanish, female voice"
    },
    {
        "id": "es_MX-ald-high",
        "name": "Ald (Male)",
        "lang": "es_MX",
        "description": "Mexican Spanish, male voice"
    }
]

# ── ROUTES ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def healthcheck():
    return jsonify({"status": "ok", "message": "Piper-TTS API is running"}), 200

@app.route("/api/voices", methods=["GET"])
def api_voices():
    """
    Lists available high quality English and Spanish voices.
    """
    voices = []
    
    # Check for downloaded voices in piper_data directory
    for voice in DEFAULT_VOICES:
        voice_id = voice["id"]
        # Look for the voice file in subdirectories
        model_path = None
        for root, dirs, files in os.walk(PIPER_DATA_DIR):
            for file in files:
                if file == f"{voice_id}.onnx":
                    model_path = os.path.join(root, file)
                    break
            if model_path:
                break
        
        if model_path and os.path.exists(model_path):
            voices.append(voice)
            logger.info(f"Found voice model: {voice_id}")
        else:
            logger.warning(f"Voice model not found: {voice_id}")
    
    # If no voices found, return default list anyway for frontend
    if not voices:
        logger.warning("No voice models found, returning default list")
        voices = DEFAULT_VOICES
    
    logger.info(f"Returning {len(voices)} voices")
    return jsonify({"voices": voices})

@app.route("/api/synthesize", methods=["POST"])
def api_synthesize():
    """
    Expects JSON: { "text": "Your text here", "voice": "voice_id" }
    Returns JSON: { "url": "/outputs/<filename>.wav" }
    """
    data = request.get_json(silent=True)
    if not data or "text" not in data or "voice" not in data:
        logger.error("Missing required fields in request")
        return jsonify({"error": "Missing 'text' or 'voice' field"}), 400

    text = data["text"].strip()
    voice = data["voice"].strip()
    if not text or not voice:
        logger.error("Empty text or voice provided")
        return jsonify({"error": "Empty text or voice"}), 400

    logger.info(f"Synthesizing text (length: {len(text)}) with voice: {voice}")

    # 1) Create a unique filename for the WAV
    filename = f"{uuid.uuid4().hex}.wav"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 2) Find the .onnx file for the selected voice
    model_path = None
    for root, dirs, files in os.walk(PIPER_DATA_DIR):
        for file in files:
            if file == f"{voice}.onnx":
                model_path = os.path.join(root, file)
                break
        if model_path:
            break
    
    if not model_path:
        logger.error(f"Voice model not found: {voice}")
        return jsonify({"error": f"Voice model '{voice}' not found"}), 400

    logger.info(f"Using model: {model_path}")

    # 3) Build Piper command
    cmd = [
        "piper",
        "-m", model_path,
        "-f", filepath,
        "--data-dir", PIPER_DATA_DIR,
        "--download-dir", PIPER_DATA_DIR,
    ]

    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
            text=False,
            timeout=60  # 60 second timeout
        )
        logger.info("Piper synthesis completed successfully")
    except subprocess.TimeoutExpired:
        logger.error("Piper synthesis timed out")
        return jsonify({"error": "Speech synthesis timed out"}), 500
    except subprocess.CalledProcessError as e:
        logger.error(f"Piper failed with exit code {e.returncode}")
        logger.error(f"Stderr: {e.stderr.decode() if e.stderr else 'No stderr'}")
        return jsonify({"error": f"Piper failed (exit code {e.returncode})"}), 500
    except FileNotFoundError:
        logger.error("Piper binary not found")
        return jsonify({"error": "Piper binary not found in PATH. Did you install piper-tts?"}), 500

    # 4) Verify the output file was created
    if not os.path.exists(filepath):
        logger.error(f"Output file not created: {filepath}")
        return jsonify({"error": "Audio file generation failed"}), 500

    file_size = os.path.getsize(filepath)
    logger.info(f"Audio file created successfully: {filename} ({file_size} bytes)")
    return jsonify({"url": f"/outputs/{filename}"}), 200

@app.route("/outputs/<path:filename>", methods=["GET"])
def serve_wav(filename):
    """
    Serves the generated WAV from the outputs/ folder.
    """
    try:
        logger.info(f"Serving audio file: {filename}")
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)
    except FileNotFoundError:
        logger.error(f"Audio file not found: {filename}")
        return jsonify({"error": "Audio file not found"}), 404

@app.route("/api/status", methods=["GET"])
def api_status():
    """
    Returns API status and available voices count.
    """
    voice_count = len([f for f in os.listdir(PIPER_DATA_DIR) if f.endswith('.onnx')])
    return jsonify({
        "status": "running",
        "version": "1.0.0",
        "voices_available": voice_count,
        "piper_data_dir": PIPER_DATA_DIR,
        "output_dir": OUTPUT_DIR
    })

# ── ERROR HANDLERS ──────────────────────────────────────────────
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Request too large"}), 413

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

# ── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Piper TTS API server...")
    logger.info(f"Piper data directory: {PIPER_DATA_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    
    # Check if piper binary is available
    try:
        subprocess.run(["piper", "--help"], capture_output=True, check=True)
        logger.info("Piper binary found and working")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("Piper binary not found or not working")
    
    # Listen on 0.0.0.0 so Docker's port-mapping works
    app.run(host="0.0.0.0", port=5600, debug=False)