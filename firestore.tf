# Firestore database used as the device key registry.
# Each device id maps to its public key, which the ingest service
# uses to verify the JWT signature on incoming messages.
resource "google_firestore_database" "registry" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  deletion_policy = "DELETE"

  depends_on = [google_project_service.enabled]
}
