"""
FastAPI Backend for People Counter System
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import cv2
import os
import json
import uuid
from datetime import datetime
import asyncio
from pathlib import Path

import sys
from pathlib import Path

# Add parent directory to path
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

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

app = FastAPI(title="People Counter API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
processing_jobs: Dict[str, Dict] = {}

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"

# Create directories
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)


class ProcessingConfig(BaseModel):
    model: str = "yolov8n.pt"
    conf_threshold: float = 0.25
    line_orientation: str = "horizontal"
    line_position: float = 0.5
    debug: bool = False
    skip_frames: int = 1  # Process every N frames (1 = all frames, 2 = every other frame)
    resize_factor: float = 1.0  # Resize video (1.0 = original, 0.5 = half size)


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    total_enter: int
    total_exit: int
    current_occupancy: int
    message: Optional[str] = None


def setup_counting_line(frame_height: int, frame_width: int, orientation: str, position: float):
    """Setup counting line based on frame dimensions."""
    if orientation == "horizontal":
        y = int(frame_height * position)
        line_start = (0, y)
        line_end = (frame_width, y)
    else:  # vertical
        x = int(frame_width * position)
        line_start = (x, 0)
        line_end = (x, frame_height)
    return line_start, line_end


def process_video(job_id: str, video_path: str, config: ProcessingConfig):
    """Process video in background."""
    try:
        processing_jobs[job_id]["status"] = "processing"
        processing_jobs[job_id]["message"] = "Initializing..."
        
        # Initialize components
        detector = PersonDetector(model_path=config.model, conf_threshold=config.conf_threshold)
        tracker = ByteTracker()
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Apply resize factor
        frame_width = int(original_width * config.resize_factor)
        frame_height = int(original_height * config.resize_factor)
        
        # Setup counting line (adjust for resized dimensions)
        line_start, line_end = setup_counting_line(
            frame_height, frame_width, config.line_orientation, config.line_position
        )
        counter = LineCounter(line_start, line_end, config.line_orientation, debug=config.debug)
        
        # Setup output video
        output_path = OUTPUT_DIR / f"{job_id}_output.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(
            str(output_path), fourcc, fps, (frame_width, frame_height)
        )
        
        # FPS counter
        fps_counter = FPSCounter()
        
        # Process frames
        frame_count = 0
        processed_frames = 0
        skip_counter = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize frame if needed
            if config.resize_factor != 1.0:
                frame = cv2.resize(frame, (frame_width, frame_height))
            
            # Skip frames for faster processing
            skip_counter += 1
            if skip_counter < config.skip_frames:
                # Still write frame to output but don't process
                frame = draw_counting_line(frame, line_start, line_end)
                # Get last known counts
                total_enter = processing_jobs[job_id].get("total_enter", 0)
                total_exit = processing_jobs[job_id].get("total_exit", 0)
                current_occupancy = processing_jobs[job_id].get("current_occupancy", 0)
                frame = draw_counters(frame, total_enter, total_exit, current_occupancy)
                video_writer.write(frame)
                frame_count += 1
                continue
            
            skip_counter = 0
            processed_frames += 1
            
            # Detect persons
            detections = detector.detect(frame)
            
            # Track persons
            tracks = tracker.update(detections)
            
            # Update counting
            timestamp = frame_count / fps
            total_enter, total_exit, current_occupancy = counter.update(tracks, timestamp)
            
            # Update job status (only every 10 frames to reduce overhead)
            if processed_frames % 10 == 0:
                processing_jobs[job_id]["total_enter"] = total_enter
                processing_jobs[job_id]["total_exit"] = total_exit
                processing_jobs[job_id]["current_occupancy"] = current_occupancy
                processing_jobs[job_id]["progress"] = (frame_count / total_frames * 100) if total_frames > 0 else 0
                processing_jobs[job_id]["fps"] = fps_counter.update()
            
            # Draw on frame
            frame = draw_counting_line(frame, line_start, line_end)
            for track in tracks:
                x1, y1, x2, y2, track_id, conf = track
                frame = draw_bounding_box(frame, (x1, y1, x2, y2), track_id, conf)
            frame = draw_counters(frame, total_enter, total_exit, current_occupancy)
            frame = draw_fps(frame, fps_counter.fps)
            
            # Write frame
            video_writer.write(frame)
            frame_count += 1
        
        # Cleanup
        cap.release()
        video_writer.release()
        
        # Save results
        history = counter.get_history()
        results_path = RESULTS_DIR / f"{job_id}_results.csv"
        if history:
            import csv
            with open(results_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'track_id', 'direction', 'total_enter', 'total_exit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(history)
        
        # Update job status
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["message"] = "Processing completed"
        processing_jobs[job_id]["output_video"] = str(output_path)
        processing_jobs[job_id]["results_csv"] = str(results_path) if history else None
        
    except Exception as e:
        processing_jobs[job_id]["status"] = "error"
        processing_jobs[job_id]["message"] = str(e)
        print(f"Error processing video: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "People Counter API", "version": "1.0.0"}


@app.post("/api/upload", response_model=Dict)
async def upload_video(
    file: UploadFile = File(...),
    config: Optional[str] = None
):
    """Upload video for processing."""
    try:
        # Parse config if provided
        processing_config = ProcessingConfig()
        if config:
            config_dict = json.loads(config)
            processing_config = ProcessingConfig(**config_dict)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize job
        processing_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0.0,
            "total_enter": 0,
            "total_exit": 0,
            "current_occupancy": 0,
            "fps": 0.0,
            "message": "Video uploaded, waiting to process...",
            "input_file": str(file_path),
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "job_id": job_id,
            "message": "Video uploaded successfully",
            "status": "queued"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process/{job_id}")
async def start_processing(job_id: str, background_tasks: BackgroundTasks, config: Optional[str] = None):
    """Start processing a video."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if processing_jobs[job_id]["status"] == "processing":
        raise HTTPException(status_code=400, detail="Job is already processing")
    
    # Parse config
    processing_config = ProcessingConfig()
    if config:
        config_dict = json.loads(config)
        processing_config = ProcessingConfig(**config_dict)
    
    # Get video path
    video_path = processing_jobs[job_id]["input_file"]
    
    # Start background processing
    background_tasks.add_task(process_video, job_id, video_path, processing_config)
    
    return {"message": "Processing started", "job_id": job_id}


@app.post("/api/process-direct")
async def process_video_direct(
    file: UploadFile = File(...),
    config: Optional[str] = None
):
    """Process video directly and return results."""
    try:
        # Parse config
        processing_config = ProcessingConfig()
        if config:
            config_dict = json.loads(config)
            processing_config = ProcessingConfig(**config_dict)
        
        # Save uploaded file temporarily
        temp_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"temp_{temp_id}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process video synchronously
        result = await process_video_sync(temp_id, str(file_path), processing_config)
        
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_video_sync(job_id: str, video_path: str, config: ProcessingConfig):
    """Process video synchronously and return results."""
    try:
        # Initialize components
        detector = PersonDetector(model_path=config.model, conf_threshold=config.conf_threshold)
        tracker = ByteTracker()
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        # Get video properties
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Apply resize factor
        frame_width = int(original_width * config.resize_factor)
        frame_height = int(original_height * config.resize_factor)
        
        # Setup counting line
        line_start, line_end = setup_counting_line(
            frame_height, frame_width, config.line_orientation, config.line_position
        )
        counter = LineCounter(line_start, line_end, config.line_orientation, debug=config.debug)
        
        # Setup output video
        output_path = OUTPUT_DIR / f"{job_id}_output.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(
            str(output_path), fourcc, fps, (frame_width, frame_height)
        )
        
        # FPS counter
        fps_counter = FPSCounter()
        
        # Process frames
        frame_count = 0
        processed_frames = 0
        skip_counter = 0
        total_enter = 0
        total_exit = 0
        current_occupancy = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Resize frame if needed
            if config.resize_factor != 1.0:
                frame = cv2.resize(frame, (frame_width, frame_height))
            
            # Skip frames for faster processing
            skip_counter += 1
            if skip_counter < config.skip_frames:
                # Still write frame to output but don't process
                frame = draw_counting_line(frame, line_start, line_end)
                frame = draw_counters(frame, total_enter, total_exit, current_occupancy)
                video_writer.write(frame)
                frame_count += 1
                continue
            
            skip_counter = 0
            processed_frames += 1
            
            # Detect persons
            detections = detector.detect(frame)
            
            # Track persons
            tracks = tracker.update(detections)
            
            # Update counting
            timestamp = frame_count / fps
            total_enter, total_exit, current_occupancy = counter.update(tracks, timestamp)
            
            # Draw on frame
            frame = draw_counting_line(frame, line_start, line_end)
            for track in tracks:
                x1, y1, x2, y2, track_id, conf = track
                frame = draw_bounding_box(frame, (x1, y1, x2, y2), track_id, conf)
            frame = draw_counters(frame, total_enter, total_exit, current_occupancy)
            frame = draw_fps(frame, fps_counter.update())
            
            # Write frame
            video_writer.write(frame)
            frame_count += 1
        
        # Cleanup
        cap.release()
        video_writer.release()
        
        # Save results
        history = counter.get_history()
        results_path = RESULTS_DIR / f"{job_id}_results.csv"
        if history:
            import csv
            with open(results_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['timestamp', 'track_id', 'direction', 'total_enter', 'total_exit']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(history)
        
        return {
            "status": "completed",
            "total_enter": total_enter,
            "total_exit": total_exit,
            "current_occupancy": current_occupancy,
            "output_video": str(output_path),
            "results_csv": str(results_path) if history else None,
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        total_enter=job["total_enter"],
        total_exit=job["total_exit"],
        current_occupancy=job["current_occupancy"],
        message=job.get("message")
    )


@app.get("/api/download/{job_id}/video")
async def download_video(job_id: str):
    """Download processed video."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if processing_jobs[job_id]["status"] != "completed":
        raise HTTPException(status_code=400, detail="Video not ready yet")
    
    video_path = processing_jobs[job_id].get("output_video")
    if not video_path or not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{job_id}_output.mp4"
    )


@app.get("/api/download/{job_id}/results")
async def download_results(job_id: str):
    """Download results CSV."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Results not ready yet")
    
    csv_path = job.get("results_csv")
    if not csv_path:
        # Create empty CSV if no results
        csv_path = RESULTS_DIR / f"{job_id}_results.csv"
        import csv
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['timestamp', 'track_id', 'direction', 'total_enter', 'total_exit']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        job["results_csv"] = str(csv_path)
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Results file not found")
    
    return FileResponse(
        csv_path,
        media_type="text/csv",
        filename=f"{job_id}_results.csv"
    )


@app.get("/api/jobs")
async def list_jobs():
    """List all jobs."""
    return {
        "jobs": [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "progress": job["progress"],
                "created_at": job.get("created_at")
            }
            for job in processing_jobs.values()
        ]
    }


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    # Delete files
    if "input_file" in job and os.path.exists(job["input_file"]):
        os.remove(job["input_file"])
    if "output_video" in job and os.path.exists(job["output_video"]):
        os.remove(job["output_video"])
    if "results_csv" in job and job["results_csv"] and os.path.exists(job["results_csv"]):
        os.remove(job["results_csv"])
    
    del processing_jobs[job_id]
    
    return {"message": "Job deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

