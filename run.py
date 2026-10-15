"""Start the CabinetSight backend server."""
import os
import uvicorn

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
