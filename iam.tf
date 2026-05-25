# Service account the Cloud Run ingest service runs as.
resource "google_service_account" "ingest" {
  account_id   = "sa-ingest"
  display_name = "SecureStream ingest service"

  depends_on = [google_project_service.enabled]
}

# Least privilege: the ingest service may publish to the telemetry topic, nothing else.
resource "google_pubsub_topic_iam_member" "ingest_publisher" {
  topic  = google_pubsub_topic.telemetry.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.ingest.email}"
}

# Least privilege: the ingest service may read device public keys from Firestore, read only.
resource "google_project_iam_member" "ingest_firestore" {
  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.ingest.email}"
}

# Make sure the Pub/Sub service agent exists so we can grant it BigQuery access.
resource "google_project_service_identity" "pubsub" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"

  depends_on = [google_project_service.enabled]
}

# The Pub/Sub service agent writes messages into BigQuery for the subscription.
resource "google_project_iam_member" "pubsub_bq_writer" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_project_service_identity.pubsub.email}"
}
