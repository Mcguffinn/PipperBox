import os
from flask import Flask, render_template_string, send_from_directory, jsonify

app = Flask(__name__)

# Get backend URL from environment variable
BACKEND_URL = os.environ.get('BACKEND_URL', 'https://your-backend-url.com')

# Inline HTML template (since Vercel has specific file structure requirements)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎤 Pipperbox TTS</title>
    <link rel="stylesheet" href="/static/base.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0;
            padding: 2em;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .top-nav {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        .nav-bar a {
            color: white;
            margin: 0 10px;
            text-decoration: none;
            transition: all 0.3s ease;
        }
        .nav-bar a:hover {
            transform: scale(1.1);
            color: #ffd700;
        }
        h1 {
            text-align: center;
            color: #4a5568;
            margin-bottom: 2rem;
            font-size: 2.5rem;
        }
        .form-group {
            margin-bottom: 1.5rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #4a5568;
        }
        textarea, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
            box-sizing: border-box;
        }
        textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
        }
        textarea {
            min-height: 120px;
            resize: vertical;
        }
        .voice-info {
            font-size: 14px;
            color: #718096;
            margin-top: 5px;
            font-style: italic;
        }
        .button-group {
            display: flex;
            gap: 1rem;
            margin-top: 2rem;
        }
        button {
            flex: 1;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        #synthesizeBtn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        #synthesizeBtn:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102,126,234,0.3);
        }
        #synthesizeBtn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        #downloadBtn {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            display: none;
        }
        #downloadBtn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(72,187,120,0.3);
        }
        .status {
            padding: 12px;
            border-radius: 8px;
            margin: 1rem 0;
            font-weight: 500;
        }
        .status.success {
            background-color: #f0fff4;
            color: #22543d;
            border: 1px solid #9ae6b4;
        }
        .status.error {
            background-color: #fed7d7;
            color: #742a2a;
            border: 1px solid #feb2b2;
        }
        .status.loading {
            background-color: #ebf8ff;
            color: #2c5282;
            border: 1px solid #90cdf4;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .audio-player {
            margin-top: 2rem;
            text-align: center;
            display: none;
        }
        audio {
            width: 100%;
            max-width: 500px;
            margin: 1rem 0;
        }
    </style>
</head>
<body>
    <div class="top-nav">
        <nav class="nav-bar">
            <a href="https://github.com/pipperbox/pipperbox-frontend" target="_blank" title="GitHub">
                <i class="fab fa-github fa-2x"></i>
            </a>
            <a href="https://blog.edwinderonvil.com" target="_blank" title="Blog">
                <i class="fas fa-blog fa-2x"></i>
            </a>
        </nav>
    </div>
    
    <div class="container">
        <h1>🎤 PiperBox</h1>
        
        <form id="ttsForm">
            <div class="form-group">
                <label for="text">Text to Synthesize:</label>
                <textarea 
                    id="text" 
                    name="text" 
                    placeholder="Enter the text you want to convert to speech..."
                    required
                ></textarea>
            </div>
            
            <div class="form-group">
                <label for="voice">Select Voice:</label>
                <select id="voice" name="voice" required>
                    <option value="">Loading voices...</option>
                </select>
                <div class="voice-info" id="voiceInfo"></div>
            </div>
            
            <div class="button-group">
                <button type="submit" id="synthesizeBtn">
                    🎵 Generate Speech
                </button>
                <button type="button" id="downloadBtn">
                    📥 Download Audio
                </button>
            </div>
        </form>
        
        <div id="status" class="status" style="display: none;"></div>
        
        <div class="audio-player" id="audioPlayer">
            <audio controls id="audioElement">
                Your browser does not support the audio element.
            </audio>
        </div>
    </div>

    <script>
        const API_BASE = '{{ backend_url }}';
        let currentAudioUrl = null;

        // Voice information mapping
        const voiceInfo = {
            'en_US-lessac-medium': 'English (US) - Clear, professional female voice',
            'en_US-lessac-high': 'English (US) - Clear, professional female voice',
            'en_US-ryan-high': 'English (US) - Clear, professional male voice',
            'en_US-amy-high': 'English (US) - Warm, friendly female voice',
            'en_GB-alba-high': 'English (UK) - British accent, clear female voice',
            'es_ES-maragda-high': 'Spanish (Spain) - European Spanish, female voice',
            'es_MX-ald-high': 'Spanish (Mexico) - Mexican Spanish, male voice'
        };

        // Load available voices on page load
        async function loadVoices() {
            try {
                const response = await fetch(`${API_BASE}/api/voices`);
                const data = await response.json();
                
                const voiceSelect = document.getElementById('voice');
                voiceSelect.innerHTML = '<option value="">Select a voice...</option>';
                
                if (data.voices && data.voices.length > 0) {
                    data.voices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = `${voice.name} (${voice.lang})`;
                        voiceSelect.appendChild(option);
                    });
                } else {
                    // Fallback to default voices if API doesn't return any
                    const defaultVoices = [
                        { id: 'en_US-lessac-medium', name: 'Lessac (Female)', lang: 'en_US' },
                        { id: 'en_US-lessac-high', name: 'Lessac (Female)', lang: 'en_US' },
                        { id: 'en_US-ryan-high', name: 'Ryan (Male)', lang: 'en_US' },
                        { id: 'en_US-amy-high', name: 'Amy (Female)', lang: 'en_US' },
                        { id: 'en_GB-alba-high', name: 'Alba (Female)', lang: 'en_GB' },
                        { id: 'es_ES-maragda-high', name: 'Maragda (Female)', lang: 'es_ES' },
                        { id: 'es_MX-ald-high', name: 'Ald (Male)', lang: 'es_MX' }
                    ];
                    
                    defaultVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.id;
                        option.textContent = `${voice.name} (${voice.lang})`;
                        voiceSelect.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error loading voices:', error);
                showStatus('Failed to load voices. Please check if the backend is running.', 'error');
                
                // Show default voices on error
                const voiceSelect = document.getElementById('voice');
                voiceSelect.innerHTML = `
                    <option value="">Select a voice...</option>
                    <option value="en_US-lessac-medium">Lessac (Female Medium) - en_US</option>
                    <option value="en_US-lessac-high">Lessac (Female High) - en_US</option>
                    <option value="en_US-ryan-high">Ryan (Male High) - en_US</option>
                    <option value="en_US-amy-high">Amy (Female High) - en_US</option>
                    <option value="en_GB-alba-high">Alba (Female High) - en_GB</option>
                    <option value="es_ES-maragda-high">Maragda (Female High) - es_ES</option>
                    <option value="es_MX-ald-high">Ald (Male High) - es_MX</option>
                `;
            }
        }

        // Update voice info when selection changes
        document.getElementById('voice').addEventListener('change', function() {
            const selectedVoice = this.value;
            const voiceInfoElement = document.getElementById('voiceInfo');
            
            if (selectedVoice && voiceInfo[selectedVoice]) {
                voiceInfoElement.textContent = voiceInfo[selectedVoice];
            } else {
                voiceInfoElement.textContent = '';
            }
        });

        // Show status message
        function showStatus(message, type) {
            const statusElement = document.getElementById('status');
            statusElement.textContent = message;
            statusElement.className = `status ${type}`;
            statusElement.style.display = 'block';
            
            if (type === 'loading') {
                statusElement.classList.add('loading');
            } else {
                statusElement.classList.remove('loading');
            }
        }

        // Hide status message
        function hideStatus() {
            document.getElementById('status').style.display = 'none';
        }

        // Handle form submission
        document.getElementById('ttsForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const text = document.getElementById('text').value.trim();
            const voice = document.getElementById('voice').value;
            const synthesizeBtn = document.getElementById('synthesizeBtn');
            
            if (!text || !voice) {
                showStatus('Please enter text and select a voice.', 'error');
                return;
            }
            
            // Disable button and show loading
            synthesizeBtn.disabled = true;
            synthesizeBtn.textContent = '🔄 Generating...';
            showStatus('Generating speech audio...', 'loading');
            
            try {
                const response = await fetch(`${API_BASE}/api/synthesize`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        voice: voice
                    })
                });
                
                const data = await response.json();
                
                if (response.ok && data.url) {
                    currentAudioUrl = `${API_BASE}${data.url}`;
                    
                    // Show audio player
                    const audioElement = document.getElementById('audioElement');
                    const audioPlayer = document.getElementById('audioPlayer');
                    
                    audioElement.src = currentAudioUrl;
                    audioPlayer.style.display = 'block';
                    
                    // Show download button
                    document.getElementById('downloadBtn').style.display = 'block';
                    
                    showStatus('✅ Speech generated successfully!', 'success');
                    
                    // Auto-play the audio
                    try {
                        await audioElement.play();
                    } catch (e) {
                        console.log('Auto-play prevented by browser');
                    }
                } else {
                    throw new Error(data.error || 'Unknown error occurred');
                }
            } catch (error) {
                console.error('Error:', error);
                showStatus(`❌ Error: ${error.message}`, 'error');
            } finally {
                // Re-enable button
                synthesizeBtn.disabled = false;
                synthesizeBtn.textContent = '🎵 Generate Speech';
            }
        });

        // Handle download button
        document.getElementById('downloadBtn').addEventListener('click', function() {
            if (currentAudioUrl) {
                const link = document.createElement('a');
                link.href = currentAudioUrl;
                link.download = `speech_${Date.now()}.wav`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                showStatus('📥 Audio download started!', 'success');
            }
        });

        // Load voices when page loads
        window.addEventListener('load', loadVoices);
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, backend_url=BACKEND_URL)

@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "message": "Frontend server is running"})

# Export the app for Vercel
application = app

if __name__ == "__main__":
    app.run(debug=True)