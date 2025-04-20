# app.py

import logging
from flask import Flask
from config import Config
from entities import db
from interfaces.emotion_api import emotion_api
from interfaces.notes_api import notes_api
import os

# Configure logging to display all levels of messages to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder='interfaces/templates', static_folder='interfaces/static')
app.config.from_object(Config)

# Ensure directories exist
os.makedirs(app.config['PROCESSED_FRAMES_DIR'], exist_ok=True)
os.makedirs(app.config['ANNOTATED_VIDEOS_DIR'], exist_ok=True)

# Initialize SQLAlchemy
db.init_app(app)

# Register the blueprint
app.register_blueprint(emotion_api)
app.register_blueprint(notes_api)

with app.app_context():
    # Import models
    from entities.video import Video
    from entities.frame import Frame
    from entities.person import Person
    from entities.emotion import Emotion
    from entities.emotion_report import EmotionReport  # ← NUEVO
    from entities.emotion_report_notes import EmotionReportNote # ← NUEVO

    # Create the database tables

    db.create_all()

if __name__ == '__main__':
    logging.info("Starting Emotion Detection Microservice")
    app.run(host='0.0.0.0', port=5002, threaded=True)