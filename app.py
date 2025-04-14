import os
import logging
import uuid
import json
import shutil
import tempfile
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-dev-secret-key")
# Set session to use filesystem instead of signed cookies to avoid size limitations
app.config['SESSION_TYPE'] = 'filesystem'

# Import modules after app initialization to avoid circular imports
from detector import YOLODetector
from scheduler import TrafficScheduler
from visualizer import TrafficVisualizer

# Initialize modules
detector = YOLODetector()
scheduler = TrafficScheduler()
visualizer = TrafficVisualizer()

# Use temporary directories for uploads and results
TEMP_DIR = tempfile.gettempdir()
UPLOAD_FOLDER = os.path.join('static', 'uploads')
RESULTS_FOLDER = os.path.join('static', 'results')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

# Cleanup function to remove temporary files
def cleanup_temp_files(session_id):
    """Remove temporary files for this session"""
    if not session_id:
        return
        
    # Clean up upload directory
    session_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    if os.path.exists(session_upload_dir):
        shutil.rmtree(session_upload_dir)
        
    # Clean up results directory
    session_results_dir = os.path.join(app.config['RESULTS_FOLDER'], session_id)
    if os.path.exists(session_results_dir):
        shutil.rmtree(session_results_dir)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_images():
    """Handle image uploads and process them"""
    if 'lane_images' not in request.files:
        flash('No images uploaded', 'danger')
        return redirect(url_for('index'))
    
    files = request.files.getlist('lane_images')
    if not files or files[0].filename == '':
        flash('No images selected', 'danger')
        return redirect(url_for('index'))
    
    # Validate number of lanes
    if len(files) < 2 or len(files) > 4:
        flash('Please upload 2-4 lane images', 'danger')
        return redirect(url_for('index'))
    
    # Generate unique session ID for this analysis
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    
    # Create directories for this session
    session_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    session_results_dir = os.path.join(app.config['RESULTS_FOLDER'], session_id)
    os.makedirs(session_upload_dir, exist_ok=True)
    os.makedirs(session_results_dir, exist_ok=True)
    
    # Save uploaded images
    saved_paths = []
    try:
        for i, file in enumerate(files):
            if file and file.filename:
                lane_number = i + 1
                filename = f"lane_{lane_number}_{uuid.uuid4()}.jpg"
                filepath = os.path.join(session_upload_dir, filename)
                file.save(filepath)
                saved_paths.append((filepath, lane_number))
    except Exception as e:
        logging.error(f"Error saving uploaded files: {e}")
        flash(f"Error processing uploads: {str(e)}", 'danger')
        return redirect(url_for('index'))
    
    # Process images with YOLOv8
    try:
        results = []
        for img_path, lane_number in saved_paths:
            # Detect objects in image
            detections = detector.detect(img_path)
            
            # Calculate priority score
            priority_score = scheduler.calculate_priority(detections, lane_number)
            
            # Generate annotated image
            annotated_img_path = os.path.join(session_results_dir, f"annotated_lane_{lane_number}.jpg")
            visualizer.annotate_image(img_path, detections, annotated_img_path)
            
            # Add to results
            results.append({
                'lane_number': lane_number,
                'original_img': os.path.relpath(img_path, 'static'),
                'annotated_img': os.path.relpath(annotated_img_path, 'static'),
                'priority_score': priority_score,
                'counts': detections['counts'],
                'has_emergency': detections['has_emergency'],
                'has_jaywalkers': detections['has_jaywalkers']
            })
        
        # Determine which lane gets the green light
        green_lane = scheduler.select_green_light(results)
        
        # Store results in session
        session['results'] = results
        session['green_lane'] = green_lane
        
        return redirect(url_for('show_results'))
    
    except Exception as e:
        logging.error(f"Error processing images: {e}")
        flash(f"Error analyzing traffic: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/results')
def show_results():
    """Display traffic analysis results"""
    if 'results' not in session or 'green_lane' not in session:
        flash('No traffic analysis results available', 'warning')
        return redirect(url_for('index'))
    
    return render_template(
        'results.html',
        results=session['results'],
        green_lane=session['green_lane']
    )

@app.route('/simulator')
def simulator():
    """Render the traffic simulator page"""
    return render_template('simulator.html')

@app.route('/run-simulation', methods=['POST'])
def run_simulation():
    """Process simulation data and show results"""
    try:
        # Get the number of lanes
        lane_count = int(request.form.get('lane_count', 2))
        if lane_count < 2 or lane_count > 4:
            flash('Invalid number of lanes', 'danger')
            return redirect(url_for('simulator'))
        
        # Generate unique session ID for this simulation
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # Create results directory for this session
        session_results_dir = os.path.join(app.config['RESULTS_FOLDER'], session_id)
        os.makedirs(session_results_dir, exist_ok=True)
        
        # Get starvation control setting
        starvation_control = 'starvation_control' in request.form
        
        # Get previous green lane (for starvation control)
        try:
            prev_green = int(request.form.get('prev_green', 0))
        except:
            prev_green = 0
        
        # Process each lane
        results = []
        for lane_number in range(1, lane_count + 1):
            # Extract lane data from form
            try:
                vehicles = int(request.form.get(f'vehicles_{lane_number}', 0))
                pedestrians = int(request.form.get(f'pedestrians_{lane_number}', 0))
                jaywalkers = int(request.form.get(f'jaywalkers_{lane_number}', 0))
                emergency = f'emergency_{lane_number}' in request.form
                
                # Validate data
                if jaywalkers > pedestrians:
                    jaywalkers = pedestrians
                
                # Create simulated detections
                detections = create_simulated_detection(
                    vehicles, pedestrians, jaywalkers, emergency, lane_number
                )
                
                # Calculate priority score (with starvation control)
                priority_score = calculate_simulated_priority(
                    detections, lane_number, prev_green, starvation_control
                )
                
                # Add to results
                results.append({
                    'lane_number': lane_number,
                    'priority_score': priority_score,
                    'counts': detections['counts'],
                    'has_emergency': detections['has_emergency'],
                    'has_jaywalkers': detections['has_jaywalkers']
                })
            except Exception as e:
                logging.error(f"Error processing lane {lane_number}: {e}")
                flash(f"Error with lane {lane_number} data: {str(e)}", 'danger')
                return redirect(url_for('simulator'))
        
        # Determine which lane gets the green light
        green_lane = scheduler.select_green_light(results)
        
        # Store results in session
        session['sim_results'] = results
        session['sim_green_lane'] = green_lane
        
        return redirect(url_for('simulation_results'))
    
    except Exception as e:
        logging.error(f"Error processing simulation: {e}")
        flash(f"Error running simulation: {str(e)}", 'danger')
        return redirect(url_for('simulator'))

@app.route('/simulation-results')
def simulation_results():
    """Display simulation results"""
    if 'sim_results' not in session or 'sim_green_lane' not in session:
        flash('No simulation results available', 'warning')
        return redirect(url_for('simulator'))
    
    return render_template(
        'simulation_results.html',
        results=session['sim_results'],
        green_lane=session['sim_green_lane']
    )

@app.route('/clear')
def clear_session():
    """Clear the session data and remove temporary files"""
    session_id = session.get('session_id')
    
    # Clean up any temporary files associated with this session
    if session_id:
        cleanup_temp_files(session_id)
        
    # Clear all session data
    session.clear()
    
    flash('Session cleared and temporary files removed', 'info')
    return redirect(url_for('index'))

def create_simulated_detection(vehicles, pedestrians, jaywalkers, has_emergency, lane_id):
    """Create simulated detection data for the traffic simulator"""
    # Basic detections data structure
    detections = {
        'counts': {
            'vehicles': vehicles,
            'pedestrians': pedestrians,
            'jaywalkers': jaywalkers,
            'emergency_vehicles': 1 if has_emergency else 0
        },
        'vehicles': [],
        'pedestrians': [],
        'emergency_vehicles': [],
        'jaywalkers': [],
        'has_emergency': has_emergency,
        'has_jaywalkers': jaywalkers > 0,
        'image_path': f'lane_{lane_id}_simulated',
        'image_shape': (480, 640, 3)  # dummy dimensions
    }
    
    return detections

def calculate_simulated_priority(detections, lane_id, prev_green=0, starvation_control=True):
    """Calculate priority score for simulated data"""
    # Get counts
    vehicle_count = detections['counts']['vehicles']
    pedestrian_count = detections['counts']['pedestrians']
    jaywalker_count = detections['counts']['jaywalkers']
    emergency_count = detections['counts']['emergency_vehicles']
    
    # Calculate base scores
    vehicle_score = vehicle_count * 1.0
    pedestrian_score = pedestrian_count * 0.5
    jaywalker_score = jaywalker_count * -0.25
    emergency_score = 100.0 if emergency_count > 0 else 0.0
    
    # Calculate starvation control bonus
    starvation_score = 0.0
    if starvation_control and prev_green > 0 and lane_id != prev_green:
        starvation_score = 2.0  # Small bonus for not being the previous green lane
    
    # Calculate total score
    total_score = vehicle_score + pedestrian_score + jaywalker_score + emergency_score + starvation_score
    
    # Prepare priority score result
    priority_score = {
        'total_score': total_score,
        'breakdown': {
            'vehicles': {
                'count': vehicle_count,
                'weight': 1.0,
                'score': vehicle_score
            },
            'pedestrians': {
                'count': pedestrian_count,
                'weight': 0.5,
                'score': pedestrian_score
            },
            'jaywalkers': {
                'count': jaywalker_count,
                'weight': -0.25,
                'score': jaywalker_score
            },
            'emergency_vehicles': {
                'count': emergency_count,
                'weight': 100.0 if emergency_count > 0 else 0.0,
                'score': emergency_score
            },
            'starvation_control': {
                'active': starvation_control and prev_green > 0,
                'prev_green': prev_green,
                'score': starvation_score
            }
        }
    }
    
    return priority_score

# Cleanup old files periodically
def cleanup_old_files(max_age_hours=24):
    """Clean up files older than the given age in hours"""
    try:
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        # Clean upload directory
        if os.path.exists(UPLOAD_FOLDER):
            for session_dir in os.listdir(UPLOAD_FOLDER):
                session_path = os.path.join(UPLOAD_FOLDER, session_dir)
                if os.path.isdir(session_path):
                    # Check if directory is older than max age
                    dir_modified_time = os.path.getmtime(session_path)
                    if current_time - dir_modified_time > max_age_seconds:
                        shutil.rmtree(session_path)
                        logging.info(f"Removed old upload directory: {session_path}")
        
        # Clean results directory
        if os.path.exists(RESULTS_FOLDER):
            for session_dir in os.listdir(RESULTS_FOLDER):
                session_path = os.path.join(RESULTS_FOLDER, session_dir)
                if os.path.isdir(session_path):
                    # Check if directory is older than max age
                    dir_modified_time = os.path.getmtime(session_path)
                    if current_time - dir_modified_time > max_age_seconds:
                        shutil.rmtree(session_path)
                        logging.info(f"Removed old results directory: {session_path}")
    
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

# Run cleanup on startup
import time
cleanup_old_files()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
