"""
Utility functions for the people counter system.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import time


def draw_bounding_box(frame: np.ndarray,
                     bbox: Tuple[int, int, int, int],
                     track_id: int,
                     confidence: float,
                     color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
    """
    Draw bounding box with track ID and confidence.
    
    Args:
        frame: Input frame
        bbox: Bounding box (x1, y1, x2, y2)
        track_id: Track ID
        confidence: Detection confidence
        color: BGR color tuple
        
    Returns:
        Frame with drawn bounding box
    """
    x1, y1, x2, y2 = bbox
    
    # Draw rectangle
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    
    # Prepare label
    label = f"ID: {track_id} ({confidence:.2f})"
    
    # Calculate text size
    (text_width, text_height), baseline = cv2.getTextSize(
        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
    )
    
    # Draw label background
    cv2.rectangle(
        frame,
        (x1, y1 - text_height - baseline - 5),
        (x1 + text_width, y1),
        color,
        -1
    )
    
    # Draw label text
    cv2.putText(
        frame,
        label,
        (x1, y1 - baseline - 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 0),
        1
    )
    
    return frame


def draw_counting_line(frame: np.ndarray,
                      line_start: Tuple[int, int],
                      line_end: Tuple[int, int],
                      color: Tuple[int, int, int] = (255, 0, 0),
                      thickness: int = 3) -> np.ndarray:
    """
    Draw counting line on frame.
    
    Args:
        frame: Input frame
        line_start: Start point (x, y)
        line_end: End point (x, y)
        color: BGR color tuple
        thickness: Line thickness
        
    Returns:
        Frame with drawn line
    """
    cv2.line(frame, line_start, line_end, color, thickness)
    
    # Add arrow indicators
    arrow_length = 20
    if line_start[0] == line_end[0]:  # Vertical line
        # Draw arrows pointing left (enter) and right (exit)
        cv2.arrowedLine(
            frame,
            (line_start[0] - arrow_length, line_start[1]),
            (line_start[0], line_start[1]),
            (0, 255, 0),
            2,
            tipLength=0.3
        )
        cv2.putText(
            frame,
            "ENTER",
            (line_start[0] - arrow_length - 60, line_start[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2
        )
        cv2.arrowedLine(
            frame,
            (line_end[0] + arrow_length, line_end[1]),
            (line_end[0], line_end[1]),
            (0, 0, 255),
            2,
            tipLength=0.3
        )
        cv2.putText(
            frame,
            "EXIT",
            (line_end[0] + arrow_length + 10, line_end[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2
        )
    else:  # Horizontal line
        # Draw arrows pointing up (enter) and down (exit)
        cv2.arrowedLine(
            frame,
            (line_start[0], line_start[1] - arrow_length),
            (line_start[0], line_start[1]),
            (0, 255, 0),
            2,
            tipLength=0.3
        )
        cv2.putText(
            frame,
            "ENTER",
            (line_start[0] + 10, line_start[1] - arrow_length - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2
        )
        cv2.arrowedLine(
            frame,
            (line_end[0], line_end[1] + arrow_length),
            (line_end[0], line_end[1]),
            (0, 0, 255),
            2,
            tipLength=0.3
        )
        cv2.putText(
            frame,
            "EXIT",
            (line_end[0] + 10, line_end[1] + arrow_length + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 255),
            2
        )
    
    return frame


def draw_counters(frame: np.ndarray,
                 total_enter: int,
                 total_exit: int,
                 current_occupancy: int,
                 position: Tuple[int, int] = (10, 30)) -> np.ndarray:
    """
    Draw counter information on frame.
    
    Args:
        frame: Input frame
        total_enter: Total people entered
        total_exit: Total people exited
        current_occupancy: Current occupancy count
        position: Top-left position for text
        
    Returns:
        Frame with drawn counters
    """
    x, y = position
    
    # Background rectangle
    cv2.rectangle(frame, (x - 5, y - 25), (x + 300, y + 80), (0, 0, 0), -1)
    cv2.rectangle(frame, (x - 5, y - 25), (x + 300, y + 80), (255, 255, 255), 2)
    
    # Text
    cv2.putText(
        frame,
        f"Entered: {total_enter}",
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )
    
    cv2.putText(
        frame,
        f"Exited: {total_exit}",
        (x, y + 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )
    
    cv2.putText(
        frame,
        f"Current: {current_occupancy}",
        (x, y + 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 0),
        2
    )
    
    return frame


def draw_fps(frame: np.ndarray,
            fps: float,
            position: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    Draw FPS counter on frame.
    
    Args:
        frame: Input frame
        fps: Current FPS
        position: Position for FPS text (default: bottom-left)
        
    Returns:
        Frame with drawn FPS
    """
    if position is None:
        position = (10, frame.shape[0] - 20)
    x, y = position
    
    # Background
    text = f"FPS: {fps:.1f}"
    (text_width, text_height), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
    )
    cv2.rectangle(
        frame,
        (x - 5, y - text_height - 5),
        (x + text_width + 5, y + 5),
        (0, 0, 0),
        -1
    )
    
    # Text
    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 255),
        2
    )
    
    return frame


class FPSCounter:
    """Simple FPS counter."""
    
    def __init__(self):
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0
        
    def update(self) -> float:
        """Update and return current FPS."""
        self.frame_count += 1
        elapsed = time.time() - self.start_time
        
        if elapsed > 0:
            self.fps = self.frame_count / elapsed
        
        return self.fps
    
    def reset(self):
        """Reset FPS counter."""
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0.0

