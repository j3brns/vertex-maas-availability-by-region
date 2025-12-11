# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "google-cloud-aiplatform",
#     "python-dotenv",
# ]
# ///
"""
Vertex AI Model Enumerator for Organization Policies.

This script generates a list of Google-published Vertex AI models available in a specific
Google Cloud region. This list is formatted for direct use in Google Cloud Organization
Policies (e.g., restricting which models can be used in a project).

Problem Solved:
    The Vertex AI API does not provide a single endpoint to "list all models available in Region X".
    - The Global endpoint often returns a curated/limited list of "featured" models.
    - Regional endpoints often return 404s for the discovery (listing) API.
    - The Master Catalog (us-central1) lists all models but doesn't guarantee they work in your region.

Solution Strategy:
    1. Discovery: Fetches the complete catalog of models from the `us-central1` endpoint,
       which serves as the "Master Catalog" for Model Garden.
    2. Verification: Validates each model's availability in the target region (e.g., europe-west4)
       by attempting to retrieve the specific model resource from that region's API endpoint.
       This "Ping Test" filters out models that are defined globally but not deployed regionally.

Usage:
    uv run enumerate.py --region europe-west4 --project my-project-id
"""

import os
import sys
import argparse
import logging
from typing import Optional, List, Any
import concurrent.futures

from dotenv import load_dotenv
from google.cloud import aiplatform_v1beta1
from google.api_core import exceptions

# Configure logging to stderr so stdout remains clean for piping output to files.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

def get_project_id(arg_project: Optional[str]) -> str:
    """
    Determines the Google Cloud Project ID.
    
    Priority:
    1. CLI Argument (--project)
    2. Environment Variable (GOOGLE_CLOUD_PROJECT)
    
    Args:
        arg_project: Project ID passed via command line.
        
    Returns:
        str: The resolved Project ID.
        
    Raises:
        SystemExit: If no project ID can be found.
    """
    if arg_project:
        return arg_project
    
    env_project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if env_project:
        return env_project
    
    logger.error("Could not determine Project ID. Set GOOGLE_CLOUD_PROJECT env var or use --project.")
    sys.exit(1)

def check_model_availability(client: aiplatform_v1beta1.ModelGardenServiceClient, model_name: str) -> bool:
    """
    Verifies if a specific model resource exists in the region connected to by the client.
    
    This acts as a "Ping Test". If the API returns the model details, it is available.
    If it returns a 404 or other error, it is considered unavailable in this region.

    Args:
        client: An initialized ModelGardenServiceClient pointing to the target regional endpoint.
        model_name: The full resource name of the model (e.g., "publishers/google/models/gemini-pro").

    Returns:
        bool: True if available, False otherwise.
    """
    try:
        client.get_publisher_model(name=model_name)
        return True
    except exceptions.NotFound:
        # 404: The model is not available in this region.
        return False
    except Exception:
        # Any other error (e.g., 403 Permission, 500 Server) also implies we can't use it.
        return False

def fetch_models(project_id: str, region: str, publisher: str = "google") -> List[Any]:
    """
    Fetches the full catalog of models and filters them by regional availability.

    Args:
        project_id: The Google Cloud Project ID.
        region: The target region to check availability for (e.g., "europe-west4").
        publisher: The model publisher to filter by (default: "google").

    Returns:
        List[Any]: A list of available PublisherModel objects.
    """
    # 1. Discovery: Get ALL models from the Master Catalog (us-central1)
    # The 'global' endpoint (aiplatform.googleapis.com) often returns a filtered list,
    # so we use us-central1 for the most complete discovery.
    discovery_endpoint = "us-central1-aiplatform.googleapis.com"
    logger.info(f"Discovery: Fetching full catalog from {discovery_endpoint}...")
    
    discovery_client = aiplatform_v1beta1.ModelGardenServiceClient(
        client_options={"api_endpoint": discovery_endpoint}
    )
    
    parent = f"publishers/{publisher}"
    try:
        # List all models for the publisher
        response = discovery_client.list_publisher_models(parent=parent)
        all_models = list(response)
        logger.info(f"Discovery: Found {len(all_models)} models in Master Catalog.")
    except Exception as e:
        logger.error(f"Failed to discover models: {e}")
        sys.exit(1)

    # 2. Filtering: If target region is NOT us-central1, verify availability
    # We assume if the user asks for us-central1, the discovery list is sufficient.
    if region == "us-central1":
        logger.info("Region is us-central1; returning full discovery catalog.")
        return all_models
    
    logger.info(f"Filtering: Verifying availability in {region} for {len(all_models)} models...")
    
    # Client for the target region to perform the "Ping Test"
    region_client = aiplatform_v1beta1.ModelGardenServiceClient(
        client_options={"api_endpoint": f"{region}-aiplatform.googleapis.com"}
    )

    available_models = []
    
    # Use ThreadPool to check in parallel as these are simple I/O bound HTTP GETs.
    # A high worker count (50) significantly speeds up checking 100+ models.
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        # Submit all checks
        future_to_model = {
            executor.submit(check_model_availability, region_client, model.name): model 
            for model in all_models
        }
        
        count = 0
        total = len(all_models)
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_model):
            model = future_to_model[future]
            is_available = future.result()
            count += 1
            
            # Log progress every 20 models
            if count % 20 == 0:
                logger.info(f"Checked {count}/{total} models...")
            
            if is_available:
                available_models.append(model)

    return available_models

def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Enumerate Google Cloud Vertex AI Models for Organization Policies."
    )
    parser.add_argument("--project", help="Google Cloud Project ID")
    parser.add_argument("--region", help="GCP Region (e.g., europe-west4)")
    parser.add_argument("--publisher", default="google", help="Model Publisher (default: google)")
    
    args = parser.parse_args()

    project_id = get_project_id(args.project)
    
    # Region is critical for the filtering logic
    region = args.region or os.getenv("REGION") or "us-central1"

    # Execute
    models = fetch_models(project_id, region, args.publisher)
    
    if models:
        logger.info(f"Successfully retrieved {len(models)} models available in {region}.")
        
        # Output strictly the policy lines to stdout for easy piping
        print(f"# Models available in {region} for publisher '{args.publisher}'")
        for model in models:
            # model.name is usually "publishers/google/models/..."
            print(f"- {model.name}:predict")
    else:
        logger.warning(f"No models found available in {region}.")

if __name__ == "__main__":
    main()