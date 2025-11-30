"""
Line Crossing and Counting Module
Handles virtual counting line and entry/exit counting logic.
"""

from typing import Tuple, List, Dict
import numpy as np


class LineCounter:
    """Manages virtual counting line and people counting."""
    
    def __init__(self, 
                 line_start: Tuple[int, int],
                 line_end: Tuple[int, int],
                 direction: str = "horizontal",
                 debug: bool = False):
        """
        Initialize the counting line.
        
        Args:
            line_start: Start point of the counting line (x, y)
            line_end: End point of the counting line (x, y)
            direction: "horizontal" or "vertical"
            debug: Enable debug output
        """
        self.line_start = line_start
        self.line_end = line_end
        self.direction = direction.lower()
        self.debug = debug
        
        # Determine which side is "enter" and which is "exit"
        # For horizontal line: top is enter, bottom is exit (or vice versa)
        # For vertical line: left is enter, right is exit (or vice versa)
        self.enter_side = "top" if self.direction == "horizontal" else "left"
        self.exit_side = "bottom" if self.direction == "horizontal" else "right"
        
        # Track states
        self.track_positions: Dict[int, Tuple[int, int]] = {}  # track_id -> last position
        self.track_sides: Dict[int, str] = {}  # track_id -> current side ("enter" or "exit")
        self.track_crossed: Dict[int, bool] = {}  # track_id -> whether they've crossed in current session
        self.track_lost_frames: Dict[int, int] = {}  # track_id -> frames since last seen
        
        # Counters
        self.total_enter = 0
        self.total_exit = 0
        self.current_occupancy = 0
        
        # History for CSV logging
        self.counting_history: List[Dict] = []
        
        # Configuration
        self.min_crossing_distance = 2  # Minimum pixels to move before counting (reduces noise)
        self.lost_frame_threshold = 30  # Frames to wait before resetting track state
        self.crossing_reset_distance = 20  # Distance to move back before allowing re-crossing
        
    def get_line_equation(self) -> Tuple[float, float, float]:
        """
        Get line equation in form ax + by + c = 0.
        
        Returns:
            Tuple of (a, b, c) coefficients
        """
        x1, y1 = self.line_start
        x2, y2 = self.line_end
        
        # Line equation: (y2 - y1)x - (x2 - x1)y + (x2 - x1)y1 - (y2 - y1)x1 = 0
        a = y2 - y1
        b = -(x2 - x1)
        c = (x2 - x1) * y1 - (y2 - y1) * x1
        
        return a, b, c
    
    def point_to_line_distance(self, point: Tuple[int, int]) -> float:
        """
        Calculate signed distance from point to line.
        Positive = one side, Negative = other side.
        
        Args:
            point: Point (x, y)
            
        Returns:
            Signed distance
        """
        a, b, c = self.get_line_equation()
        x, y = point
        distance = (a * x + b * y + c) / np.sqrt(a**2 + b**2) if (a**2 + b**2) > 0 else 0
        return distance
    
    def get_point_side(self, point: Tuple[int, int]) -> str:
        """
        Determine which side of the line a point is on.
        
        Args:
            point: Point (x, y)
            
        Returns:
            "enter" or "exit"
        """
        distance = self.point_to_line_distance(point)
        
        if self.direction == "horizontal":
            # For horizontal line: negative distance = top (enter), positive = bottom (exit)
            return "enter" if distance < 0 else "exit"
        else:
            # For vertical line: negative distance = left (enter), positive = right (exit)
            return "enter" if distance < 0 else "exit"
    
    def update(self, 
               tracks: List[Tuple[int, int, int, int, int, float]],
               timestamp: float) -> Tuple[int, int, int]:
        """
        Update counting based on current tracks.
        
        Args:
            tracks: List of (x1, y1, x2, y2, track_id, confidence) tuples
            timestamp: Current timestamp
            
        Returns:
            Tuple of (total_enter, total_exit, current_occupancy)
        """
        current_track_ids = set()
        
        # Update lost frame counters
        for track_id in self.track_lost_frames:
            self.track_lost_frames[track_id] += 1
        
        for track in tracks:
            x1, y1, x2, y2, track_id, conf = track
            
            # Calculate center point
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            center = (center_x, center_y)
            
            current_track_ids.add(track_id)
            
            # Reset lost frame counter
            if track_id in self.track_lost_frames:
                del self.track_lost_frames[track_id]
            
            # Determine current side
            current_side = self.get_point_side(center)
            
            if track_id not in self.track_positions:
                # New track - initialize
                self.track_positions[track_id] = center
                self.track_sides[track_id] = current_side
                self.track_crossed[track_id] = False
            else:
                # Existing track - check for line crossing
                previous_side = self.track_sides.get(track_id, current_side)
                previous_pos = self.track_positions[track_id]
                
                # Calculate distance moved
                distance_moved = np.sqrt((center_x - previous_pos[0])**2 + (center_y - previous_pos[1])**2)
                
                # Check if side changed (line crossing detected)
                if previous_side != current_side:
                    # Check if we should count this crossing
                    has_crossed = self.track_crossed.get(track_id, False)
                    
                    if self.debug:
                        print(f"[DEBUG] Track {track_id}: Side changed from {previous_side} to {current_side}, "
                              f"distance={distance_moved:.1f}, has_crossed={has_crossed}")
                    
                    # Count if:
                    # 1. Hasn't been counted for this crossing yet
                    # 2. Moved minimum distance (to avoid noise from detection jitter)
                    if not has_crossed and distance_moved >= self.min_crossing_distance:
                        # Line crossed! Determine direction based on current side
                        if current_side == "enter":
                            self.total_enter += 1
                            self.current_occupancy += 1
                            direction = "enter"
                        else:  # current_side == "exit"
                            self.total_exit += 1
                            self.current_occupancy = max(0, self.current_occupancy - 1)
                            direction = "exit"
                        
                        # Mark as crossed to prevent double counting
                        self.track_crossed[track_id] = True
                        
                        # Log to history
                        self.counting_history.append({
                            "timestamp": timestamp,
                            "track_id": track_id,
                            "direction": direction,
                            "total_enter": self.total_enter,
                            "total_exit": self.total_exit
                        })
                        
                        print(f"[COUNT] Track {track_id} {direction.upper()}: Enter={self.total_enter}, Exit={self.total_exit}, Occupancy={self.current_occupancy}")
                    elif self.debug and has_crossed:
                        print(f"[DEBUG] Track {track_id}: Already counted, skipping")
                    elif self.debug and distance_moved < self.min_crossing_distance:
                        print(f"[DEBUG] Track {track_id}: Distance too small ({distance_moved:.1f} < {self.min_crossing_distance})")
                
                # Reset crossed flag if track moves significantly away from line
                # This allows re-counting if person crosses again
                elif previous_side == current_side:
                    if self.track_crossed.get(track_id, False):
                        # Calculate distance from line
                        line_distance = abs(self.point_to_line_distance(center))
                        # Reset if moved far enough from line
                        if line_distance > self.crossing_reset_distance and distance_moved >= self.min_crossing_distance:
                            self.track_crossed[track_id] = False
            
            # Update track state
            self.track_positions[track_id] = center
            self.track_sides[track_id] = current_side
        
        # Handle tracks that are no longer present
        tracks_to_remove = set(self.track_positions.keys()) - current_track_ids
        for track_id in tracks_to_remove:
            if track_id not in self.track_lost_frames:
                self.track_lost_frames[track_id] = 0
        
        # Remove tracks that have been lost for too long
        tracks_to_delete = []
        for track_id, lost_frames in self.track_lost_frames.items():
            if lost_frames >= self.lost_frame_threshold:
                tracks_to_delete.append(track_id)
        
        for track_id in tracks_to_delete:
            if track_id in self.track_positions:
                del self.track_positions[track_id]
            if track_id in self.track_sides:
                del self.track_sides[track_id]
            if track_id in self.track_crossed:
                del self.track_crossed[track_id]
            if track_id in self.track_lost_frames:
                del self.track_lost_frames[track_id]
        
        return self.total_enter, self.total_exit, self.current_occupancy
    
    def reset_counting_flags(self):
        """Reset counting flags for all tracks (useful for testing)."""
        self.track_crossed.clear()
    
    def get_history(self) -> List[Dict]:
        """Get counting history for CSV export."""
        return self.counting_history.copy()

