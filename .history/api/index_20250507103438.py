from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Add the parent directory to the path to import scraper.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import the scraper module
import scraper

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests - provide API information"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_headers('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "message": "City of London Planning Scraper API",
            "endpoints": {
                "/api": "GET - This information",
                "/api/scrape": "POST - Run scraper with specific parameters"
            },
            "usage": "Send a POST request to /api/scrape with start_month, end_month and/or selected_wards parameters"
        }
        
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        """Handle POST requests - run the scraper"""
        if self.path == '/api/scrape':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                start_month = data.get('start_month')
                end_month = data.get('end_month')
                selected_wards = data.get('selected_wards', [])
                format_type = data.get('format', 'json')
                
                # Run the scraper with the provided parameters
                results = scraper.scrape_data(
                    start_month=start_month,
                    end_month=end_month,
                    selected_wards=selected_wards
                )
                
                # Handle response based on requested format
                if format_type == 'csv':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/csv')
                    self.send_header('Content-Disposition', 'attachment; filename="cityoflondon_data.csv"')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(results['csv'].encode())
                else:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {
                        "data": results['data'],
                        "count": results['count'],
                        "months": results['months'],
                        "wards": results['wards']
                    }
                    self.wfile.write(json.dumps(response).encode())
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                response = {"error": str(e)}
                self.wfile.write(json.dumps(response).encode())
                
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {"error": "Endpoint not found"}
            self.wfile.write(json.dumps(response).encode()) 