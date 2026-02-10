import sys
import os

# Set environment variables manually for the test
os.environ["FIREBASE_MONGO_URI"] = "mongodb://admin:x3SA47EI2rgQxhtrd0HaQb1xO5pX_grNwtLRHVFPrDWLjxn_@2a098228-7f53-42ac-b724-49d6c41b5a87.nam5.firestore.goog:443/digistudio-core?loadBalanced=true&tls=true&authMechanism=SCRAM-SHA-256&retryWrites=false"
os.environ["FIREBASE_DB_NAME"] = "digistudio-core"

# Add the project root to sys.path if necessary
# In this environment, it seems digistudio is in site-packages or the path is already set.

from digistudio.integrations.firebase import get_firebase_client

def test_helpers():
    client = get_firebase_client()
    test_col = "temp_test_collection"
    
    print(f"--- Testing Firestore Collection Management ---")
    
    # 1. Existence check (should be False unless it already has data)
    exists = client.collection_exists(test_col)
    print(f"Initial check - '{test_col}' exists: {exists}")
    
    # 2. Create collection (No-op in Firestore until data is added)
    print(f"Creating collection (no-op): {test_col}")
    client.create_collection(test_col)
    
    # 3. Add data so it actually 'exists'
    print(f"Inserting dummy data to make it 'exist'...")
    client.insert_one(test_col, {"test": True})
    
    # 4. Check again (should be True now)
    exists = client.collection_exists(test_col)
    print(f"Post-insert check - '{test_col}' exists: {exists}")
    
    # 5. List collections
    cols = client.list_collections()
    print(f"All collections: {cols}")
    
    # 6. Delete collection (Clears all data)
    print(f"Deleting (clearing) collection: {test_col}")
    client.delete_collection(test_col)
    
    # 7. Final check
    # Note: In some systems, even after deleting all docs, the name might persist for a short while
    exists = client.collection_exists(test_col)
    print(f"Final check - '{test_col}' exists: {exists}")
    
    if not exists:
        print("\nSUCCESS: All helpers verified.")
    else:
        # Check if it's empty even if name is still listed
        count = len(client.find(test_col))
        print(f"Collection count: {count}")
        if count == 0:
            print("\nSUCCESS: Collection cleared (Firestore collection names may persist).")
        else:
            print("\nFAILURE: Collection still has data.")

if __name__ == "__main__":
    test_helpers()
