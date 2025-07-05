
# Vehicle Detection API Backend

## Setup Instructions

1. **Install Python 3.8+** if not already installed

2. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

3. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment:**
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

5. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Run the server:**
   ```bash
   python run.py
   ```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

## Key Features

- Real-time vehicle detection using your Roboflow model
- Configurable confidence and overlap thresholds
- Proper classification to avoid false emergency vehicle detections
- Optimized for speed and accuracy
- CORS enabled for frontend communication

## Model Configuration

- **Model:** toy-vehicle-detection-te7wp/3
- **API Key:** qDrma4OYH0YLt5Wh8iEp (configured in main.py)
- **Default Confidence:** 50%
- **Default Overlap:** 50%
