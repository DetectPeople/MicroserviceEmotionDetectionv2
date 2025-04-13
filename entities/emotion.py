# entities/emotion.py

from entities import db
from sqlalchemy.orm import relationship

class Emotion(db.Model):
    __tablename__ = 'emotions'

    id = db.Column(db.Integer, primary_key=True)
    frame_id = db.Column(db.Integer, db.ForeignKey('frames.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('persons.id'), nullable=True)
    emotion_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    bbox = db.Column(db.String(255), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    person_identity = db.Column(db.String(100), nullable=True)  # New field for person identity

    # Relationships
    frame = db.relationship('Frame', back_populates='emotions')
    person = db.relationship('Person', back_populates='emotions')

    def __repr__(self):
        return f'<Emotion {self.emotion_type} with confidence {self.confidence} for Person {self.person_identity}>'
