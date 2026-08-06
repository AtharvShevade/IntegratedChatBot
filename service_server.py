from __future__ import annotations
 
import os
import sys
import uvicorn
 
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
 
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
 
if __name__ == "__main__":
    print("[SERVICE] Starting FastAPI backend...")
 
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info",
    )