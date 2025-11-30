# Real-Time People Detection, Tracking, and Entry-Exit Counting System

A production-ready Python system for real-time people detection, tracking, and counting using YOLOv8 and ByteTrack. The system detects people in video streams, assigns unique IDs, tracks them across frames, and counts entries/exits across a virtual counting line.

## Features

- **Person Detection**: YOLOv8 pretrained model for accurate person detection
- **Multi-Person Tracking**: ByteTrack algorithm for robust tracking with unique IDs
- **Entry/Exit Counting**: Virtual counting line (horizontal or vertical) with entry/exit detection
- **Double Counting Prevention**: Uses track IDs to prevent counting the same person multiple times
- **Real-Time Performance**: Optimized for real-time or near real-time processing
- **Multiple Input Sources**: Supports video files and webcam input
- **Visualization**: Real-time display with bounding boxes, track IDs, and counters
- **Data Export**: Automatic CSV export with timestamp, track_id, direction, and counts
- **FPS Monitoring**: Built-in FPS counter for performance monitoring

## Project Structure

```
people-counter-system/
├── main.py              # Main entry point
├── detector.py          # YOLOv8 person detection
├── tracker.py           # ByteTrack tracking logic
├── counter.py           # Line crossing and counting
├── utils.py             # Helper functions
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- CUDA-capable GPU (optional, but recommended for better performance)

### Setup

1. **Clone or navigate to the project directory:**
```bash
cd people-counter-system
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

**Note**: The first time you run the system, YOLOv8 will automatically download the pretrained model weights (yolov8n.pt) if they don't exist locally.

## Usage

### Basic Usage

**Webcam (default camera):**
```bash
python main.py
```

**Specific webcam:**
```bash
python main.py --input 1
```

**Video file:**
```bash
python main.py --input path/to/video.mp4
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input` | Input source: video file path or camera index | `0` (webcam) |
| `--model` | YOLOv8 model path | `yolov8n.pt` |
| `--conf` | Detection confidence threshold | `0.25` |
| `--line` | Counting line orientation (`horizontal` or `vertical`) | `horizontal` |
| `--line-pos` | Counting line position (0.0-1.0, fraction of frame) | `0.5` (center) |
| `--output` | Output video path (optional) | None |
| `--csv` | Output CSV file path | `counting_results.csv` |
| `--no-display` | Don't display video window | False |

### Examples

**Process video with horizontal counting line at top:**
```bash
python main.py --input video.mp4 --line horizontal --line-pos 0.2 --output output.mp4
```

**Process video with vertical counting line on the right:**
```bash
python main.py --input video.mp4 --line vertical --line-pos 0.8 --csv results.csv
```

**Use larger YOLOv8 model for better accuracy:**
```bash
python main.py --input video.mp4 --model yolov8m.pt --conf 0.3
```

**Process without display (faster):**
```bash
python main.py --input video.mp4 --no-display
```

### Interactive Controls

When the video window is displayed:
- **'q'**: Quit the application
- **'r'**: Reset all counters

## Output

### CSV File

The system automatically saves counting results to a CSV file with the following columns:

- `timestamp`: Time in seconds from video start
- `track_id`: Unique track ID of the person
- `direction`: `enter` or `exit`
- `total_enter`: Total count of people entered up to this point
- `total_exit`: Total count of people exited up to this point

Example:
```csv
timestamp,track_id,direction,total_enter,total_exit
1.23,1,enter,1,0
2.45,2,enter,2,0
5.67,1,exit,2,1
```

### Video Output (Optional)

If `--output` is specified, the annotated video with bounding boxes, track IDs, and counters will be saved.

## How It Works

1. **Detection**: YOLOv8 detects all persons in each frame
2. **Tracking**: ByteTrack associates detections across frames and assigns unique track IDs
3. **Line Crossing**: The system tracks each person's position relative to the counting line
4. **Counting**: When a person crosses the line, the system increments the appropriate counter
5. **Double Counting Prevention**: Each track ID is counted only once per crossing

### Counting Line Logic

- **Horizontal Line**: 
  - Top side = Enter
  - Bottom side = Exit
- **Vertical Line**:
  - Left side = Enter
  - Right side = Exit

The system determines which side a person is on based on the signed distance from their center point to the line.

## Performance

- **YOLOv8n (nano)**: Fastest, lower accuracy (~30-60 FPS on GPU)
- **YOLOv8s (small)**: Balanced (~20-40 FPS on GPU)
- **YOLOv8m (medium)**: Better accuracy (~15-30 FPS on GPU)
- **YOLOv8l (large)**: High accuracy (~10-20 FPS on GPU)
- **YOLOv8x (xlarge)**: Highest accuracy (~5-15 FPS on GPU)

Performance depends on:
- Hardware (CPU/GPU)
- Input resolution
- Number of people in frame
- Model size

## Troubleshooting

### Low FPS

- Use a smaller YOLOv8 model (yolov8n.pt)
- Reduce input resolution
- Use `--no-display` flag
- Ensure GPU is being used (check CUDA availability)

### Detection Issues

- Adjust `--conf` threshold (lower = more detections, higher = fewer false positives)
- Use a larger YOLOv8 model for better accuracy
- Ensure good lighting and camera quality

### Counting Errors

- Adjust `--line-pos` to position the line correctly
- Ensure the line is perpendicular to the main flow of people
- Check that the line orientation matches the scene

### CUDA/GPU Issues

If you encounter CUDA errors:
- Install PyTorch with CUDA support: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`
- Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`

## Technical Details

### Dependencies

- **torch**: PyTorch for deep learning
- **ultralytics**: YOLOv8 implementation
- **opencv-python**: Video processing and visualization
- **numpy**: Numerical operations
- **pandas**: Data handling (for CSV export)
- **filterpy**: Kalman filter utilities (used by ByteTrack)
- **scipy**: Scientific computing

### Model Information

- **YOLOv8**: Pretrained on COCO dataset
- **Person Class ID**: 0 (COCO dataset)
- **Automatic Download**: Models are downloaded automatically on first use

## License

This project uses pretrained models and algorithms:
- YOLOv8: AGPL-3.0 License (Ultralytics)
- ByteTrack: MIT License

## Contributing

This is a production-ready system. For improvements:
1. Ensure code follows PEP 8 style guide
2. Add comments for complex logic
3. Test with various video sources
4. Maintain backward compatibility

## Acknowledgments

- **YOLOv8**: Ultralytics (https://github.com/ultralytics/ultralytics)
- **ByteTrack**: ByteTrack algorithm for multi-object tracking
- **OpenCV**: Computer vision library

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed correctly
3. Test with a simple video file first
4. Check console output for error messages

---

**Note**: This system uses only pretrained models - no training or fine-tuning is required. All models are downloaded automatically on first use.

