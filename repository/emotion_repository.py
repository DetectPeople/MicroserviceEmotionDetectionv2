# MicroserviceEmotionDetection/repository/emotion_repository.py

from entities.emotion import Emotion
from entities import db


class EmotionRepository:
    def save(self, emotion):
        db.session.add(emotion)
        db.session.commit()

    def get_emotions_by_video_id(self, video_id):
        return Emotion.query.filter_by(video_id=video_id).all()

    def delete_emotions_by_video_id(self, video_id):
        emotions_to_delete = Emotion.query.filter_by(video_id=video_id).all()
        for emotion in emotions_to_delete:
            db.session.delete(emotion)
        db.session.commit()
