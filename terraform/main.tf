# Enforce the organization policy to restrict which Vertex AI models can be used.
# Constraint: constraints/aiplatform.restrictedModelUsage

resource "google_org_policy_policy" "vertex_ai_restricted_model_usage" {
  name   = "projects/${var.project_id}/policies/aiplatform.restrictedModelUsage"
  parent = "projects/${var.project_id}"

  spec {
    rules {
      values {
        allowed_values = var.allowed_models
      }
    }
  }
}
