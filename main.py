"""
Main entry point for People Detection, Tracking, and Entry-Exit Counting System.
"""

import cv2
import argparse
import csv
import os
from datetime import datetime
from typing import Optional

from detector import PersonDetector
from tracker import ByteTracker
from counter import LineCounter
from utils import (
    draw_bounding_box,
    draw_counting_line,
    draw_counters,
    draw_fps,
    FPSCounter
)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Real-Time People Detection, Tracking, and Entry-Exit Counting System"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        default="0",
        help="Input source: video file path or camera index (default: 0 for webcam)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n.pt",
        help="YOLOv8 model path (default: yolov8n.pt)"
    )
    
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Detection confidence threshold (default: 0.25)"
    )
    
    parser.add_argument(
        "--line",
        type=str,
        default="horizontal",
        choices=["horizontal", "vertical"],
        help="Counting line orientation (default: horizontal)"
    )
    
    parser.add_argument(
        "--line-pos",
        type=float,
        default=0.5,
        help="Counting line position as fraction of frame (0.0-1.0, default: 0.5 for center)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output video path (optional)"
    )
    
    parser.add_argument(
        "--csv",
        type=str,
        default="counting_results.csv",
        help="Output CSV file path (default: counting_results.csv)"
    )
    
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Don't display video window"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for counting"
    )
    
    return parser.parse_args()


def setup_counting_line(frame_height: int, 
                       frame_width: int,
                       orientation: str,
                       position: float) -> tuple:
    """
    Setup counting line based on frame dimensions.
    
    Args:
        frame_height: Frame height
        frame_width: Frame width
        orientation: "horizontal" or "vertical"
        position: Position as fraction (0.0-1.0)
        
    Returns:
        Tuple of (line_start, line_end)
    """
    if orientation == "horizontal":
        y = int(frame_height * position)
        line_start = (0, y)
        line_end = (frame_width, y)
    else:  # vertical
        x = int(frame_width * position)
        line_start = (x, 0)
        line_end = (x, frame_height)
    
    return line_start, line_end


def save_to_csv(csv_path: str, history: list):
    """
    Save counting history to CSV file.
    
    Args:
        csv_path: Path to CSV file
        history: List of counting events
    """
    if not history:
        print("No counting events to save.")
        return
    
    try:
        # Try to save with a unique filename if file is locked
        import os
        base_path = csv_path
        counter = 1
        while os.path.exists(csv_path) and counter < 100:
            # Check if file is locked by trying to open it
            try:
                test_file = open(csv_path, 'r')
                test_file.close()
                break  # File exists but is not locked
            except (PermissionError, IOError):
                # File is locked, try alternative name
                name, ext = os.path.splitext(base_path)
                csv_path = f"{name}_{counter}{ext}"
                counter += 1
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'track_id', 'direction', 'total_enter', 'total_exit']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(history)
        
        print(f"Results saved to {csv_path}")
    except PermissionError:
        print(f"Warning: Cannot save to {csv_path} (file may be open in another program).")
        print("Trying alternative filename...")
        # Try with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(base_path)
        alt_path = f"{name}_{timestamp}{ext}"
        try:
            with open(alt_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'track_id', 'direction', 'total_enter', 'total_exit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(history)
            print(f"Results saved to {alt_path}")
        except Exception as e:
            print(f"Error saving CSV: {e}")
    except Exception as e:
        print(f"Error saving CSV: {e}")


def main():
    """Main function."""
    args = parse_arguments()
    
    # Initialize components
    print("Initializing detector...")
    detector = PersonDetector(model_path=args.model, conf_threshold=args.conf)
    
    print("Initializing tracker...")
    tracker = ByteTracker()
    
    # Open video source
    if args.input.isdigit():
        # Webcam
        input_source = int(args.input)
        print(f"Opening webcam {input_source}...")
    else:
        # Video file
        input_source = args.input
        print(f"Opening video: {input_source}...")
    
    cap = cv2.VideoCapture(input_source)
    if not cap.isOpened():
        print(f"Error: Cannot open input source: {args.input}")
        return
    
    # Get video properties
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    
    print(f"Video resolution: {frame_width}x{frame_height}, FPS: {fps:.2f}")
    
    # Setup counting line
    line_start, line_end = setup_counting_line(
        frame_height, frame_width, args.line, args.line_pos
    )
    print(f"Counting line: {line_start} -> {line_end} ({args.line})")
    
    counter = LineCounter(line_start, line_end, args.line, debug=args.debug)
    
    # Setup video writer if output specified
    video_writer = None
    if args.output:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(
            args.output, fourcc, fps, (frame_width, frame_height)
        )
        print(f"Output video: {args.output}")
    
    # FPS counter
    fps_counter = FPSCounter()
    
    # Main loop
    frame_count = 0
    print("\nStarting detection and tracking...")
    print("Press 'q' to quit, 'r' to reset counters\n")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("End of video or failed to read frame.")
                break
            
            # Detect persons
            detections = detector.detect(frame)
            
            # Track persons
            tracks = tracker.update(detections)
            
            # Update counting
            timestamp = frame_count / fps
            total_enter, total_exit, current_occupancy = counter.update(tracks, timestamp)
            
            # Draw on frame
            # Draw counting line
            frame = draw_counting_line(frame, line_start, line_end)
            
            # Draw bounding boxes and track IDs
            for track in tracks:
                x1, y1, x2, y2, track_id, conf = track
                frame = draw_bounding_box(frame, (x1, y1, x2, y2), track_id, conf)
            
            # Draw counters
            frame = draw_counters(frame, total_enter, total_exit, current_occupancy)
            
            # Draw FPS
            current_fps = fps_counter.update()
            frame = draw_fps(frame, current_fps)
            
            # Write frame to output video
            if video_writer:
                video_writer.write(frame)
            
            # Display frame
            if not args.no_display:
                cv2.imshow("People Counter", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("Quitting...")
                    break
                elif key == ord('r'):
                    print("Resetting counters...")
                    counter.total_enter = 0
                    counter.total_exit = 0
                    counter.current_occupancy = 0
                    counter.counting_history.clear()
                    counter.reset_counting_flags()
            
            frame_count += 1
            
            # Print progress for video files
            if not args.input.isdigit() and frame_count % 30 == 0:
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                progress = (frame_count / total_frames * 100) if total_frames > 0 else 0
                print(f"Progress: {frame_count}/{total_frames} frames ({progress:.1f}%) | "
                      f"FPS: {current_fps:.1f} | Enter: {total_enter} | Exit: {total_exit} | "
                      f"Occupancy: {current_occupancy}")
    
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    
    finally:
        # Cleanup
        cap.release()
        if video_writer:
            video_writer.release()
        cv2.destroyAllWindows()
        
        # Save results to CSV
        history = counter.get_history()
        if history:
            save_to_csv(args.csv, history)
            print(f"\nFinal counts - Enter: {counter.total_enter}, "
                  f"Exit: {counter.total_exit}, Occupancy: {counter.current_occupancy}")
        else:
            print("\nNo counting events recorded.")
        
        print("Done.")


if __name__ == "__main__":
    main()

