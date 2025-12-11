import google.auth
from google.auth.transport.requests import Request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    credentials, project_id = google.auth.default()
    if not credentials.valid:
        credentials.refresh(Request())
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or project_id
    region = os.getenv("REGION", "europe-west4")

    print(f"Testing Project: {project_id} in {region}")
    
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
        "x-goog-user-project": project_id
    }

    # Test Listing Publishers
    url = "https://aiplatform.googleapis.com/v1beta1/publishers"
    print(f"\nGET {url}")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            publishers = data.get("publishers", [])
            print(f"Found {len(publishers)} publishers.")
            for p in publishers[:5]:
                print(f" - {p.get('name')}")
        else:
            print(f"Error: {response.text[:100]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_connection()
