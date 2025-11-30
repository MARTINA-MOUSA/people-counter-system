"""
Streamlit Frontend for People Counter System
"""

import streamlit as st
import requests
import time
import json
from io import BytesIO
from pathlib import Path
import pandas as pd

# API Configuration
import os
API_PORT = os.getenv("API_PORT", "8000")
API_BASE_URL = f"http://localhost:{API_PORT}"

# Page configuration
st.set_page_config(
    page_title="People Counter System",
    page_icon="👥",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">👥 People Counter System</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Model selection
    model = st.selectbox(
        "YOLOv8 Model",
        ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"],
        index=0,
        help="Select YOLOv8 model size (nano is fastest, xlarge is most accurate)"
    )
    
    # Confidence threshold
    conf_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.1,
        max_value=1.0,
        value=0.25,
        step=0.05,
        help="Detection confidence threshold"
    )
    
    # Line orientation
    line_orientation = st.selectbox(
        "Counting Line Orientation",
        ["horizontal", "vertical"],
        index=0
    )
    
    # Line position
    line_position = st.slider(
        "Line Position",
        min_value=0.0,
        max_value=1.0,
        value=0.5,
        step=0.1,
        help="Position of counting line (0.0 = top/left, 1.0 = bottom/right)"
    )
    
    # Debug mode
    debug = st.checkbox("Debug Mode", value=False, help="Enable debug output")
    
    # Performance settings
    st.markdown("---")
    st.markdown("### ⚡ Performance")
    skip_frames = st.slider(
        "Skip Frames",
        min_value=1,
        max_value=5,
        value=1,
        help="Process every N frames (1=all frames, 2=every other frame, etc.)"
    )
    resize_factor = st.slider(
        "Resize Factor",
        min_value=0.3,
        max_value=1.0,
        value=1.0,
        step=0.1,
        help="Resize video for faster processing (1.0=original size)"
    )
    
    st.markdown("---")
    st.markdown("### 📊 API Status")
    
    # API Port Configuration
    st.markdown("#### 🔌 API Settings")
    custom_port = st.text_input("API Port", value=API_PORT, key="api_port", help="Change if backend is on different port")
    api_url = f"http://localhost:{custom_port}" if custom_port else API_BASE_URL
    
    # Update session state
    if 'api_base_url' not in st.session_state:
        st.session_state.api_base_url = api_url
    
    # Check API connection
    try:
        response = requests.get(f"{api_url}/", timeout=2)
        if response.status_code == 200:
            st.success(f"✅ API Connected on port {custom_port}")
        else:
            st.error("❌ API Error")
    except:
        st.error(f"❌ API Not Available on port {custom_port}")
        st.info("Please start the backend API server first:\n```bash\npython run_backend.py\n```\nOr if using different port:\n```bash\npython run_backend.py --port 8001\n```")

# Main content - Single page for upload and processing
st.header("📹 رفع ومعالجة الفيديو")

uploaded_file = st.file_uploader(
    "اختر ملف فيديو",
    type=['mp4', 'avi', 'mov', 'mkv'],
    help="Upload a video file to process"
)

if uploaded_file is not None:
    # Display video info
    st.info(f"📁 الملف: {uploaded_file.name} | الحجم: {uploaded_file.size / (1024*1024):.2f} MB")
    
    # Process button
    if st.button("🚀 بدء المعالجة", type="primary", use_container_width=True):
        try:
            # Prepare config
            config = {
                "model": model,
                "conf_threshold": conf_threshold,
                "line_orientation": line_orientation,
                "line_position": line_position,
                "debug": debug,
                "skip_frames": skip_frames,
                "resize_factor": resize_factor
            }
            
            # Process video directly
            api_url = st.session_state.get('api_base_url', API_BASE_URL)
            
            with st.spinner("⏳ جاري معالجة الفيديو... قد يستغرق هذا بعض الوقت"):
                # Reset file pointer
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file.read(), uploaded_file.type)}
                data = {"config": json.dumps(config)}
                
                response = requests.post(
                    f"{api_url}/api/process-direct",
                    files=files,
                    data=data,
                    timeout=600  # 10 minutes timeout
                )
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.processing_result = result
                st.success("✅ تمت المعالجة بنجاح!")
            else:
                st.error(f"❌ خطأ في المعالجة: {response.text}")
                
        except Exception as e:
            st.error(f"❌ خطأ: {str(e)}")

# Display results if available
if "processing_result" in st.session_state:
    result = st.session_state.processing_result
    
    st.markdown("---")
    st.header("📊 النتائج")
    
    # Statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 دخل", result["total_enter"])
    
    with col2:
        st.metric("🚪 خرج", result["total_exit"])
    
    with col3:
        st.metric("📍 الحالي", result["current_occupancy"])
    
    # Download buttons
    st.markdown("---")
    st.subheader("📥 تحميل النتائج")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if result.get("output_video"):
            try:
                api_url = st.session_state.get('api_base_url', API_BASE_URL)
                video_path = result["output_video"]
                
                # Download video file
                if st.button("📹 تحميل الفيديو المعالج", use_container_width=True):
                    try:
                        # Read video file and provide download
                        with open(video_path, 'rb') as f:
                            video_bytes = f.read()
                        st.download_button(
                            label="⬇️ اضغط للتحميل",
                            data=video_bytes,
                            file_name=Path(video_path).name,
                            mime="video/mp4",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"خطأ في تحميل الفيديو: {str(e)}")
            except Exception as e:
                st.info(f"الفيديو: {result.get('output_video', 'غير متاح')}")
    
    with col2:
        if result.get("results_csv"):
            try:
                csv_path = result["results_csv"]
                
                # Download CSV file
                if st.button("📊 تحميل ملف CSV", use_container_width=True):
                    try:
                        # Read CSV file and provide download
                        with open(csv_path, 'rb') as f:
                            csv_bytes = f.read()
                        st.download_button(
                            label="⬇️ اضغط للتحميل",
                            data=csv_bytes,
                            file_name=Path(csv_path).name,
                            mime="text/csv",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"خطأ في تحميل CSV: {str(e)}")
            except Exception as e:
                st.info(f"CSV: {result.get('results_csv', 'غير متاح')}")
    
    # Display history if available
    if result.get("history"):
        st.markdown("---")
        st.subheader("📈 تفاصيل الأحداث")
        history_df = pd.DataFrame(result["history"])
        st.dataframe(history_df, use_container_width=True)
        
        # Chart
        if len(history_df) > 0:
            st.subheader("📊 الرسم البياني")
            history_df['timestamp'] = pd.to_numeric(history_df['timestamp'])
            chart_data = history_df.groupby(['timestamp', 'direction']).size().reset_index(name='count')
            st.line_chart(chart_data.pivot(index='timestamp', columns='direction', values='count'), use_container_width=True)
    
    # Clear results button
    if st.button("🗑️ مسح النتائج", use_container_width=True):
        if "processing_result" in st.session_state:
            del st.session_state.processing_result
        st.rerun()

# Keep old tabs for backward compatibility
tab1, tab2, tab3 = st.tabs(["📹 Upload & Process (Old)", "📊 Job Status", "📈 Results"])

with tab1:
    st.info("استخدم الواجهة الرئيسية أعلاه للمعالجة المباشرة")

with tab2:
    st.header("Job Status")
    
    # Get job ID
    if "current_job_id" in st.session_state:
        job_id = st.text_input("Job ID", value=st.session_state.current_job_id)
    else:
        job_id = st.text_input("Job ID", placeholder="Enter job ID or select from list")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔍 Check Status", type="primary"):
            if job_id:
                try:
                    api_url = st.session_state.get('api_base_url', API_BASE_URL)
                    response = requests.get(f"{api_url}/api/status/{job_id}", timeout=5)
                    if response.status_code == 200:
                        status = response.json()
                        st.session_state.current_status = status
                    else:
                        st.error(f"Job not found: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter a job ID")
    
    with col2:
        if st.button("📋 List All Jobs"):
            try:
                api_url = st.session_state.get('api_base_url', API_BASE_URL)
                response = requests.get(f"{api_url}/api/jobs", timeout=5)
                if response.status_code == 200:
                    jobs = response.json()["jobs"]
                    if jobs:
                        st.session_state.jobs_list = jobs
                    else:
                        st.info("No jobs found")
                else:
                    st.error("Error fetching jobs")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Display jobs list
    if "jobs_list" in st.session_state:
        st.subheader("All Jobs")
        jobs_df = pd.DataFrame(st.session_state.jobs_list)
        st.dataframe(jobs_df, use_container_width=True)
    
    # Display current status
    if "current_status" in st.session_state:
        status = st.session_state.current_status
        
        st.markdown("---")
        st.subheader("Current Job Status")
        
        # Status indicator
        if status["status"] == "completed":
            st.success(f"✅ Status: {status['status'].upper()}")
        elif status["status"] == "processing":
            st.info(f"🔄 Status: {status['status'].upper()}")
        elif status["status"] == "error":
            st.error(f"❌ Status: {status['status'].upper()}")
        else:
            st.warning(f"⏳ Status: {status['status'].upper()}")
        
        # Progress bar
        if status["status"] == "processing":
            st.progress(status["progress"] / 100)
            st.caption(f"Progress: {status['progress']:.1f}%")
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Entered", status["total_enter"])
        
        with col2:
            st.metric("Exited", status["total_exit"])
        
        with col3:
            st.metric("Current Occupancy", status["current_occupancy"])
        
        # Message
        if status.get("message"):
            st.info(f"ℹ️ {status['message']}")
        
        # Download buttons
        if status["status"] == "completed":
            st.markdown("---")
            st.subheader("Download Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Download Video", use_container_width=True):
                    try:
                        api_url = st.session_state.get('api_base_url', API_BASE_URL)
                        response = requests.get(
                            f"{api_url}/api/download/{job_id}/video",
                            timeout=300,
                            stream=True
                        )
                        if response.status_code == 200:
                            st.download_button(
                                label="⬇️ Click to Download Video",
                                data=response.content,
                                file_name=f"{job_id}_output.mp4",
                                mime="video/mp4",
                                use_container_width=True
                            )
                        else:
                            st.error("Error downloading video")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            with col2:
                if st.button("📊 Download CSV Results", use_container_width=True):
                    try:
                        api_url = st.session_state.get('api_base_url', API_BASE_URL)
                        response = requests.get(
                            f"{api_url}/api/download/{job_id}/results",
                            timeout=30
                        )
                        if response.status_code == 200:
                            st.download_button(
                                label="⬇️ Click to Download CSV",
                                data=response.content,
                                file_name=f"{job_id}_results.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.error("Error downloading results")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
        
        # Auto-refresh for processing jobs
        if status["status"] == "processing":
            time.sleep(2)
            st.rerun()

with tab3:
    st.header("Results Analysis")
    
    if "current_job_id" in st.session_state:
        job_id = st.session_state.current_job_id
        
        # Try to load results
        try:
            api_url = st.session_state.get('api_base_url', API_BASE_URL)
            response = requests.get(
                f"{api_url}/api/download/{job_id}/results",
                timeout=30
            )
            if response.status_code == 200:
                # Parse CSV
                from io import StringIO
                csv_data = StringIO(response.text)
                df = pd.read_csv(csv_data)
                
                st.subheader("Counting Events")
                st.dataframe(df, use_container_width=True)
                
                # Statistics
                st.subheader("Statistics")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Entered", len(df[df['direction'] == 'enter']))
                
                with col2:
                    st.metric("Total Exited", len(df[df['direction'] == 'exit']))
                
                with col3:
                    st.metric("Unique Tracks", df['track_id'].nunique())
                
                with col4:
                    st.metric("Total Events", len(df))
                
                # Charts
                if len(df) > 0:
                    st.subheader("Timeline")
                    df['timestamp'] = pd.to_numeric(df['timestamp'])
                    chart_data = df.groupby(['timestamp', 'direction']).size().reset_index(name='count')
                    st.line_chart(chart_data.pivot(index='timestamp', columns='direction', values='count'), use_container_width=True)
            else:
                st.info("No results available yet. Please process a video first.")
        except Exception as e:
            st.info("No results available yet. Please process a video first.")
    else:
        st.info("Please upload and process a video first.")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>People Counter System | Built with Streamlit & FastAPI</p>
    </div>
""", unsafe_allow_html=True)

