output "telemetry_topic" {
  description = "Pub/Sub topic devices publish to."
  value       = google_pubsub_topic.telemetry.id
}

output "bigquery_dataset" {
  description = "BigQuery dataset holding the telemetry tables."
  value       = google_bigquery_dataset.securestream.dataset_id
}

output "ingest_service_account" {
  description = "Service account for the Cloud Run ingest service."
  value       = google_service_account.ingest.email
}

output "firestore_database" {
  description = "Firestore database used as the device registry."
  value       = google_firestore_database.registry.name
}
