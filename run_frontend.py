"""
Run the Streamlit frontend
"""

import subprocess
import sys
import socket

def find_free_port(start_port=8501, max_attempts=10):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return None

if __name__ == "__main__":
    # Try to use port 8501, or find a free port
    port = 8501
    try:
        # Test if port is available
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
    except OSError:
        print(f"Port {port} is not available. Searching for free port...")
        port = find_free_port(8501)
        if port is None:
            print("Error: Could not find a free port. Please close other applications.")
            sys.exit(1)
        print(f"Using port {port} instead.")
    
    print(f"Starting frontend on http://localhost:{port}")
    print(f"🌐 Open your browser and go to: http://localhost:{port}\n")
    
    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "frontend/app.py",
        f"--server.port={port}",
        "--server.address=localhost"
    ])

