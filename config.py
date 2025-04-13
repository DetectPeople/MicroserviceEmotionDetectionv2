# MicroserviceEmotionDetection/config.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+mysqlconnector://root:root@localhost:3306/data_analysis'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROCESSED_FRAMES_DIR = os.path.join(BASE_DIR, 'processed_frames')
    ANNOTATED_VIDEOS_DIR = os.path.join(BASE_DIR, 'annotated_videos')
    # Existing configurations...
    MODELS_DIR = os.path.join(BASE_DIR, 'models')

    # Ensure directories exist
    os.makedirs(PROCESSED_FRAMES_DIR, exist_ok=True)
    os.makedirs(ANNOTATED_VIDEOS_DIR, exist_ok=True)


# Configurar la sesión de SQLAlchemy
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()