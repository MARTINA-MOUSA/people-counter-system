"""
Streamlit entry point with integrated Backend API
This file runs both Frontend and Backend in the same process for Streamlit Cloud
"""

import os
import sys
import threading
import time
import socket
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Global lock to prevent concurrent backend starts
_backend_lock = threading.Lock()
BACKEND_STARTED = False
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is already in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result == 0
    except Exception:
        return False

def is_backend_running(port: int) -> bool:
    """Check if backend is already running by making HTTP request."""
    try:
        import requests
        response = requests.get(f"http://127.0.0.1:{port}/", timeout=1)
        return response.status_code == 200
    except Exception:
        return False

def start_backend():
    """Start FastAPI backend in background thread."""
    global BACKEND_STARTED
    
    # Use lock to prevent concurrent starts
    with _backend_lock:
        if BACKEND_STARTED:
            return
        
        # Check if backend is already running
        if is_backend_running(BACKEND_PORT):
            print(f"✅ Backend API already running on port {BACKEND_PORT}")
            BACKEND_STARTED = True
            return
        
        # Check if port is in use (but not by our backend)
        if is_port_in_use(BACKEND_PORT):
            print(f"⚠️ Port {BACKEND_PORT} is already in use. Backend may already be running.")
            # Try to verify it's our backend
            if is_backend_running(BACKEND_PORT):
                BACKEND_STARTED = True
                return
            else:
                print(f"⚠️ Port {BACKEND_PORT} is in use by another process. Skipping backend start.")
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
                except OSError as e:
                    if "address already in use" in str(e).lower():
                        print(f"✅ Backend already running on port {BACKEND_PORT}")
                    else:
                        print(f"⚠️ Backend server error: {e}")
                except Exception as e:
                    print(f"⚠️ Backend server error: {e}")
            
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            
            # Wait a bit for server to start and verify it's running
            time.sleep(2)
            
            # Verify backend is running
            if is_backend_running(BACKEND_PORT):
                BACKEND_STARTED = True
                print(f"✅ Backend API started successfully on port {BACKEND_PORT}")
            else:
                print(f"⚠️ Backend may still be starting...")
        
        except Exception as e:
            print(f"⚠️ Could not start backend: {e}")
            import traceback
            traceback.print_exc()
            print("Frontend will still work but API features may not be available.")

# Start backend automatically (only if not already started)
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
