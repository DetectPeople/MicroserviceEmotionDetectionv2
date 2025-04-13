from entities.frame import Frame
from entities import db  # Importamos db del módulo de entidades

class FrameRepository:
    def get_frames_by_video_id(self, video_id):
        # Utilizar db.session si estás usando Flask-SQLAlchemy
        return db.session.query(Frame).filter_by(video_id=video_id).order_by(Frame.frame_number).all()

    def get_all(self):
        # Obtener todos los registros de Frame usando db.session
        return db.session.query(Frame).all()