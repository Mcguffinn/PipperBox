import os
from flask import Flask, render_template, send_from_directory

app = Flask(__name__)

BACKEND_URL = os.environ.get('BACKEND_URL', 'http://192.168.1.75:{BACKEND_PORT}')

@app.route('/')
def index():
    return render_template('index.html', backend_url=BACKEND_URL)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/health')
def health_check():
    return {"status": "ok", "message": "Frontend server is running"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('FRONTEND_PORT', 5000), debug=False)