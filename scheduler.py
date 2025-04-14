import logging
import time

class TrafficScheduler:
    """Class for traffic light scheduling based on detected objects."""
    
    def __init__(self):
        """Initialize the traffic scheduler."""
        # Weights for scoring
        self.weights = {
            'vehicle': 1.0,        # Each vehicle counts as 1 point
            'pedestrian': 0.5,     # Each pedestrian counts as 0.5 points
            'emergency': 10.0,     # Emergency vehicles get high priority
            'jaywalker': -0.25,    # Jaywalkers reduce priority slightly
            'starvation': 0.5     # Per second of waiting
        }
        
        # Starvation control
        self.last_green = {}  # Dictionary to track when each lane last had a green light
        self.max_wait_time = 60  # Maximum wait time in seconds
    
    def calculate_priority(self, detections, lane_id):
        """Calculate priority score for a lane based on detections.
        
        Args:
            detections (dict): Detection results from YOLODetector.
            lane_id (int): Lane identifier.
            
        Returns:
            dict: Priority score and breakdown.
        """
        try:
            priority = 0.0
            breakdown = {}
            
            # Add score for vehicles
            vehicle_score = detections['counts']['vehicles'] * self.weights['vehicle']
            priority += vehicle_score
            breakdown['vehicles'] = {
                'count': detections['counts']['vehicles'],
                'weight': self.weights['vehicle'],
                'score': vehicle_score
            }
            
            # Add score for pedestrians
            pedestrian_score = detections['counts']['pedestrians'] * self.weights['pedestrian']
            priority += pedestrian_score
            breakdown['pedestrians'] = {
                'count': detections['counts']['pedestrians'],
                'weight': self.weights['pedestrian'],
                'score': pedestrian_score
            }
            
            # Subtract for jaywalkers (slight penalty)
            jaywalker_score = detections['counts']['jaywalkers'] * self.weights['jaywalker']
            priority += jaywalker_score
            breakdown['jaywalkers'] = {
                'count': detections['counts']['jaywalkers'],
                'weight': self.weights['jaywalker'],
                'score': jaywalker_score
            }
            
            # Add high priority for emergency vehicles
            emergency_score = 0
            if detections['has_emergency']:
                emergency_score = self.weights['emergency']
                priority += emergency_score
            
            breakdown['emergency_vehicles'] = {
                'count': detections['counts']['emergency_vehicles'],
                'weight': self.weights['emergency'],
                'score': emergency_score
            }
            
            # Add starvation control bonus
            starvation_score = 0
            current_time = time.time()
            if lane_id in self.last_green:
                wait_time = current_time - self.last_green[lane_id]
                # Calculate bonus - the longer the wait, the higher the bonus
                if wait_time > 20:  # Only start adding bonus after 20 seconds
                    wait_factor = min(wait_time / self.max_wait_time, 1.0)  # Cap at max_wait_time
                    starvation_score = wait_factor * self.weights['starvation'] * 100
                    priority += starvation_score
            
            breakdown['starvation_control'] = {
                'wait_time': current_time - self.last_green.get(lane_id, current_time) if lane_id in self.last_green else 0,
                'score': starvation_score
            }
            
            # Calculate total score
            total_score = priority
            
            return {
                'lane_id': lane_id,
                'total_score': total_score,
                'breakdown': breakdown,
                'has_emergency': detections['has_emergency']
            }
            
        except Exception as e:
            logging.error(f"Error calculating priority score: {e}")
            raise
    
    def select_green_light(self, lane_results):
        """Select which lane should get the green light.
        
        Args:
            lane_results (list): List of lane priority results.
            
        Returns:
            int: Lane ID that should get the green light.
        """
        try:
            # First check for emergency vehicles
            emergency_lanes = [
                lane['lane_number'] for lane in lane_results 
                if lane.get('has_emergency', False)
            ]
            
            if emergency_lanes:
                # If multiple lanes have emergency vehicles, pick the one with highest priority
                if len(emergency_lanes) > 1:
                    max_priority = 0
                    selected_lane = emergency_lanes[0]
                    
                    for lane in lane_results:
                        if lane['lane_number'] in emergency_lanes and lane['priority_score']['total_score'] > max_priority:
                            max_priority = lane['priority_score']['total_score']
                            selected_lane = lane['lane_number']
                    
                    chosen_lane = selected_lane
                else:
                    chosen_lane = emergency_lanes[0]
            else:
                # No emergency vehicles, pick lane with highest priority score
                max_priority = -1
                chosen_lane = 1  # Default to first lane
                
                for lane in lane_results:
                    if lane['priority_score']['total_score'] > max_priority:
                        max_priority = lane['priority_score']['total_score']
                        chosen_lane = lane['lane_number']
            
            # Update last green time for the chosen lane
            current_time = time.time()
            self.last_green[chosen_lane] = current_time
            
            return chosen_lane
            
        except Exception as e:
            logging.error(f"Error selecting green light lane: {e}")
            raise
