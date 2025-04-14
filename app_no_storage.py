import os
import logging
import tempfile
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-dev-secret-key")

# Import modules after app initialization to avoid circular imports
from detector import YOLODetector
from scheduler import TrafficScheduler
from visualizer import TrafficVisualizer

# Initialize modules
detector = YOLODetector()
scheduler = TrafficScheduler()
visualizer = TrafficVisualizer()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_images():
    """Handle image uploads and process them without storing data"""
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
    
    # Process images directly without saving to disk
    try:
        results = []
        for i, file in enumerate(files):
            if file and file.filename:
                lane_number = i + 1
                
                # Process the image directly
                file_data = file.read()
                
                # Create a temporary file for detection processing
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_file.write(file_data)
                    temp_path = temp_file.name
                
                try:
                    # Detect objects in image
                    detections = detector.detect(temp_path)
                    
                    # Calculate priority score
                    priority_score = scheduler.calculate_priority(detections, lane_number)
                    
                    # Add to results (without any image paths)
                    results.append({
                        'lane_number': lane_number,
                        'priority_score': priority_score,
                        'counts': detections['counts'],
                        'has_emergency': detections['has_emergency'],
                        'has_jaywalkers': detections['has_jaywalkers']
                    })
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        
        # Determine which lane gets the green light
        green_lane = scheduler.select_green_light(results)
        
        # Render the results page directly instead of storing in session
        return render_template(
            'results_no_images.html',
            results=results,
            green_lane=green_lane
        )
    
    except Exception as e:
        logging.error(f"Error processing images: {e}")
        flash(f"Error analyzing traffic: {str(e)}", 'danger')
        return redirect(url_for('index'))

@app.route('/simulator')
def simulator():
    """Render the traffic simulator page"""
    return render_template('simulator.html')

@app.route('/run-simulation', methods=['POST'])
def run_simulation():
    """Process simulation data and show results without storing data"""
    try:
        # Get the number of lanes
        lane_count = int(request.form.get('lane_count', 2))
        if lane_count < 2 or lane_count > 4:
            flash('Invalid number of lanes', 'danger')
            return redirect(url_for('simulator'))
        
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
        
        # Render the simulation results directly
        return render_template(
            'simulation_results.html',
            results=results,
            green_lane=green_lane
        )
    
    except Exception as e:
        logging.error(f"Error processing simulation: {e}")
        flash(f"Error running simulation: {str(e)}", 'danger')
        return redirect(url_for('simulator'))

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

@app.route('/clear_session')
def clear_session():
    """Redirect to index - no data to clear"""
    flash('No data stored - nothing to clear', 'info')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)