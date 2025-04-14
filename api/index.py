import os
import sys

# Add the parent directory to sys.path so we can import our application
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the Flask app from main.py
from main import app

# This is required for Vercel serverless functions
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)