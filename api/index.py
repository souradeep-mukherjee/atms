import os
import logging
import json
from urllib.parse import parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple response function for Vercel serverless
def http_response(status_code, body, headers=None):
    if headers is None:
        headers = {'Content-Type': 'application/json'}
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

# Entry point for Vercel serverless function
def handler(request, context):
    try:
        logger.info("Received request in Vercel serverless function")
        
        # For a full-fledged app, we would initialize Flask here 
        # and use it to handle requests, but this requires more setup
        # Since we're having issues with PostgreSQL in serverless,
        # let's use a simpler approach first
        
        # Return a simple response for now
        return http_response(200, {
            'message': 'Traffic Control System API is running',
            'version': '1.0.0',
            'env': os.environ.get('VERCEL_ENV', 'development'),
            'region': os.environ.get('VERCEL_REGION', 'unknown')
        })
    except Exception as e:
        logger.error(f"Error in serverless function: {str(e)}")
        return http_response(500, {'error': f'Internal server error: {str(e)}'})