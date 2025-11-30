# Real-Time People Detection, Tracking, and Entry-Exit Counting System

A production-ready Python system for real-time people detection, tracking, and counting using YOLOv8 and ByteTrack. The system detects people in video streams, assigns unique IDs, tracks them across frames, and counts entries/exits across a virtual counting line.

## ✨ Features

### Core Features
- **Person Detection**: YOLOv8 pretrained model for accurate person detection
- **Multi-Person Tracking**: ByteTrack algorithm for robust tracking with unique IDs
- **Entry/Exit Counting**: Virtual counting line (horizontal or vertical) with entry/exit detection
- **Double Counting Prevention**: Uses track IDs to prevent counting the same person multiple times
- **Real-Time Performance**: Optimized for real-time or near real-time processing
- **Multiple Input Sources**: Supports video files and webcam input
- **Visualization**: Real-time display with bounding boxes, track IDs, and counters
- **Data Export**: Automatic CSV export with timestamp, track_id, direction, and counts
- **FPS Monitoring**: Built-in FPS counter for performance monitoring

### Web Interface Features (NEW)
- **🌐 Modern Web UI**: Beautiful Streamlit-based web interface
- **📤 Direct Processing**: Upload and process videos directly in the browser
- **📊 Real-Time Results**: View statistics, charts, and download results instantly
- **⚙️ Configurable Settings**: Adjust model, confidence, line position, and performance settings
- **📥 Easy Downloads**: Download processed videos and CSV results with one click
- **📈 Data Visualization**: Interactive charts and tables for counting events

### Performance Optimizations (NEW)
- **Frame Skipping**: Process every N frames for faster processing
- **Video Resizing**: Resize videos to reduce processing time
- **Smart Updates**: Reduced status update frequency for better performance
- **Background Processing**: Asynchronous job processing for multiple videos

## Project Structure

```
people-counter-system/
├── main.py              # CLI entry point
├── detector.py          # YOLOv8 person detection
├── tracker.py           # ByteTrack tracking logic
├── counter.py           # Line crossing and counting
├── utils.py             # Helper functions
├── backend/
│   ├── __init__.py
│   └── api.py          # FastAPI backend server
├── frontend/
│   ├── __init__.py
│   └── app.py          # Streamlit web interface
├── run_backend.py       # Backend launcher
├── run_frontend.py      # Frontend launcher
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

### Option 1: Web Interface (Recommended) 🌐

**Step 1: Start Backend API**
```bash
python run_backend.py
```
The API will be available at: http://localhost:8000

**Step 2: Start Frontend (in a new terminal)**
```bash
python run_frontend.py
```
The web interface will open at: http://localhost:8501

**Step 3: Use the Web Interface**
1. Open your browser and go to http://localhost:8501
2. Configure settings in the sidebar (model, confidence, line position, etc.)
3. Upload a video file
4. Click "🚀 بدء المعالجة" (Start Processing)
5. View results, statistics, and download files directly in the browser

### Option 2: Command Line Interface (CLI) 💻

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
| `--debug` | Enable debug output for counting | False |

### Web Interface Settings

The web interface provides additional settings:

- **YOLOv8 Model**: Choose from nano (fastest) to xlarge (most accurate)
- **Confidence Threshold**: Adjust detection sensitivity (0.1-1.0)
- **Line Orientation**: Horizontal or vertical counting line
- **Line Position**: Position of counting line (0.0-1.0)
- **Skip Frames**: Process every N frames (1-5) for faster processing
- **Resize Factor**: Resize video (0.3-1.0) to reduce processing time
- **Debug Mode**: Enable detailed counting logs

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

### Model Performance

- **YOLOv8n (nano)**: Fastest, lower accuracy (~30-60 FPS on GPU)
- **YOLOv8s (small)**: Balanced (~20-40 FPS on GPU)
- **YOLOv8m (medium)**: Better accuracy (~15-30 FPS on GPU)
- **YOLOv8l (large)**: High accuracy (~10-20 FPS on GPU)
- **YOLOv8x (xlarge)**: Highest accuracy (~5-15 FPS on GPU)

### Performance Optimization Tips

1. **For Speed**: 
   - Use `yolov8n.pt` model
   - Set `skip_frames=2` (process every other frame)
   - Use `resize_factor=0.5` (half resolution = 4x faster)
   
2. **For Accuracy**:
   - Use `yolov8m.pt` or larger
   - Set `skip_frames=1` (process all frames)
   - Use `resize_factor=1.0` (original resolution)

Performance depends on:
- Hardware (CPU/GPU)
- Input resolution
- Number of people in frame
- Model size
- Skip frames setting
- Resize factor

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

## API Endpoints (Backend)

The FastAPI backend provides the following endpoints:

- `GET /` - API information
- `POST /api/upload` - Upload video file
- `POST /api/process/{job_id}` - Start processing a job
- `POST /api/process-direct` - Process video directly (returns results immediately)
- `GET /api/status/{job_id}` - Get job status
- `GET /api/download/{job_id}/video` - Download processed video
- `GET /api/download/{job_id}/results` - Download CSV results
- `GET /api/jobs` - List all jobs
- `DELETE /api/jobs/{job_id}` - Delete a job

API documentation is available at: http://localhost:8000/docs

## Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Web Interface
```bash
# Terminal 1
python run_backend.py

# Terminal 2
python run_frontend.py
```

### 3. Open Browser
Navigate to: http://localhost:8501

### 4. Process Video
- Upload video file
- Configure settings
- Click "Start Processing"
- View results and download files

## Advanced Usage

### Direct Processing (No Jobs)
Use the `/api/process-direct` endpoint for immediate processing:
```python
import requests
import json

files = {"file": open("video.mp4", "rb")}
config = {
    "model": "yolov8n.pt",
    "conf_threshold": 0.25,
    "skip_frames": 1,
    "resize_factor": 1.0
}
data = {"config": json.dumps(config)}

response = requests.post(
    "http://localhost:8000/api/process-direct",
    files=files,
    data=data
)
result = response.json()
print(f"Entered: {result['total_enter']}, Exited: {result['total_exit']}")
```

## License

This project uses pretrained models and algorithms:
- YOLOv8: AGPL-3.0 License (Ultralytics)
- ByteTrack: MIT License
- FastAPI: MIT License
- Streamlit: Apache 2.0 License

## Contributing

This is a production-ready system. For improvements:
1. Ensure code follows PEP 8 style guide
2. Add comments for complex logic
3. Test with various video sources
4. Maintain backward compatibility
5. Update documentation for new features

## Acknowledgments

- **YOLOv8**: Ultralytics (https://github.com/ultralytics/ultralytics)
- **ByteTrack**: ByteTrack algorithm for multi-object tracking
- **OpenCV**: Computer vision library
- **FastAPI**: Modern web framework for building APIs
- **Streamlit**: Framework for building web apps

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed correctly
3. Test with a simple video file first
4. Check console output for error messages
5. Review API documentation at `/docs` endpoint

## Changelog

### Version 2.0 (Latest)
- ✨ Added web interface with Streamlit
- ✨ Added FastAPI backend for API access
- ✨ Added direct processing endpoint
- ⚡ Performance optimizations (frame skipping, resizing)
- 📊 Real-time results visualization
- 📥 Easy file downloads
- 🌐 Modern, user-friendly interface

### Version 1.0
- Initial release with CLI interface
- YOLOv8 person detection
- ByteTrack tracking
- Line crossing detection
- CSV export

---

**Note**: This system uses only pretrained models - no training or fine-tuning is required. All models are downloaded automatically on first use.

