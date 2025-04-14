import os
import logging
import random
from datetime import datetime

class YOLODetector:
    """Simplified simulated version of a YOLO detector for demonstration purposes."""
    
    def __init__(self, model_name='yolov8n.pt'):
        """Initialize the simulated detector.
        
        Args:
            model_name (str): Name of the YOLOv8 model (not used in simulation).
        """
        try:
            logging.info(f"Initializing simplified detector (for demo only)")
            
            # Define classes of interest
            self.vehicle_classes = ['car', 'bus', 'truck', 'motorcycle', 'bicycle']
            self.emergency_classes = ['ambulance', 'fire truck', 'police car', 'police']
            self.person_class = 'person'
            
        except Exception as e:
            logging.error(f"Error initializing simulated detector: {e}")
            raise
    
    def detect(self, image_path):
        """Simulate object detection on the image.
        
        Args:
            image_path (str): Path to the image file.
            
        Returns:
            dict: Dictionary containing simulated detection results.
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # We're not actually doing any image processing,
            # just using the file path to generate a deterministic seed
            
            # Get file creation time to use as part of seed
            image_stat = os.stat(image_path)
            
            # Create a seed based on filename hash and file size
            image_hash = hash(image_path) % 10000
            file_size = image_stat.st_size
            
            rand_seed = (image_hash + file_size) % 10000
            random.seed(rand_seed)
            
            # Generate counts based on seed
            counts = {
                'vehicles': random.randint(1, 15),
                'pedestrians': random.randint(0, 8),
                'emergency_vehicles': 1 if random.random() < 0.2 else 0,  # 20% chance
                'jaywalkers': 0
            }
            
            # Add some jaywalkers (a percentage of pedestrians)
            if counts['pedestrians'] > 0:
                counts['jaywalkers'] = min(random.randint(0, counts['pedestrians']), 3)
            
            # Initialize detection lists - with basic detection info only
            vehicles = []
            pedestrians = []
            emergency_vehicles = []
            jaywalkers = []
            
            # We'll simulate dimensions of a 640x480 image
            w, h = 640, 480
            
            # Generate vehicle detections (simplified - just for demo)
            for i in range(counts['vehicles']):
                # Random box dimensions
                x1 = random.randint(10, w - 100)
                y1 = random.randint(10, h - 100)
                box_w = random.randint(50, 150)
                box_h = random.randint(50, 100)
                x2 = min(x1 + box_w, w - 10)
                y2 = min(y1 + box_h, h - 10)
                
                confidence = round(random.uniform(0.6, 0.95), 2)
                class_name = random.choice(self.vehicle_classes)
                
                vehicles.append({
                    'box': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'class': class_name
                })
            
            # Generate emergency vehicle detections
            if counts['emergency_vehicles'] > 0:
                # Put emergency vehicle in a random spot
                x1 = random.randint(10, w - 150)
                y1 = random.randint(10, h - 150)
                box_w = random.randint(80, 200)
                box_h = random.randint(80, 120)
                x2 = min(x1 + box_w, w - 10)
                y2 = min(y1 + box_h, h - 10)
                
                confidence = round(random.uniform(0.75, 0.95), 2)
                
                emergency_vehicles.append({
                    'box': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'class': 'emergency_vehicle'
                })
                
                # Also add to vehicles
                vehicles.append({
                    'box': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'class': 'emergency_vehicle'
                })
            
            # Generate pedestrian detections
            for i in range(counts['pedestrians']):
                # Random box dimensions
                x1 = random.randint(10, w - 80)
                y1 = random.randint(10, h - 150)
                box_w = random.randint(30, 70)
                box_h = random.randint(70, 150)
                x2 = min(x1 + box_w, w - 10)
                y2 = min(y1 + box_h, h - 10)
                
                confidence = round(random.uniform(0.6, 0.95), 2)
                
                pedestrians.append({
                    'box': (x1, y1, x2, y2),
                    'confidence': confidence,
                    'class': 'person'
                })
            
            # Generate jaywalker detections
            if pedestrians and counts['jaywalkers'] > 0:
                jaywalker_indices = random.sample(range(len(pedestrians)), min(counts['jaywalkers'], len(pedestrians)))
                for idx in jaywalker_indices:
                    jaywalkers.append({
                        'box': pedestrians[idx]['box'],
                        'confidence': pedestrians[idx]['confidence'],
                        'class': 'jaywalker'
                    })
            
            # Prepare the final detection results
            detection_results = {
                'counts': counts,
                'vehicles': vehicles,
                'pedestrians': pedestrians,
                'emergency_vehicles': emergency_vehicles,
                'jaywalkers': jaywalkers,
                'has_emergency': counts['emergency_vehicles'] > 0,
                'has_jaywalkers': counts['jaywalkers'] > 0,
                'image_path': image_path,
                'image_shape': (h, w, 3)  # Just for compatibility
            }
            
            return detection_results
            
        except Exception as e:
            logging.error(f"Error performing detection: {e}")
            raise
    
    def _check_emergency_vehicle(self, image, box):
        """Simulate checking if vehicle is an emergency vehicle.
        This is a placeholder for the real implementation.
        
        Args:
            image: The image data (not used in simulation).
            box (tuple): Bounding box coordinates (x1, y1, x2, y2).
            
        Returns:
            bool: True if the vehicle is an emergency vehicle.
        """
        # For simulation, this is handled in the detect method
        return False
    
    def _check_jaywalking(self, image, box):
        """Simulate checking if pedestrian is jaywalking.
        This is a placeholder for the real implementation.
        
        Args:
            image: The image data (not used in simulation).
            box (tuple): Bounding box coordinates (x1, y1, x2, y2).
            
        Returns:
            bool: True if the pedestrian is jaywalking.
        """
        # For simulation, this is handled in the detect method
        return False
