"""
Run the FastAPI backend server
"""

import uvicorn
import sys
import socket
import argparse

def find_free_port(start_port=8000, max_attempts=20):
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return port
        except (OSError, socket.error):
            continue
    return None

def is_port_available(port):
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('127.0.0.1', port))
            return True
    except (OSError, socket.error):
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run People Counter Backend API")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    port = args.port
    
    # Check if port is available
    if not is_port_available(port):
        print(f"⚠️  Port {port} is not available. Searching for free port...")
        port = find_free_port(8000)
        if port is None:
            print("❌ Error: Could not find a free port. Please close other applications or specify a different port.")
            print("   Try: python run_backend.py --port 8001")
            sys.exit(1)
        print(f"✅ Using port {port} instead.")
    else:
        print(f"✅ Port {port} is available.")
    
    print(f"\n🚀 Starting backend server on http://localhost:{port}")
    print(f"📚 API documentation: http://localhost:{port}/docs")
    print(f"🔗 Frontend should connect to: http://localhost:{port}\n")
    
    try:
        uvicorn.run(
            "backend.api:app",
            host="127.0.0.1",
            port=port,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print(f"💡 Try using a different port: python run_backend.py --port 8001")
        sys.exit(1)

