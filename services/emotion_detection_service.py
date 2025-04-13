# services/emotion_detection_service.py

import cv2
import os
from fer import FER
from config import Config
import numpy as np

class EmotionDetectionService:
    def __init__(self):
        self.detector = FER(mtcnn=True)

        # Load age and gender models
        self.age_net = cv2.dnn.readNetFromCaffe(
            os.path.join(Config.MODELS_DIR, 'deploy_age.prototxt'),
            os.path.join(Config.MODELS_DIR, 'age_net.caffemodel')
        )
        self.gender_net = cv2.dnn.readNetFromCaffe(
            os.path.join(Config.MODELS_DIR, 'deploy_gender.prototxt'),
            os.path.join(Config.MODELS_DIR, 'gender_net.caffemodel')
        )

        # Age and gender lists
        self.AGE_LIST = ['(0-2)', '(4-6)', '(8-12)', '(15-20)',
                         '(25-32)', '(38-43)', '(48-53)', '(60-100)']
        self.GENDER_LIST = ['Male', 'Female']

    def detect_emotions_in_frame(self, frame_path):
        image = cv2.imread(frame_path)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.detector.detect_emotions(rgb_image)
        annotations = []

        # Compute frame-level data
        frame_data = self.compute_frame_data(image)

        for i, result in enumerate(results):
            bbox = result['box']
            emotions = result['emotions']
            emotion_label = max(emotions, key=emotions.get)
            confidence = emotions[emotion_label]
            x, y, w, h = bbox
            annotations.append({
                'person_identity': f'Person_{i}',
                'bbox': (x, y, w, h),
                'emotion': emotion_label.capitalize(),
                'confidence': confidence,
                'age_estimation': None,
                'gender_estimation': None
            })

            # Extract face ROI for age and gender estimation
            face_img = image[y:y+h, x:x+w]

            # Verificar que la imagen del rostro no esté vacía
            if face_img.size == 0:
                print(f"[WARNING] Cara vacía detectada en bbox: {x}, {y}, {w}, {h}")
                continue  # Saltar esta detección y evitar que rompa

            # Estimate age and gender
            age_estimation, gender_estimation = self.estimate_age_gender(face_img)

            annotations[-1]['age_estimation'] = age_estimation
            annotations[-1]['gender_estimation'] = gender_estimation

            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(image, f"{emotion_label.capitalize()} ({confidence*100:.2f}%)", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(image, f"{gender_estimation}, {age_estimation}", (x, y + h + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        annotated_frame_path = os.path.join(Config.PROCESSED_FRAMES_DIR, os.path.basename(frame_path))
        annotated_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(annotated_frame_path, annotated_image)

        return annotations, annotated_frame_path, frame_data

    def compute_frame_data(self, image):
        # Compute average brightness
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        average_brightness = np.mean(gray)

        # Compute contrast ratio
        contrast_ratio = gray.std()

        # Compute sharpness using variance of Laplacian
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = laplacian_var

        # Compute color temperature (approximate estimation)
        avg_color_per_row = np.average(image, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)
        color_temperature = (avg_color[2] - avg_color[0])  # Simplified estimation

        # Compute background complexity using entropy
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_norm = hist.ravel()/hist.sum()
        hist_norm = hist_norm[hist_norm > 0]
        entropy = -np.sum(hist_norm * np.log2(hist_norm))
        background_complexity = entropy

        frame_data = {
            'average_brightness': average_brightness,
            'contrast_ratio': contrast_ratio,
            'sharpness': sharpness,
            'color_temperature': color_temperature,
            'background_complexity': background_complexity
        }
        return frame_data

    def estimate_age_gender(self, face_img):
        if face_img is None or face_img.size == 0:
            return "Unknown", "Unknown"
        blob = cv2.dnn.blobFromImage(face_img, 1, (227, 227),
                                     [78.4263377603, 87.7689143744, 114.895847746],
                                     swapRB=False)

        # Predict gender
        self.gender_net.setInput(blob)
        gender_preds = self.gender_net.forward()
        gender = self.GENDER_LIST[gender_preds[0].argmax()]

        # Predict age
        self.age_net.setInput(blob)
        age_preds = self.age_net.forward()
        age = self.AGE_LIST[age_preds[0].argmax()]

        return age, gender