# Vertex AI Model Enumerator

A utility tool to robustly list Google Vertex AI models (Model Garden) available in specific regions, formatted for use in Google Cloud Organization Policies.

## The Problem

Discovering the correct list of models for a specific Google Cloud region (e.g., `europe-west4`) is surprisingly difficult due to API inconsistencies:

1.  **Fragmented Discovery:** The Global endpoint (`aiplatform.googleapis.com`) often returns a limited, curated list of "Featured" models (e.g., only the latest Gemini versions), missing dozens of others like PaLM or older Gemini versions.
2.  **Regional 404s:** Regional endpoints (e.g., `europe-west4-aiplatform...`) often return `404 Not Found` when attempting to *list* (discover) publisher models, even though those models *exist* in that region.
3.  **No Direct Filter:** There is no standard API parameter to "List all models available in Region X".

## The Solution

This script implements a **Two-Stage Discovery & Verification** strategy:

1.  **Global Discovery (The Menu):** It fetches the *complete* master catalog of ~120+ models from the `us-central1` endpoint (which hosts the canonical list for Model Garden).
2.  **Regional Verification (The Filter):** It performs a parallel "Ping Test" against your target region's API (e.g., `europe-west4`) for *every* model found in the catalog.
    *   If the region acknowledges the model (200 OK), it is added to the list.
    *   If the region denies the model (404 Not Found), it is filtered out.

This ensures you get a 100% accurate list of models that are *actually deployable/usable* in your target region.

## Requirements

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (Recommended) OR standard pip

## Usage

### Using `uv` (Recommended)

This script contains inline PEP 723 metadata, so `uv` can run it without manual installation steps.

```bash
# List models available in europe-west4
uv run enumerate.py --region europe-west4 --project your-project-id
```

### Using standard pip

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Run the script:
    ```bash
    python enumerate.py --region europe-west4 --project your-project-id
    ```

## Arguments

- `--region`: The Google Cloud region to check (e.g., `europe-west4`, `us-east1`). Defaults to `us-central1`.
- `--project`: Your Google Cloud Project ID. (Can also be set via `GOOGLE_CLOUD_PROJECT` env var or `.env` file).
- `--publisher`: The model publisher to list (default: `google`).

## Output

The script logs progress/debug info to `stderr` and prints the final clean list to `stdout`. This allows you to pipe the output directly to a file:

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
