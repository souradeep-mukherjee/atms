import os
import logging
from flask import Flask
from models import db, TrafficEvent, LaneData

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)

# Configure secret key for sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a-secure-development-key"

# Check database URL configuration
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    logger.warning("DATABASE_URL environment variable not found. Using SQLite database instead.")
    db_url = "sqlite:///traffic_analytics.db"

# Configure database connection
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the database with the app
db.init_app(app)

# Import the functions from app_with_db
from app_with_db import index, upload_images, simulator, run_simulation, stats, clear_session

# Register routes
app.add_url_rule('/', 'index', index)
app.add_url_rule('/upload', 'upload_images', upload_images, methods=['POST'])
app.add_url_rule('/simulator', 'simulator', simulator)
app.add_url_rule('/run-simulation', 'run_simulation', run_simulation, methods=['POST'])
app.add_url_rule('/stats', 'stats', stats)
app.add_url_rule('/clear_session', 'clear_session', clear_session)

# Create all tables if they don't exist yet
with app.app_context():
    db.create_all()
    logger.info("Database tables created or verified")

# Run the application when executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)