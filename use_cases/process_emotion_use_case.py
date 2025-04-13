import requests
import time
import logging
from repository.video_repository import VideoRepository
from repository.frame_repository import FrameRepository
from repository.emotion_repository import EmotionRepository
from repository.person_repository import PersonRepository
from services.emotion_detection_service import EmotionDetectionService
from services.video_generation_service import VideoGenerationService
from entities import db
from entities.emotion import Emotion
from config import Config
import os
import numpy as np

class ProcessEmotionUseCase:
    def __init__(self):
        self.video_repository = VideoRepository()
        self.frame_repository = FrameRepository()
        self.emotion_repository = EmotionRepository()
        self.person_repository = PersonRepository()
        self.emotion_service = EmotionDetectionService()
        self.video_generation_service = VideoGenerationService()

    def execute(self, video_id):
        video = self.video_repository.get_by_id(video_id)
        if not video:
            raise ValueError('Video not found')

        # Check if frames already exist for the video
        frames = self.frame_repository.get_frames_by_video_id(video_id)
        logging.info(f"Initial frames count: {len(frames)}")
        if not frames:
            logging.info("No frames found, requesting frame processing from 5001...")
            response = requests.post("http://127.0.0.1:5001/process_video", json={"video_id": video_id})

            if response.status_code != 200:
                raise ValueError(f"Error generating frames: {response.text}")

            # Retry to get frames after the generation request
            max_retries = 10
            wait_time = 2
            timeout = 30  # Timeout to avoid waiting indefinitely
            start_time = time.time()
            for attempt in range(max_retries):
                if time.time() - start_time > timeout:
                    logging.error("Timeout reached while waiting for frames.")
                    return None

                time.sleep(wait_time)
                db.session.expire_all()
                frames = self.frame_repository.get_frames_by_video_id(video_id)
                if frames:
                    logging.info(f"Frames found on attempt {attempt + 1}")
                    break
                logging.info(f"Waiting for frames... attempt {attempt + 1}/{max_retries}")

            # If frames are still not available after retries, return None to handle this in the API
            if not frames:
                logging.info("Frames still unavailable after retries.")
                return None  # Indicate that frames are not ready yet

        # Clear any previous emotions to avoid duplication in detection
        existing_emotions = self.emotion_repository.get_emotions_by_video_id(video_id)
        if existing_emotions:
            self.emotion_repository.delete_emotions_by_video_id(video_id)

        # Process frames and annotate them
        annotated_frames = []
        frames_to_update = []
        persons_to_update = []
        total_frames = len(frames)
        for idx, frame in enumerate(frames):
            annotations, annotated_frame_path, frame_data = self.emotion_service.detect_emotions_in_frame(frame.path)
            frame_data['annotated_path'] = annotated_frame_path
            frame_data['frame_id'] = frame.id
            annotated_frames.append(frame_data)

            # Update frame with frame_data
            frame.average_brightness = float(frame_data['average_brightness']) if isinstance(frame_data['average_brightness'], np.float32) else frame_data['average_brightness']
            frame.contrast_ratio = float(frame_data['contrast_ratio']) if isinstance(frame_data['contrast_ratio'], np.float32) else frame_data['contrast_ratio']
            frame.sharpness = float(frame_data['sharpness']) if isinstance(frame_data['sharpness'], np.float32) else frame_data['sharpness']
            frame.color_temperature = float(frame_data['color_temperature']) if isinstance(frame_data['color_temperature'], np.float32) else frame_data['color_temperature']
            frame.background_complexity = float(frame_data['background_complexity']) if isinstance(frame_data['background_complexity'], np.float32) else frame_data['background_complexity']
            frames_to_update.append(frame)

            for annotation in annotations:
                bbox_str = ",".join(map(str, annotation['bbox']))
                person = self.person_repository.get_or_create(video_id, annotation['person_identity'])

                # Update person with age and gender estimation
                person.age_estimation = float(annotation['age_estimation']) if isinstance(annotation['age_estimation'], np.float32) else annotation['age_estimation']
                person.gender_estimation = annotation['gender_estimation']
                persons_to_update.append(person)

                emotion = Emotion(
                    frame_id=frame.id,
                    person_id=person.id,
                    emotion_type=annotation['emotion'],
                    confidence=annotation['confidence'],
                    bbox=bbox_str,
                    video_id=video.id
                )
                self.emotion_repository.save(emotion)

            progress_percent = int(((idx + 1) / total_frames) * 100)
            logging.info(f"Processed frame {idx + 1}/{total_frames} ({progress_percent}% complete)")

        # Commit all changes to frames and persons
        db.session.add_all(frames_to_update)
        db.session.add_all(persons_to_update)
        db.session.commit()

        # Generate annotated video
        output_video_filename = f'video_{video.id}_emotion_annotated.mp4'
        output_video_path = os.path.join(Config.ANNOTATED_VIDEOS_DIR, output_video_filename)
        self.video_generation_service.generate_video_from_frames(annotated_frames, output_video_path)

        logging.info("Emotion detection complete, annotated video generated.")
        return output_video_path