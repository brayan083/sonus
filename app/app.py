import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

from routes import all_blueprints

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", 2048)) * 1024 * 1024

socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=50 * 1024 * 1024)

for bp in all_blueprints:
    app.register_blueprint(bp)

# Import realtime events (registers socketio handlers)
from routes.realtime import register_socketio_events
register_socketio_events(socketio)


@app.errorhandler(413)
def too_large(e):
    max_mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return f"El archivo es demasiado grande. Maximo: {max_mb} MB.", 413


if __name__ == "__main__":
    socketio.run(
        app,
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", 5001)),
    )
