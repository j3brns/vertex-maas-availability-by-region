# Vertex AI Model Enumerator

A robust utility to list Google Vertex AI models (Model Garden) available in specific regions, formatted for use in Google Cloud Organization Policies.

## The Problem

Discovering the correct list of models for a specific Google Cloud region (e.g., `europe-west4`) is surprisingly difficult due to API inconsistencies:

1.  **Fragmented Discovery:** The Global endpoint (`aiplatform.googleapis.com`) often returns a limited, curated list of "Featured" models, missing dozens of others (like PaLM, older Gemini versions, or specific specialized models).
2.  **Regional 404s:** Regional endpoints (e.g., `europe-west4-aiplatform...`) often return `404 Not Found` when attempting to *list* (discover) publisher models, even though those models *exist* and are usable in that region.
3.  **No Direct Filter:** There is no standard API parameter to "List all models available in Region X".

## The Solution

This script implements a **Two-Stage Discovery & Verification** strategy:

1.  **Global Discovery (The Menu):** It fetches the *complete* master catalog of ~120+ models from the `us-central1` endpoint (which hosts the canonical list for Model Garden).
2.  **Regional Verification (The Filter):** It performs a parallel "Ping Test" against your target region's API (e.g., `europe-west4`) for *every* model found in the catalog.
    *   If the region acknowledges the model (200 OK), it is added to the list.
    *   If the region denies the model (404 Not Found), it is filtered out.

This ensures you get a 100% accurate list of models that are *actually deployable/usable* in your target region.

## Prerequisites

- Python 3.9+
- A Google Cloud Project with the **Vertex AI API** enabled (`aiplatform.googleapis.com`).
- **Network access to `us-central1`**: The script performs initial model discovery from the `us-central1-aiplatform.googleapis.com` endpoint. Ensure your environment has outbound network access to this region.
- [uv](https://github.com/astral-sh/uv) (Recommended) OR standard pip.

## Setup

1.  **Authentication (Critical):**
    You must authenticate with Google Cloud before running the script. The script uses Application Default Credentials (ADC).
    ```bash
    gcloud auth application-default login
    ```
    *Alternatively, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of a Service Account JSON key.*

2.  **Configuration (Optional):**
    You can use a `.env` file to set default values for your project and region.
    ```bash
    cp .env.template .env
    # Edit .env with your specific values
    ```

## Usage

### Using `uv` (Recommended)
`uv` will automatically handle dependency installation using the inline metadata in the script.

```bash
# List models available in europe-west4
uv run enumerate.py --region europe-west4 --project your-project-id
```

### Using standard pip

1.  **Install Dependencies:**
    ```bash
    pip install google-cloud-aiplatform python-dotenv
    ```

2.  **Run the Script:**
    ```bash
    python enumerate.py --region europe-west4 --project your-project-id
    ```

## Arguments

| Argument      | Env Variable           | Description                                                                 |
| :---          | :---                   | :---                                                                        |
| `--region`    | `REGION`               | The Google Cloud region to check (e.g., `europe-west4`). Default: `us-central1`. |
| `--project`   | `GOOGLE_CLOUD_PROJECT` | Your Google Cloud Project ID.                                               |
| `--publisher` | N/A                    | The model publisher to list (default: `google`).                            |

*Note: CLI arguments take precedence over environment variables.*

## Output

The script separates log messages from the final output:
- **Stderr:** Progress bars, debug logs, and warnings (e.g., connection pool size).
- **Stdout:** The clean, final list of resource names.

This allows you to pipe the output directly to a file for your policy definition:

```bash
uv run enumerate.py --region europe-west4 > allowed_models.txt
```

**Example Output:**
```text
# Models available in europe-west4 for publisher 'google'
- publishers/google/models/gemini-1.5-pro-002:predict
- publishers/google/models/gemini-2.0-flash-001:predict
- publishers/google/models/text-bison:predict
...
```

## Performance Note
The "Verification" phase involves sending ~120 parallel HTTP requests to the regional API. This typically takes **5-15 seconds** depending on your network latency. You may see warnings about "Connection pool is full"; these are normal and can be ignored.