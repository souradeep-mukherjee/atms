from flask import Flask, jsonify, request, render_template
import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev_key')

@app.route('/', methods=['GET'])
def home():
    """Render the landing page or API info"""
    # We'll render a simple page for now
    return jsonify({
        'api': 'Automated Traffic Control System',
        'version': '1.0',
        'endpoints': [
            {
                'path': '/',
                'method': 'GET',
                'description': 'API information'
            },
            {
                'path': '/status',
                'method': 'GET',
                'description': 'Server status and environment info'
            }
        ],
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/status', methods=['GET'])
def status():
    """Return server status and environment information"""
    return jsonify({
        'status': 'online',
        'environment': os.environ.get('VERCEL_ENV', 'development'),
        'region': os.environ.get('VERCEL_REGION', 'unknown'),
        'timestamp': datetime.utcnow().isoformat(),
        'database': {
            'connected': False,
            'message': 'Database connection pending implementation'
        }
    })

# Vercel serverless handler
def handler(request, context):
    """Handle requests in Vercel serverless environment"""
    # Convert Vercel's request format to what Flask expects
    with app.test_request_context(
        path=request.get('path', '/'),
        method=request.get('method', 'GET')
    ):
        try:
            # Dispatch the request to Flask
            response = app.full_dispatch_request()
            return {
                'statusCode': response.status_code,
                'headers': dict(response.headers),
                'body': response.get_data(as_text=True)
            }
        except Exception as e:
            logger.error(f"Error in serverless function: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Internal server error: {str(e)}'})
            }