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
API_PORT = os.getenv("API_PORT", os.getenv("BACKEND_PORT", "8000"))

# For Streamlit Cloud, backend runs in same process on localhost
# For local development, also use localhost
API_BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{API_PORT}")

# On Streamlit Cloud, backend is integrated and runs automatically
if os.getenv("STREAMLIT_SERVER_PORT"):
    # Backend is started automatically in streamlit_app.py
    pass

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
    custom_port = st.text_input("API Port", value=str(API_PORT), key="api_port", help="Change if backend is on different port")
    # Use 127.0.0.1 for localhost connections
    api_url = f"http://127.0.0.1:{custom_port}" if custom_port else API_BASE_URL
    
    # Update session state
    if 'api_base_url' not in st.session_state:
        st.session_state.api_base_url = api_url
    
    # Check API connection
    try:
        response = requests.get(f"{api_url}/", timeout=3)
        if response.status_code == 200:
            st.success(f"✅ API Connected on port {custom_port}")
            st.session_state.api_connected = True
        else:
            st.error("❌ API Error")
            st.session_state.api_connected = False
    except Exception as e:
        st.session_state.api_connected = False
        
        # Check if we're on Streamlit Cloud (backend should auto-start)
        if os.getenv("STREAMLIT_SERVER_PORT"):
            st.warning(f"⏳ Backend is starting... Please wait a moment and refresh.")
            st.info("""
            **Note:** On Streamlit Cloud, the backend starts automatically.
            If this message persists, the backend may need a moment to initialize.
            """)
        else:
            # Local development
            st.error(f"❌ API Not Available on port {custom_port}")
            st.info("""
            **To start the backend API locally:**
            
            ```bash
            uvicorn backend.api:app --host 127.0.0.1 --port 8000 --reload
            ```
            
            Or if port 8000 is busy:
            ```bash
            uvicorn backend.api:app --host 127.0.0.1 --port 8001 --reload
            ```
            """)

# Main content - Single page for upload and processing
st.header("📹 رفع ومعالجة الفيديو")

# Save uploaded file to session state to prevent it from disappearing on rerun
uploaded_file = st.file_uploader(
    "اختر ملف فيديو",
    type=['mp4', 'avi', 'mov', 'mkv'],
    help="Upload a video file to process",
    key="video_uploader"
)

# Store file info (not bytes) in session state when uploaded
# Note: We don't save file bytes to session_state to avoid memory issues
if uploaded_file is not None:
    try:
        # Check file size (limit to 500MB to prevent memory issues)
        max_size_mb = 500
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if uploaded_file.size > max_size_bytes:
            st.error(f"❌ حجم الملف كبير جداً ({uploaded_file.size / (1024*1024):.2f} MB). الحد الأقصى: {max_size_mb} MB")
            # Clear any previous file info
            if 'uploaded_file_info' in st.session_state:
                del st.session_state.uploaded_file_info
        else:
            # Save only file info (not bytes) to session state
            st.session_state.uploaded_file_info = {
                'name': uploaded_file.name,
                'size': uploaded_file.size,
                'type': uploaded_file.type
            }
    except Exception as e:
        st.error(f"❌ خطأ في قراءة الملف: {str(e)}")
        import traceback
        with st.expander("🔍 تفاصيل الخطأ"):
            st.code(traceback.format_exc())

# Use file if available
file_bytes = None
file_name = None
file_size = None
file_type = None

try:
    if uploaded_file is not None:
        # File is currently uploaded - use it directly
        file_name = uploaded_file.name
        file_size = uploaded_file.size
        file_type = uploaded_file.type
        # Don't read bytes yet - we'll read them only when processing
        file_available = True
    elif 'uploaded_file_info' in st.session_state:
        # File info is saved but file itself is not available (rerun happened)
        file_name = st.session_state.uploaded_file_info.get('name')
        file_size = st.session_state.uploaded_file_info.get('size')
        file_type = st.session_state.uploaded_file_info.get('type', 'video/mp4')
        file_available = False
        st.warning("⚠️ الملف غير متاح. يرجى رفع الملف مرة أخرى.")
    else:
        file_available = False
    
    if file_available and file_name:
        # Display video info
        st.info(f"📁 الملف: {file_name} | الحجم: {file_size / (1024*1024):.2f} MB")
        
        # Process button (only show if file is available and not already processed)
        if uploaded_file is not None:
            # Check if already processed
            if st.session_state.get("processing_complete", False):
                st.success("✅ تمت معالجة هذا الملف مسبقاً. النتائج معروضة أدناه.")
                if st.button("🔄 إعادة المعالجة", use_container_width=True, key="reprocess_button"):
                    # Reset processing state
                    st.session_state.processing_complete = False
                    if "processing_result" in st.session_state:
                        del st.session_state.processing_result
                    st.rerun()
            else:
                if st.button("🚀 بدء المعالجة", type="primary", use_container_width=True, key="process_button"):
                    # Set processing state to prevent multiple clicks
                    st.session_state.processing = True
                    
                    try:
                        # Read file bytes only when processing (not before)
                        uploaded_file.seek(0)
                        file_bytes = uploaded_file.read()
                        uploaded_file.seek(0)  # Reset for potential reuse
                        
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
                            # Use file bytes
                            files = {"file": (file_name, file_bytes, file_type)}
                            data = {"config": json.dumps(config)}
                            
                            response = requests.post(
                                f"{api_url}/api/process-direct",
                                files=files,
                                data=data,
                                timeout=600  # 10 minutes timeout
                            )
                        
                        # Clear processing state
                        st.session_state.processing = False
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.session_state.processing_result = result
                            st.session_state.processing_complete = True
                            st.session_state.processed_file_name = file_name  # Save file name
                            st.success("✅ تمت المعالجة بنجاح!")
                            # Don't use st.rerun() - it causes page reload and video disappears
                            # Results will be displayed below automatically
                        else:
                            st.error(f"❌ خطأ في المعالجة: {response.text}")
                            try:
                                error_detail = response.json()
                                st.json(error_detail)
                            except:
                                pass
                            
                    except requests.exceptions.Timeout:
                        st.session_state.processing = False
                        st.error("❌ انتهت مهلة الاتصال. الملف كبير جداً أو الخادم بطيء.")
                        st.info("💡 جرب تقليل حجم الفيديو أو زيادة إعدادات Skip Frames في Sidebar")
                    except requests.exceptions.ConnectionError:
                        st.session_state.processing = False
                        st.error("❌ لا يمكن الاتصال بالخادم. تأكد من أن Backend يعمل.")
                        st.info("💡 على Streamlit Cloud، انتظر قليلاً ثم أعد تحميل الصفحة")
                    except Exception as e:
                        st.session_state.processing = False
                        st.error(f"❌ خطأ: {str(e)}")
                        import traceback
                        with st.expander("🔍 تفاصيل الخطأ"):
                            st.code(traceback.format_exc())
except Exception as e:
    st.error(f"❌ خطأ في معالجة الملف: {str(e)}")
    import traceback
    with st.expander("🔍 تفاصيل الخطأ"):
        st.code(traceback.format_exc())

# Display results if available (without rerun to prevent video disappearing)
# Only show results if processing is complete
if "processing_result" in st.session_state and st.session_state.get("processing_complete", False):
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
    if st.button("🗑️ مسح النتائج", use_container_width=True, key="clear_results"):
        if "processing_result" in st.session_state:
            del st.session_state.processing_result
        if "processing_complete" in st.session_state:
            del st.session_state.processing_complete
        # Use st.rerun() only when clearing, not when processing
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>People Counter System | Built with Streamlit & FastAPI</p>
    </div>
""", unsafe_allow_html=True)

