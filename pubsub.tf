# Topic that every device message is published to.
resource "google_pubsub_topic" "telemetry" {
  name = "telemetry"

  depends_on = [google_project_service.enabled]
}

# Subscription that writes each message straight into BigQuery.
# No code needed, this is a managed Pub/Sub to BigQuery subscription.
resource "google_pubsub_subscription" "telemetry_to_bq" {
  name  = "telemetry-to-bq"
  topic = google_pubsub_topic.telemetry.id

  bigquery_config {
    table          = "${var.project_id}.${google_bigquery_dataset.securestream.dataset_id}.${google_bigquery_table.raw_telemetry.table_id}"
    write_metadata = true
  }

  depends_on = [
    google_bigquery_table.raw_telemetry,
    google_project_iam_member.pubsub_bq_writer,
  ]
}
