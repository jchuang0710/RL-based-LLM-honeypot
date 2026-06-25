"""
Run the FastAPI application

Usage:
    python -m src.api.run [--mode train|test] [--port PORT]
    
    --mode: 'train' for training mode, 'test' for test mode (default: 'train')
    --port: Port number for the API server (default: 8000)
"""
import uvicorn
import sys
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='FastAPI Honeypot Server')
    parser.add_argument('--mode', type=str, choices=['train', 'test'], default='train',
                        help='Mode: train (training mode) or test (test mode with loaded model)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Port number for the API server (default: 8000)')
    args = parser.parse_args()
    
    # Pass mode to uvicorn via environment variable or modify main.py to read from sys.argv
    # For now, we'll modify the startup to read from sys.argv
    if '--mode' not in sys.argv:
        sys.argv.extend(['--mode', args.mode])
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=args.port,
        reload=True
    )
