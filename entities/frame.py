# entities/frame.py

from entities import db
from sqlalchemy.orm import relationship

class Frame(db.Model):
    __tablename__ = 'frames'

    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    frame_number = db.Column(db.Integer, nullable=False)
    path = db.Column(db.String(255), nullable=False)

    # New columns for frame-level data
    average_brightness = db.Column(db.Float, nullable=True)
    contrast_ratio = db.Column(db.Float, nullable=True)
    background_complexity = db.Column(db.Float, nullable=True)
    color_temperature = db.Column(db.Float, nullable=True)
    sharpness = db.Column(db.Float, nullable=True)

    # Relationships
    emotions = db.relationship('Emotion', back_populates='frame', lazy=True)
    video = db.relationship('Video', back_populates='frames')

    def __repr__(self):
        return f'<Frame {self.frame_number} of Video {self.video_id}>'