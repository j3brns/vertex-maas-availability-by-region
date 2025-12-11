# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "google-cloud-aiplatform",
#     "python-dotenv",
#     "protobuf"
# ]
# ///
from google.cloud import aiplatform_v1beta1
from google.protobuf.json_format import MessageToDict
import json
import sys

def inspect_model():
    # Test checking availability in europe-west4
    region = "europe-west4"
    client_options = {"api_endpoint": f"{region}-aiplatform.googleapis.com"}
    client = aiplatform_v1beta1.ModelGardenServiceClient(client_options=client_options)
    
    test_models = [
        "publishers/google/models/gemini-1.5-pro-002",
        "publishers/google/models/bert-base" 
    ]
    
    for model_name in test_models:
        print(f"Checking {model_name} in {region}...")
        try:
            model = client.get_publisher_model(name=model_name)
            print(f"SUCCESS: {model_name} is available in {region}")
        except Exception as e:
            print(f"FAILED: {model_name} is NOT available (or API error): {e}")

if __name__ == "__main__":
    inspect_model()