# entities/video.py

from datetime import datetime
from entities import db
from sqlalchemy.orm import relationship

class Video(db.Model):
    __tablename__ = 'videos'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    path = db.Column(db.String(255), nullable=False)

    # Relationships
    frames = db.relationship('Frame', back_populates='video', lazy=True)
    persons = db.relationship('Person', back_populates='video', lazy=True)

    def __repr__(self):
        return f'<Video {self.filename}>'
