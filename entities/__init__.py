# entities/__init__.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models to register them with SQLAlchemy
from entities.video import Video
from entities.frame import Frame
from entities.person import Person
from entities.emotion import Emotion
from entities.emotion_report import EmotionReport
from entities.emotion_report_notes import EmotionReportNote