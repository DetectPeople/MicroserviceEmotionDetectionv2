# MicroserviceEmotionDetection/repository/video_repository.py

from entities.video import Video

class VideoRepository:
    def get_all(self):
        return Video.query.all()

    def get_by_id(self, video_id):
        return Video.query.get(video_id)