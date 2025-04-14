from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class TrafficEvent(db.Model):
    """Records traffic analysis events with timestamp and results"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    event_type = db.Column(db.String(50), nullable=False)  # 'upload' or 'simulation'
    
    # Store the number of lanes analyzed
    lane_count = db.Column(db.Integer, nullable=False)
    
    # Selected green light lane
    green_lane = db.Column(db.Integer, nullable=False)
    
    # Store JSON statistics for this event (not the images themselves)
    stats = db.Column(JSON, nullable=False)
    
    # Relationships
    lanes = db.relationship('LaneData', backref='event', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TrafficEvent {self.id} ({self.event_type}) at {self.timestamp}>"


class LaneData(db.Model):
    """Stores detection data for each lane in a traffic event"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('traffic_event.id', ondelete='CASCADE'), nullable=False)
    lane_number = db.Column(db.Integer, nullable=False)
    
    # Vehicle counts
    vehicle_count = db.Column(db.Integer, default=0)
    pedestrian_count = db.Column(db.Integer, default=0)
    jaywalker_count = db.Column(db.Integer, default=0)
    emergency_vehicle_count = db.Column(db.Integer, default=0)
    
    # Priority calculation
    priority_score = db.Column(db.Float, nullable=False)
    has_emergency = db.Column(db.Boolean, default=False)
    has_jaywalkers = db.Column(db.Boolean, default=False)
    
    # Store detailed breakdown of priority calculation
    score_breakdown = db.Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<LaneData {self.id} (Lane {self.lane_number}) Score: {self.priority_score}>"