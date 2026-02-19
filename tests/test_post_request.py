import requests
import json

# Define the API endpoint
url = "http://localhost:5000/api/jobs/"

# Define the payload data
payload = {
    "keywords": ["software engineer", "data scientist"],
    "min_salary": 75000,
    "experience": 2,
    "resume_path": "job-sourcing/other/text/resume.docx"
}

# Send POST request
try:
    response = requests.post(url, json=payload)
    
    # Print response details
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
except requests.exceptions.ConnectionError:
    print("Error: Could not connect to the server.")
    print("Make sure the Flask server is running by executing:")
    print("cd c:\\Users\\19178\\Desktop\\aiPlayground\\resume-job-sourcing && python job-sourcing/app.py")
except Exception as e:
    print(f"An error occurred: {e}")