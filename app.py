
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
# Load environment variables from .env file in the same directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

from helper import _process_single_user, run_pipeline, get_cached_jobs_from_firestore
from digistudio.processing.connections import get_user, get_all_users
from digistudio.integrations.firebase import get_firebase_client
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import concurrent.futures

# configure logging for the whole module/app
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)


LI_TOKEN = os.environ.get('LI_TOKEN')
JSESSION_ID = os.environ.get('JSESSION_ID')

# Critical Validation: Push back if the environment isn't ready
missing_vars = [var for var, val in {
    "LI_TOKEN": LI_TOKEN, 
    "JSESSION_ID": JSESSION_ID, 
}.items() if not val]

if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

client = get_firebase_client()

app = Flask(__name__)
CORS(app)

@app.route('/')
def health_check():
    
    return {"status": "healthy", "message": "Crawler service is running"}, 200

@app.route('/api/jobs', methods=['POST'])
def jobs_endpoint():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    li_token = data.get('li_token')
    j_session_id = data.get('j_session_id')
    
    if not li_token or not j_session_id:
        return jsonify({"error": "li_token and j_session_id are required"}), 400
    
    # Get user to extract URN
    user = get_user(li_token, j_session_id)
    urn = user['urn']
    # Check cache: if valid results exist within 7 days, return them
    cached_result = get_cached_jobs_from_firestore(urn)
    if cached_result is not None:
        return jsonify({"status": "cached", "result": cached_result}), 200
    
    # Cache expired or not found → run pipeline synchronously
    try:
        logger.info("Starting pipeline for request")
        result = run_pipeline(user)
        logger.info("Pipeline completed successfully")
        return jsonify({"status": "completed", "result": result}), 200
    except Exception as e:
        logger.exception("Pipeline failed")
        return jsonify({"error": f"Pipeline failed: {str(e)}"}), 500


@app.route('/api/all_users', methods=['POST'])
def all_users_endpoint():
    """Process multiple users concurrently.

    Request JSON (optional):
      - max_workers: int (default 2)
      - max_users: int (limit number of users to process)
      - uri: str (override fetch URI)
    """
    data = request.get_json() or {}
    max_workers = int(data.get('max_workers', 2))
    max_users = data.get('max_users')
    uri = data.get('uri')
    li_token = data.get('li_token')
    j_session_id = data.get('j_session_id')

    # Use `get_all_users` from the job-connecting package instead of calling Firebase directly.
    try:

        if max_users:
            try:
                users = get_all_users(client, limit=int(max_users))
            except Exception:
                users = get_all_users(client)
        else:
            users = get_all_users(client)
        logger.info("Fetched %d users from Firestore for processing.", len(users))
        if not users:
            return jsonify({"status": "empty", "message": "No users found"}), 200
    except Exception as e:
        logger.exception("Failed to load users from Firestore")
        return jsonify({"error": f"Failed to load users: {e}"}), 500

    results = []
    # Use ThreadPoolExecutor for concurrent processing across users
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_process_single_user, u, uri, li_token, j_session_id): u.get('urn') for u in users}
        for fut in concurrent.futures.as_completed(futures):
            try:
                res = fut.result()
            except Exception as e:
                urn = futures.get(fut)
                logger.exception("Error processing user %s", urn)
                res = {"urn": urn, "status": "error", "error": str(e)}
            results.append(res)

    return jsonify({"status": "completed", "results": results}), 200

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Catch-all handler that logs exception and returns generic message."""
    logger.exception("Unhandled exception in Flask app")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
