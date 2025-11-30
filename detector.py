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
    
    def __init__(self, model_path: str = "yolov8n.pt", conf_threshold: float = 0.25, use_huggingface: bool = False, hf_repo_id: Optional[str] = None):
        """
        Initialize the person detector.
        
        Args:
            model_path: Path to YOLOv8 model weights or Hugging Face model identifier
            conf_threshold: Confidence threshold for detections
            use_huggingface: If True, load model from Hugging Face
            hf_repo_id: Hugging Face repository ID (e.g., "ultralytics/yolov8n" or "keremberke/yolov8n")
        """
        import os
        
        # If using Hugging Face, download model first
        if use_huggingface or hf_repo_id:
            model_path = self._load_from_huggingface(model_path, hf_repo_id)
        
        # Try to load model
        try:
            self.model = YOLO(model_path)
        except Exception as e:
            # If model download fails, try to use a cached version or retry
            # Try to find model in common locations
            possible_paths = [
                model_path,
                os.path.join(os.path.expanduser("~"), ".ultralytics", "weights", model_path),
                os.path.join("/tmp", "Ultralytics", model_path),
                os.path.join("/tmp", "Ultralytics", "weights", model_path),
            ]
            model_loaded = False
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        self.model = YOLO(path)
                        model_loaded = True
                        print(f"✅ Loaded model from: {path}")
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
    
    def _load_from_huggingface(self, model_path: str, hf_repo_id: Optional[str] = None) -> str:
        """
        Load YOLOv8 model from Hugging Face.
        
        Args:
            model_path: Original model path (e.g., "yolov8n.pt")
            hf_repo_id: Hugging Face repository ID
            
        Returns:
            Path to downloaded model file
        """
        try:
            from huggingface_hub import hf_hub_download
            import os
            
            # Default Hugging Face repositories for YOLOv8
            if hf_repo_id is None:
                # Map model names to Hugging Face repos
                model_to_repo = {
                    "yolov8n.pt": "ultralytics/yolov8n",
                    "yolov8s.pt": "ultralytics/yolov8s",
                    "yolov8m.pt": "ultralytics/yolov8m",
                    "yolov8l.pt": "ultralytics/yolov8l",
                    "yolov8x.pt": "ultralytics/yolov8x",
                }
                hf_repo_id = model_to_repo.get(model_path, "ultralytics/yolov8n")
            
            # Extract model filename from repo if needed
            if "/" in hf_repo_id:
                repo_id = hf_repo_id
                filename = model_path if model_path.endswith(".pt") else f"{hf_repo_id.split('/')[-1]}.pt"
            else:
                repo_id = f"ultralytics/{hf_repo_id}"
                filename = model_path
            
            print(f"📥 Downloading model from Hugging Face: {repo_id}/{filename}")
            
            # Download model to cache directory
            # On Streamlit Cloud, this will be in /tmp
            cache_dir = os.getenv("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface"))
            # Use /tmp on Streamlit Cloud for writable location
            if not os.access(cache_dir, os.W_OK):
                cache_dir = "/tmp/huggingface"
                os.makedirs(cache_dir, exist_ok=True)
            
            # Download model file
            model_file = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                cache_dir=cache_dir,
                force_download=False,
                resume_download=True
            )
            
            print(f"✅ Model downloaded from Hugging Face: {model_file}")
            return model_file
            
        except ImportError:
            print("⚠️ huggingface_hub not installed. Install with: pip install huggingface_hub")
            print("   Falling back to standard YOLO download...")
            return model_path
        except Exception as e:
            print(f"⚠️ Failed to load from Hugging Face: {e}")
            print("   Falling back to standard YOLO download...")
            return model_path
        
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

