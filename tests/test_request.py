import requests
import json

# API Endpoint URL
url = 'http://localhost:5000/api/jobs'

# Payload data
data = {
    "keywords": ["Product Manager", "AI", "Machine Learning"],
    "min_salary": 120000,
    "experience": 3,
    "resume_path": "C:/Users/19178/Desktop/resume.docx" # Replace with valid path if testing locally
}

# Headers
headers = {
    'Content-Type': 'application/json'
}

try:
    print(f"Sending POST request to {url}...")
    print(f"Payload: {json.dumps(data, indent=2)}")
    
    response = requests.post(url, json=data, headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 202:
        print("\nSuccess! The pipeline has started in the background.")
    else:
        print("\nSomething went wrong.")

except requests.exceptions.ConnectionError:
    print("\nError: Could not connect to the server. Make sure 'python job-sourcing/app.py' is running.")
except Exception as e:
    print(f"\nAn error occurred: {e}")
