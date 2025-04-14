import os
import logging
import tempfile
import json
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, TrafficEvent, LaneData

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize modules (these will be imported from app.py)
# Let's create simplified versions of these for Vercel deployment
class YOLODetector:
    """Simplified simulated version of a YOLO detector for demonstration purposes."""
    
    def __init__(self, model_name='yolov8n.pt'):
        """Initialize the simulated detector."""
        logger.info("Initializing simplified detector (for demo only)")
        
    def detect(self, image_path):
        """Simulate object detection on the image."""
        # For simplicity, return simulated data
        return {
            'counts': {
                'vehicles': 5,
                'pedestrians': 3,
                'jaywalkers': 1,
                'emergency_vehicles': 0
            },
            'has_emergency': False,
            'has_jaywalkers': True,
            'image_path': image_path,
            'image_shape': (480, 640, 3)
        }

class TrafficScheduler:
    """Class for traffic light scheduling based on detected objects."""
    
    def __init__(self):
        """Initialize the traffic scheduler."""
        pass
        
    def calculate_priority(self, detections, lane_id):
        """Calculate priority score for a lane based on detections."""
        # Get counts
        vehicle_count = detections['counts']['vehicles']
        pedestrian_count = detections['counts']['pedestrians']
        jaywalker_count = detections['counts']['jaywalkers']
        emergency_count = detections['counts'].get('emergency_vehicles', 0)
        
        # Calculate base scores
        vehicle_score = vehicle_count * 1.0
        pedestrian_score = pedestrian_count * 0.5
        jaywalker_score = jaywalker_count * -0.25
        emergency_score = 100.0 if emergency_count > 0 else 0.0
        
        # Calculate total score
        total_score = vehicle_score + pedestrian_score + jaywalker_score + emergency_score
        
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
                }
            }
        }
        
        return priority_score
    
    def select_green_light(self, lane_results):
        """Select which lane should get the green light."""
        # Find the lane with highest priority score
        highest_score = -1
        selected_lane = 1  # Default to lane 1
        
        for result in lane_results:
            score = result['priority_score']['total_score']
            if score > highest_score:
                highest_score = score
                selected_lane = result['lane_number']
                
        return selected_lane

class TrafficVisualizer:
    """Simplified class for simulating traffic analysis visualization."""
    
    def __init__(self):
        """Initialize the traffic visualizer."""
        pass
        
    def annotate_image(self, image_path, detections, output_path):
        """Create a simulated annotated image based on detections."""
        # In Vercel, we can't save files, so just return the path
        return output_path
        
    def create_traffic_light_image(self, is_green, output_path, size=(200, 400)):
        """Create a simulated traffic light image."""
        # In Vercel, we can't save files, so just return the path
        return output_path

# Initialize modules
detector = YOLODetector()
scheduler = TrafficScheduler()
visualizer = TrafficVisualizer()

def cleanup_temp_files(session_id):
    """Remove temporary files for this session"""
    # In serverless environment, files are automatically cleaned up
    pass

# Routes for web application
def index():
    """Render the main page"""
    return render_template('index.html')

def upload_images():
    """Handle image uploads and process them without storing images but record anonymized stats in DB"""
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
        
        # Store anonymized results in database
        try:
            # Create a new traffic event record
            traffic_event = TrafficEvent(
                event_type='upload',
                lane_count=len(results),
                green_lane=green_lane,
                stats={
                    'timestamp': os.path.basename(__file__),
                    'total_vehicles': sum(r['counts']['vehicles'] for r in results),
                    'total_pedestrians': sum(r['counts']['pedestrians'] for r in results),
                    'has_emergency': any(r['has_emergency'] for r in results),
                    'has_jaywalkers': any(r['has_jaywalkers'] for r in results),
                }
            )
            
            # Add the event to the database
            db.session.add(traffic_event)
            
            # Create lane data records for each lane
            for result in results:
                lane_data = LaneData(
                    event=traffic_event,
                    lane_number=result['lane_number'],
                    vehicle_count=result['counts']['vehicles'],
                    pedestrian_count=result['counts']['pedestrians'],
                    jaywalker_count=result['counts']['jaywalkers'],
                    emergency_vehicle_count=result['counts']['emergency_vehicles'] if 'emergency_vehicles' in result['counts'] else 0,
                    priority_score=result['priority_score']['total_score'],
                    has_emergency=result['has_emergency'],
                    has_jaywalkers=result['has_jaywalkers'],
                    score_breakdown=result['priority_score']
                )
                db.session.add(lane_data)
            
            # Commit the changes
            db.session.commit()
            logger.info(f"Saved traffic event to database, ID: {traffic_event.id}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error storing traffic analysis: {e}")
            # Continue even if database storage fails - we can still show results
        
        # Render the results page directly instead of storing in session
        return render_template(
            'results_no_images.html',
            results=results,
            green_lane=green_lane
        )
    
    except Exception as e:
        logger.error(f"Error processing images: {e}")
        flash(f"Error analyzing traffic: {str(e)}", 'danger')
        return redirect(url_for('index'))

def simulator():
    """Render the traffic simulator page"""
    return render_template('simulator.html')

def run_simulation():
    """Process simulation data and show results without storing images but with anonymous DB stats"""
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
                logger.error(f"Error processing lane {lane_number}: {e}")
                flash(f"Error with lane {lane_number} data: {str(e)}", 'danger')
                return redirect(url_for('simulator'))
        
        # Determine which lane gets the green light
        green_lane = scheduler.select_green_light(results)
        
        # Store simulation results in database
        try:
            # Create a new traffic event record
            traffic_event = TrafficEvent(
                event_type='simulation',
                lane_count=lane_count,
                green_lane=green_lane,
                stats={
                    'timestamp': os.path.basename(__file__),
                    'starvation_control': starvation_control,
                    'prev_green': prev_green,
                    'total_vehicles': sum(r['counts']['vehicles'] for r in results),
                    'total_pedestrians': sum(r['counts']['pedestrians'] for r in results),
                    'has_emergency': any(r['has_emergency'] for r in results),
                    'has_jaywalkers': any(r['has_jaywalkers'] for r in results),
                }
            )
            
            # Add the event to the database
            db.session.add(traffic_event)
            
            # Create lane data records for each lane
            for result in results:
                lane_data = LaneData(
                    event=traffic_event,
                    lane_number=result['lane_number'],
                    vehicle_count=result['counts']['vehicles'],
                    pedestrian_count=result['counts']['pedestrians'],
                    jaywalker_count=result['counts']['jaywalkers'],
                    emergency_vehicle_count=result['counts']['emergency_vehicles'] if 'emergency_vehicles' in result['counts'] else 0,
                    priority_score=result['priority_score']['total_score'],
                    has_emergency=result['has_emergency'],
                    has_jaywalkers=result['has_jaywalkers'],
                    score_breakdown=result['priority_score']
                )
                db.session.add(lane_data)
            
            # Commit the changes
            db.session.commit()
            logger.info(f"Saved simulation event to database, ID: {traffic_event.id}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error storing simulation: {e}")
            # Continue even if database storage fails - we can still show results
        
        # Render the simulation results directly
        return render_template(
            'simulation_results.html',
            results=results,
            green_lane=green_lane
        )
    
    except Exception as e:
        logger.error(f"Error processing simulation: {e}")
        flash(f"Error running simulation: {str(e)}", 'danger')
        return redirect(url_for('simulator'))

def stats():
    """Display statistics from the database"""
    try:
        # Get recent events
        events = TrafficEvent.query.order_by(TrafficEvent.timestamp.desc()).limit(10).all()
        
        # Extract simulation vs upload counts
        sim_count = TrafficEvent.query.filter_by(event_type='simulation').count()
        upload_count = TrafficEvent.query.filter_by(event_type='upload').count()
        
        # Get lane statistics
        lanes = LaneData.query.all()
        
        # Calculate aggregated statistics
        total_vehicles = sum(lane.vehicle_count for lane in lanes)
        total_pedestrians = sum(lane.pedestrian_count for lane in lanes)
        total_emergency = sum(lane.emergency_vehicle_count for lane in lanes)
        
        # Average vehicles per lane
        avg_vehicles = total_vehicles / len(lanes) if lanes else 0
        
        # Emergency vehicle percentage
        emergency_percentage = (sum(1 for lane in lanes if lane.has_emergency) / len(lanes) * 100) if lanes else 0
        
        # Get the percentage of times each lane was given priority
        green_counts = {}
        for i in range(1, 5):
            count = TrafficEvent.query.filter_by(green_lane=i).count()
            if count > 0:
                green_counts[i] = count
        
        total_decisions = sum(green_counts.values())
        green_percentages = {lane: (count / total_decisions * 100) if total_decisions > 0 else 0 
                             for lane, count in green_counts.items()}
                             
        return render_template(
            'stats.html',
            events=events,
            sim_count=sim_count,
            upload_count=upload_count,
            total_vehicles=total_vehicles,
            total_pedestrians=total_pedestrians,
            total_emergency=total_emergency,
            avg_vehicles=avg_vehicles,
            emergency_percentage=emergency_percentage,
            green_percentages=green_percentages
        )
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        flash(f"Error retrieving statistics: {str(e)}", 'danger')
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

def clear_session():
    """Clear the session data and remove temporary files"""
    flash('Session cleared', 'info')
    # No actual session data to clear, but redirect to index
    return redirect(url_for('index'))