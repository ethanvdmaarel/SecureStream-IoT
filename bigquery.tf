# Dataset that holds all telemetry tables.
resource "google_bigquery_dataset" "securestream" {
  dataset_id                 = "securestream"
  location                   = var.region
  delete_contents_on_destroy = true

  depends_on = [google_project_service.enabled]
}

# Raw landing table. The Pub/Sub subscription writes here.
# These five columns are the schema Pub/Sub expects for a BigQuery
# subscription with write_metadata enabled.
resource "google_bigquery_table" "raw_telemetry" {
  dataset_id          = google_bigquery_dataset.securestream.dataset_id
  table_id            = "raw_telemetry"
  deletion_protection = false

  schema = jsonencode([
    { name = "subscription_name", type = "STRING", mode = "NULLABLE" },
    { name = "message_id", type = "STRING", mode = "NULLABLE" },
    { name = "publish_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "data", type = "STRING", mode = "NULLABLE" },
    { name = "attributes", type = "STRING", mode = "NULLABLE" },
  ])
}

# Table for readings that the anomaly check flags as suspicious.
# The scheduled query in a later step writes rows here.
resource "google_bigquery_table" "flagged_events" {
  dataset_id          = google_bigquery_dataset.securestream.dataset_id
  table_id            = "flagged_events"
  deletion_protection = false

  schema = jsonencode([
    { name = "device_id", type = "STRING", mode = "NULLABLE" },
    { name = "metric", type = "STRING", mode = "NULLABLE" },
    { name = "value", type = "FLOAT", mode = "NULLABLE" },
    { name = "reason", type = "STRING", mode = "NULLABLE" },
    { name = "event_time", type = "TIMESTAMP", mode = "NULLABLE" },
    { name = "detected_at", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}
