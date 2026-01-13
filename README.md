# Vertex AI Model Policy Enumeration Gremlin

![Policy Gremlin](img/PolicyGremlin.png)

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

### Global Endpoint vs Regional Endpoints

**Important Discovery:** Vertex AI has two types of endpoints:

1.  **Regional Endpoints** (e.g., `us-central1-aiplatform.googleapis.com`, `europe-west4-aiplatform.googleapis.com`)
    *   Most models are deployed to specific regions
    *   This script verifies availability against these endpoints
    *   Suitable for data residency requirements

2.  **Global Endpoint** (`aiplatform.googleapis.com`)
    *   Routes requests dynamically to available regions
    *   Higher availability, lower rate limits
    *   **Gemini 3 models are ONLY available here** (as of January 2026)
    *   Some preview models don't appear in list APIs but can be accessed directly

**Gemini 3 Availability:** The latest Gemini 3 models (`gemini-3-pro-preview`, `gemini-3-flash-preview`) are currently exclusive to the global endpoint and not yet deployed to regional endpoints.

## Prerequisites

- Python 3.9+
- A Google Cloud Project with the **Vertex AI API** enabled (`aiplatform.googleapis.com`).
- **Network access to `us-central1`**: The script performs initial model discovery from the `us-central1-aiplatform.googleapis.com` endpoint. Ensure your environment has outbound network access to this region.
- [uv](https://github.com/astral-sh/uv) (Recommended) OR standard pip.

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/j3brns/vertex-maas-availability-by-region.git
    cd vertex-maas-availability-by-region
    ```

2.  **Authentication (Critical):**
    You must authenticate with Google Cloud before running the script. The script uses Application Default Credentials (ADC).
    ```bash
    gcloud auth application-default login
    ```
    *Alternatively, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of a Service Account JSON key.*

3.  **Configuration (Optional):**
    You can use a `.env` file to set default values for your project and region.
    ```bash
    cp .env.template .env
    # Edit .env with your specific values
    ```

## Usage

### Using `uv` (Recommended)
`uv` will automatically handle dependency installation using the inline metadata in the script.

```bash
# List models available in europe-west4 for ALL popular publishers
uv run enumerate.py --region europe-west4 --publisher all

# List only specific publishers
uv run enumerate.py --region europe-west4 --publisher google,anthropic,meta

# IMPORTANT: The script currently only supports regional endpoints
# To query the global endpoint (for Gemini 3 models), you'll need to query it separately
# The global endpoint uses aiplatform.googleapis.com (not global-aiplatform.googleapis.com)
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
| `--publisher` | N/A                    | The model publisher(s). Can be `all`, a single ID (e.g., `anthropic`), or a comma-separated list (`google,meta`). Default: `google`. <br>Supported for `all`: `google`, `anthropic`, `meta`, `mistralai`, `cohere`, `ai21`. |
| `--json`      | N/A                    | Output the results as a JSON array instead of a plain text list. Useful for automation and CI/CD pipelines. |

*Note: CLI arguments take precedence over environment variables.*

## Output

The script separates log messages from the final output:
- **Stderr:** Progress bars, debug logs, and warnings.
- **Stdout:** The clean, final list (or JSON).

This allows you to pipe the output directly to files or variables.

**Standard Output (Default):**
```text
# Models available in europe-west4 for publisher 'google'
- publishers/google/models/gemini-1.5-pro-002:predict
- publishers/google/models/gemini-2.0-flash-001:predict
...
```

**JSON Output (`--json`):**
```json
[
  "publishers/google/models/gemini-1.5-pro-002:predict",
  "publishers/google/models/gemini-2.0-flash-001:predict",
  ...
]
```

### Global Endpoint Models

For models available on the global endpoint (including Gemini 3), a separate JSON file is provided in the `output/` directory: `output/vertex-google-models_global_13-01-25.json`

**Key differences:**
- Global endpoint includes Gemini 3 preview models (`gemini-3-pro-preview`, `gemini-3-flash-preview`)
- Global endpoint only includes ~12 Gemini models (curated list)
- Regional endpoints include 14-122+ models depending on the region
- Some models on global endpoint don't appear in list APIs and must be accessed directly

**Sample output files:**
- `output/vertex-google-models_global_13-01-25.json` - Global endpoint (12 models)
- `output/vertex-google-models_us-central1_13-01-25.json` - Master catalog (122 models)
- `output/vertex-google-models_europe-west4_13-01-25.json` - Europe West 4 (20 models)
- `output/vertex-google-models_europe-west2_13-01-25.json` - Europe West 2 (14 models)

**Disclaimer:** This Terraform integration is provided as a Proof of Concept (PoC) and is currently **untested**. It demonstrates how to leverage the script's output but requires thorough testing and validation in your specific environment before use in production.

This repository includes a Terraform module in the `terraform/` directory to enforce the `constraints/aiplatform.restrictedModelUsage` organization policy using the discovered list.

### Workflow

1.  **Generate the Allowed List:**
    Use the `--json` flag to capture the list of available models as a JSON array.
    ```bash
    # Capture the JSON output into a variable (Bash/Zsh)
    export TF_VAR_allowed_models=$(uv run enumerate.py --region europe-west4 --json)

    # Or save to a file in the output directory
    uv run enumerate.py --region europe-west4 --json > output/allowed_models.json
    ```

2.  **Apply with Terraform:**
    Navigate to the `terraform/` directory and apply the configuration.
    ```bash
    cd terraform
    export TF_VAR_project_id="your-project-id"
    
    terraform init
    terraform apply
    ```

    *Terraform will read the `TF_VAR_allowed_models` environment variable and enforce that ONLY the discovered models are allowed in your project.*

## Performance Note
The "Verification" phase involves sending ~120 parallel HTTP requests to the regional API. This typically takes **5-15 seconds** depending on your network latency. You may see warnings about "Connection pool is full"; these are normal and can be ignored.

## Known Limitations

### Global Endpoint Not Fully Supported
The script currently only supports regional endpoints (e.g., `us-central1-aiplatform.googleapis.com`). The global endpoint (`aiplatform.googleapis.com`) uses a different URL format and is not handled by the `--region` parameter.

### Gemini 3 Preview Models
Gemini 3 models (`gemini-3-pro-preview`, `gemini-3-flash-preview`) exist on the global endpoint but:
1. They don't appear in the `list_publisher_models()` API response
2. They can only be discovered by directly querying their resource names via `get_publisher_model()`
3. They are not yet deployed to regional endpoints (as of January 2026)

This is why the global endpoint file (`vertex-google-models_global_13-01-25.json`) was created manually through direct verification rather than automated discovery.