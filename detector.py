"""
Person Detection Module using YOLOv8
Handles person detection from video frames using pretrained YOLOv8 model.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional


class PersonDetector:
    """YOLOv8-based person detector."""
    
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.25):
        """
        Initialize the person detector.
        
        Args:
            model_path: Path to YOLOv8 model weights (will download if not exists)
            conf_threshold: Confidence threshold for detections
        """
        # YOLO will automatically download the model if it doesn't exist
        # On first run, it downloads from ultralytics.com
        # The model is saved to ~/.ultralytics/weights/ or /tmp/Ultralytics/ on Streamlit Cloud
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            # If model download fails, try to use a cached version or retry
            import os
            # Try to find model in common locations
            possible_paths = [
                model_path,
                os.path.join(os.path.expanduser("~"), ".ultralytics", "weights", model_path),
                os.path.join("/tmp", "Ultralytics", model_path),
            ]
            model_loaded = False
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        self.model = YOLO(path)
                        model_loaded = True
                        break
                    except:
                        continue
            
            if not model_loaded:
                # Last attempt: let YOLO handle the download
                print(f"⚠️ Warning: Could not load model from {model_path}, attempting automatic download...")
                self.model = YOLO(model_path)
        
        self.conf_threshold = conf_threshold
        # COCO class ID for person is 0
        self.person_class_id = 0
        
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int, float]]:
        """
        Detect persons in a frame.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            List of detections as (x1, y1, x2, y2, confidence) tuples
        """
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Check if detection is a person (class 0)
                if int(box.cls) == self.person_class_id:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    detections.append((int(x1), int(y1), int(x2), int(y2), conf))
        
        return detections
    
    def detect_with_features(self, frame: np.ndarray) -> Tuple[List[Tuple[int, int, int, int, float]], np.ndarray]:
        """
        Detect persons and return features for tracking.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Tuple of (detections, features) where:
            - detections: List of (x1, y1, x2, y2, confidence) tuples
            - features: Feature vectors for each detection (for re-identification)
        """
        results = self.model(frame, conf=self.conf_threshold, verbose=False)
        detections = []
        features = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                if int(box.cls) == self.person_class_id:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    detections.append((int(x1), int(y1), int(x2), int(y2), conf))
                    
                    # Extract center point for feature extraction
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    # Simple feature: normalized center coordinates and box dimensions
                    # In production, you might use a re-ID model here
                    w = x2 - x1
                    h = y2 - y1
                    feature = np.array([center_x / frame.shape[1], 
                                       center_y / frame.shape[0],
                                       w / frame.shape[1],
                                       h / frame.shape[0],
                                       conf])
                    features.append(feature)
        
        return detections, np.array(features) if features else np.empty((0, 5))

