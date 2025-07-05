import uvicorn
from main import app

if __name__ == "__main__":
    print("Starting Vehicle Detection API Server...")
    print("API will be available at: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    
    # Note: reload=True won't work properly here unless you use CLI.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
