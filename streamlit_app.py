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
            try:
                uvicorn.run(
                    app,
                    host="127.0.0.1",
                    port=BACKEND_PORT,
                    log_level="error"  # Reduce logs
                )
            except Exception as e:
                print(f"⚠️ Backend server error: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait a bit for server to start and verify it's running
        time.sleep(3)
        
        # Verify backend is running
        try:
            import requests
            response = requests.get(f"http://127.0.0.1:{BACKEND_PORT}/", timeout=2)
            if response.status_code == 200:
                BACKEND_STARTED = True
                print(f"✅ Backend API started successfully on port {BACKEND_PORT}")
            else:
                print(f"⚠️ Backend started but health check failed")
        except Exception as e:
            print(f"⚠️ Backend may still be starting... Error: {e}")
        
    except Exception as e:
        print(f"⚠️ Could not start backend: {e}")
        import traceback
        traceback.print_exc()
        print("Frontend will still work but API features may not be available.")

# Start backend automatically (only if not already started)
if not BACKEND_STARTED:
    start_backend()

# Import and run the frontend app
# Note: frontend.app must be imported last as it contains Streamlit code that runs on import
try:
    import frontend.app
except Exception as e:
    # Fallback: show error message if import fails
    import streamlit as st
    st.error(f"❌ Error loading application: {e}")
    import traceback
    st.code(traceback.format_exc())
    st.info("Please check the deployment logs for more details.")
