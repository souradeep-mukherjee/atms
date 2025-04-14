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
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
if not app.config['SECRET_KEY']:
    if os.environ.get('VERCEL_ENV') == 'production':
        raise ValueError("FLASK_SECRET_KEY must be set in production")
    app.config['SECRET_KEY'] = 'dev-key-warning'  # Clearly indicate this is not for production

@app.route('/', methods=['GET'])
def home():
    """Render the landing page or API info"""
    logger.info("Home endpoint accessed")
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
    logger.info("Status endpoint accessed")
    return jsonify({
        'status': 'online',
        'environment': os.environ.get('VERCEL_ENV', 'development'),
        'region': os.environ.get('VERCEL_REGION', 'unknown'),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Vercel serverless handler
def handler(req, context):
    """Handle requests in Vercel serverless environment"""
    try:
        with app.test_request_context(
            path=req.get('path', '/'),
            method=req.get('httpMethod', 'GET'),
            headers=req.get('headers', {}),
            query_string=req.get('queryStringParameters', {}),
            data=req.get('body', '')
        ):
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
            'body': json.dumps({'error': 'Internal server error'})
        }

if __name__ == '__main__':
    app.run(debug=True)