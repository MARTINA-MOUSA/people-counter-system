"""
Person Tracking Module using ByteTrack algorithm
Handles multi-person tracking with unique ID assignment.
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import deque


class Track:
    """Represents a tracked person."""
    
    def __init__(self, track_id: int, bbox: Tuple[int, int, int, int], conf: float):
        """
        Initialize a track.
        
        Args:
            track_id: Unique track identifier
            bbox: Bounding box (x1, y1, x2, y2)
            conf: Detection confidence
        """
        self.track_id = track_id
        self.bbox = bbox
        self.conf = conf
        self.hits = 1
        self.time_since_update = 0
        self.history = deque(maxlen=30)  # Store last 30 positions
        center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
        self.history.append(center)
        
    def update(self, bbox: Tuple[int, int, int, int], conf: float):
        """Update track with new detection."""
        self.bbox = bbox
        self.conf = conf
        self.hits += 1
        self.time_since_update = 0
        center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)
        self.history.append(center)
        
    def predict(self):
        """Predict next position (simple linear prediction)."""
        if len(self.history) >= 2:
            # Simple velocity-based prediction
            dx = self.history[-1][0] - self.history[-2][0]
            dy = self.history[-1][1] - self.history[-2][1]
            return (self.history[-1][0] + dx, self.history[-1][1] + dy)
        return self.history[-1] if self.history else (0, 0)


class ByteTracker:
    """ByteTrack-based multi-person tracker."""
    
    def __init__(self, 
                 max_age: int = 30,
                 min_hits: int = 3,
                 iou_threshold: float = 0.3,
                 track_thresh: float = 0.5,
                 high_thresh: float = 0.6,
                 match_thresh: float = 0.8):
        """
        Initialize the tracker.
        
        Args:
            max_age: Maximum frames to keep lost tracks
            min_hits: Minimum hits to confirm a track
            iou_threshold: IoU threshold for matching
            track_thresh: Detection confidence threshold for tracking
            high_thresh: High confidence threshold
            match_thresh: Matching threshold for high confidence detections
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.track_thresh = track_thresh
        self.high_thresh = high_thresh
        self.match_thresh = match_thresh
        
        self.tracked_tracks: List[Track] = []
        self.lost_tracks: List[Track] = []
        self.removed_tracks: List[Track] = []
        self.frame_count = 0
        self.next_id = 1
        
    def update(self, detections: List[Tuple[int, int, int, int, float]]) -> List[Tuple[int, int, int, int, int, float]]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of (x1, y1, x2, y2, confidence) tuples
            
        Returns:
            List of tracked objects as (x1, y1, x2, y2, track_id, confidence) tuples
        """
        self.frame_count += 1
        
        # Separate high and low confidence detections
        high_conf_dets = [d for d in detections if d[4] >= self.high_thresh]
        low_conf_dets = [d for d in detections if d[4] < self.high_thresh and d[4] >= self.track_thresh]
        
        # Update tracked tracks
        for track in self.tracked_tracks:
            track.time_since_update += 1
        
        # Match high confidence detections with tracked tracks
        matched, unmatched_tracks, unmatched_dets = self._associate_detections_to_trackers(
            high_conf_dets, self.tracked_tracks
        )
        
        # Update matched tracks
        for m in matched:
            track = self.tracked_tracks[m[0]]
            det = high_conf_dets[m[1]]
            track.update((det[0], det[1], det[2], det[3]), det[4])
        
        # Process unmatched tracks BEFORE adding new ones (to keep indices valid)
        tracks_to_remove = []
        tracks_to_lose = []
        for track_idx in unmatched_tracks:
            if track_idx < len(self.tracked_tracks):
                track = self.tracked_tracks[track_idx]
                if track.time_since_update > self.max_age:
                    tracks_to_remove.append(track)
                else:
                    tracks_to_lose.append(track)
        
        # Actually remove/move unmatched tracks
        for track in tracks_to_remove:
            if track in self.tracked_tracks:
                self.tracked_tracks.remove(track)
                self.removed_tracks.append(track)
        
        for track in tracks_to_lose:
            if track in self.tracked_tracks:
                self.tracked_tracks.remove(track)
                self.lost_tracks.append(track)
        
        # Create new tracks for unmatched high confidence detections
        for det_idx in unmatched_dets:
            det = high_conf_dets[det_idx]
            if det[4] >= self.high_thresh:
                new_track = Track(self.next_id, (det[0], det[1], det[2], det[3]), det[4])
                self.tracked_tracks.append(new_track)
                self.next_id += 1
        
        # Try to match low confidence detections with lost tracks
        matched_low, unmatched_lost, unmatched_low_dets = self._associate_detections_to_trackers(
            low_conf_dets, self.lost_tracks
        )
        
        # Reactivate matched lost tracks
        tracks_to_reactivate = []
        for m in matched_low:
            track = self.lost_tracks[m[0]]
            det = low_conf_dets[m[1]]
            track.update((det[0], det[1], det[2], det[3]), det[4])
            tracks_to_reactivate.append(track)
        
        # Remove reactivated tracks from lost_tracks and add to tracked_tracks
        for track in tracks_to_reactivate:
            if track in self.lost_tracks:
                self.lost_tracks.remove(track)
            self.tracked_tracks.append(track)
        
        # Remove old lost tracks
        self.lost_tracks = [t for t in self.lost_tracks if t.time_since_update <= self.max_age]
        
        # Prepare output
        output_tracks = []
        for track in self.tracked_tracks:
            if track.hits >= self.min_hits:
                bbox = track.bbox
                output_tracks.append((bbox[0], bbox[1], bbox[2], bbox[3], track.track_id, track.conf))
        
        return output_tracks
    
    def _iou(self, box1: Tuple[int, int, int, int], box2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union (IoU) between two boxes."""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return 0.0
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
    
    def _associate_detections_to_trackers(self, 
                                         detections: List[Tuple[int, int, int, int, float]],
                                         tracks: List[Track]) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associate detections to tracked objects.
        
        Returns:
            Tuple of (matched pairs, unmatched tracks, unmatched detections)
        """
        if len(tracks) == 0:
            return [], [], list(range(len(detections)))
        
        if len(detections) == 0:
            return [], list(range(len(tracks))), []
        
        # Compute IoU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)), dtype=np.float32)
        for t, track in enumerate(tracks):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = self._iou(track.bbox, (det[0], det[1], det[2], det[3]))
        
        # Greedy matching
        matched = []
        unmatched_tracks = list(range(len(tracks)))
        unmatched_dets = list(range(len(detections)))
        
        # Sort by IoU descending
        matches = []
        for t in range(len(tracks)):
            for d in range(len(detections)):
                if iou_matrix[t, d] >= self.iou_threshold:
                    matches.append((t, d, iou_matrix[t, d]))
        
        matches.sort(key=lambda x: x[2], reverse=True)
        
        for t, d, iou in matches:
            if t in unmatched_tracks and d in unmatched_dets:
                matched.append((t, d))
                unmatched_tracks.remove(t)
                unmatched_dets.remove(d)
        
        return matched, unmatched_tracks, unmatched_dets

