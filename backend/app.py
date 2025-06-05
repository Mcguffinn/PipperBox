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

# Enhanced CORS configuration for production
CORS(app, 
     origins=[
         "https://piperbox-hxw9oif5u-mcguffinns-projects.vercel.app",
         "https://your-custom-domain.com",           # Replace with your custom domain if you have one
         "http://localhost:3000",                    # For local development
         "http://localhost:5173",                    # For Vite dev server
         "https://localhost:3000",                   # For local HTTPS development
     ],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True
)

# ── CONFIG ─────────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Where Piper will cache/download its ONNX (.onnx + .onnx.json).
PIPER_DATA_DIR = os.path.join(BASE_DIR, "piper_data")
os.makedirs(PIPER_DATA_DIR, exist_ok=True)

# Where synthesized WAV files go:
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# FIX: Piper binary path detection
def find_piper_binary():
    """Find the piper binary in various possible locations"""
    possible_paths = [
        "piper",  # In PATH
        "/usr/local/bin/piper",  # Common location
        "/usr/local/bin/piper/piper",  # Docker location
        "/usr/bin/piper",
        "/opt/piper/piper"
    ]
    
    for path in possible_paths:
        try:
            result = subprocess.run([path, "--help"], capture_output=True, timeout=5)
            if result.returncode == 0:
                logger.info(f"Found piper binary at: {path}")
                return path
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            continue
    
    logger.error("Piper binary not found in any expected location")
    return None

# Get piper binary path
PIPER_BINARY = find_piper_binary()

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

# ── SECURITY MIDDLEWARE ────────────────────────────────────────
@app.after_request
def after_request(response):
    # Security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    # Only add HSTS for HTTPS
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # CORS headers for all requests
    origin = request.headers.get('Origin')
    if origin and any(origin.startswith(allowed) for allowed in [
        'https://piperbox-',
        'https://localhost:3000',
        'http://localhost:3000',
        'http://localhost:5173'
    ]):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response.headers['Access-Control-Max-Age'] = '86400'
    
    return response

# ── ROUTES ─────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def healthcheck():
    return jsonify({
        "status": "healthy", 
        "message": "Piper-TTS API is running",
        "version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "production"),
        "piper_binary": PIPER_BINARY is not None
    }), 200

@app.route("/api/health", methods=["GET"])
def health():
    """Detailed health check for load balancers"""
    piper_status = "healthy" if PIPER_BINARY else "unhealthy"
    
    if PIPER_BINARY:
        try:
            subprocess.run([PIPER_BINARY, "--help"], capture_output=True, check=True, timeout=5)
            piper_status = "healthy"
        except:
            piper_status = "unhealthy"
    
    voice_count = 0
    try:
        voice_count = len([f for f in os.listdir(PIPER_DATA_DIR) if f.endswith('.onnx')])
    except:
        pass
    
    return jsonify({
        "status": "healthy" if piper_status == "healthy" else "unhealthy",
        "piper": piper_status,
        "piper_binary_path": PIPER_BINARY,
        "voices_loaded": voice_count,
        "disk_space_ok": True,
        "timestamp": str(uuid.uuid4())
    }), 200

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

@app.route("/api/synthesize", methods=["POST", "OPTIONS"])
def api_synthesize():
    """
    Expects JSON: { "text": "Your text here", "voice": "voice_id" }
    Returns JSON: { "url": "/outputs/<filename>.wav" }
    """
    if request.method == "OPTIONS":
        return "", 200
    
    # Check if piper binary is available
    if not PIPER_BINARY:
        logger.error("Piper binary not available")
        return jsonify({"error": "Text-to-speech service is not available. Piper binary not found."}), 503
    
    data = request.get_json(silent=True)
    if not data or "text" not in data or "voice" not in data:
        logger.error("Missing required fields in request")
        return jsonify({"error": "Missing 'text' or 'voice' field"}), 400

    text = data["text"].strip()
    voice = data["voice"].strip()
    
    # Input validation
    if not text or not voice:
        logger.error("Empty text or voice provided")
        return jsonify({"error": "Empty text or voice"}), 400
    
    if len(text) > 5000:  # Limit text length
        logger.error("Text too long")
        return jsonify({"error": "Text too long (max 5000 characters)"}), 400

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
        PIPER_BINARY,
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
        logger.error("Piper binary not found during execution")
        return jsonify({"error": "Piper binary not found. Please check installation."}), 500

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
        response = send_from_directory(OUTPUT_DIR, filename, as_attachment=False)
        
        # Add cache headers for audio files
        response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
        response.headers['Content-Type'] = 'audio/wav'
        
        return response
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
        "output_dir": OUTPUT_DIR,
        "piper_binary": PIPER_BINARY,
        "piper_available": PIPER_BINARY is not None,
        "environment": os.environ.get("ENVIRONMENT", "production")
    })

# ── ERROR HANDLERS ──────────────────────────────────────────────
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "Request too large"}), 413

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded"}), 429

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

# ── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Starting Piper TTS API server...")
    logger.info(f"Piper data directory: {PIPER_DATA_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Piper binary: {PIPER_BINARY}")
    
    # Check if piper binary is available
    if PIPER_BINARY:
        try:
            subprocess.run([PIPER_BINARY, "--help"], capture_output=True, check=True)
            logger.info("Piper binary found and working")
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Piper binary not working properly")
    else:
        logger.error("Piper binary not found - API will not work properly")
    
    # Listen on 0.0.0.0 so Docker's port-mapping works
    # In production, this will be behind gunicorn
    port = int(os.environ.get("PORT", 5600))
    app.run(host="0.0.0.0", port=port, debug=False)