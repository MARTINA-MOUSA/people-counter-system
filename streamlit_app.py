"""
Streamlit entry point with integrated Backend API
This file runs both Frontend and Backend in the same process for Streamlit Cloud
"""

import os
import sys
import threading
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Check if backend is already running
BACKEND_STARTED = False
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

def start_backend():
    """Start FastAPI backend in background thread."""
    global BACKEND_STARTED
    
    if BACKEND_STARTED:
        return
    
    try:
        import uvicorn
        from backend.api import app
        
        # Start server in background thread
        def run_server():
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=BACKEND_PORT,
                log_level="error"  # Reduce logs
            )
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait a bit for server to start
        time.sleep(2)
        
        BACKEND_STARTED = True
        print(f"✅ Backend API started on port {BACKEND_PORT}")
        
    except Exception as e:
        print(f"⚠️ Could not start backend: {e}")
        print("Frontend will still work but API features may not be available.")

# Start backend automatically
start_backend()

# Import and run the frontend app
import frontend.app
