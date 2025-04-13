# MicroserviceEmotionDetection/services/video_generation_service.py

import logging
import cv2
import os
import subprocess
from config import Config

class VideoGenerationService:
    def generate_video_from_frames(self, frames, output_video_filename):
        frame_paths = [frame['annotated_path'] for frame in frames]
        if not frame_paths:
            logging.error("No frames to generate video.")
            print("No frames to generate video.")
            raise ValueError("No frames to generate video.")

        temp_output_path = os.path.join(Config.ANNOTATED_VIDEOS_DIR, 'temp_output_video.avi')
        output_video_path = os.path.join(Config.ANNOTATED_VIDEOS_DIR, output_video_filename)

        first_frame = cv2.imread(frame_paths[0])
        if first_frame is None:
            logging.error(f"Could not read the first frame at {frame_paths[0]}")
            print(f"Could not read the first frame at {frame_paths[0]}")
            raise ValueError("Invalid frame path for video generation.")

        height, width, layers = first_frame.shape
        size = (width, height)

        logging.info(f"Starting video generation: {output_video_filename} with dimensions {size}")
        print(f"Starting video generation: {output_video_filename} with dimensions {size}")

        out = cv2.VideoWriter(temp_output_path, cv2.VideoWriter_fourcc(*'XVID'), 24, size)

        for frame_path in frame_paths:
            img = cv2.imread(frame_path)
            if img is not None:
                out.write(img)
                logging.info(f"Writing frame to temp video: {frame_path}")
                print(f"Writing frame to temp video: {frame_path}")
            else:
                logging.warning(f"Skipping unreadable frame: {frame_path}")
                print(f"Skipping unreadable frame: {frame_path}")

        out.release()
        logging.info(f"Temporary AVI video created at {temp_output_path}")
        print(f"Temporary AVI video created at {temp_output_path}")

        ffmpeg_command = [
            'ffmpeg', '-y', '-i', temp_output_path,
            '-vcodec', 'libx264', '-acodec', 'aac',
            '-f', 'mp4', output_video_path
        ]

        try:
            subprocess.run(ffmpeg_command, check=True)
            logging.info(f"MP4 video successfully generated at {output_video_path}")
            print(f"MP4 video successfully generated at {output_video_path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg error: {e}")
            print(f"FFmpeg error: {e}")
        finally:
            if os.path.exists(temp_output_path):
                os.remove(temp_output_path)
                logging.info(f"Temporary file {temp_output_path} removed.")
                print(f"Temporary file {temp_output_path} removed.")

        return output_video_path