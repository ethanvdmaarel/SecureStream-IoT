# SecureStream — GCP Foundation (Terraform)

This sets up the cloud backend for the SecureStream IoT project: Pub/Sub, BigQuery,
Firestore, a service account and IAM. No hardware is needed for this step. You run
everything from Cloud Shell in your browser, so nothing has to be installed on a laptop.

## What this creates

- A Pub/Sub topic `telemetry` that every device message is published to
- A BigQuery dataset `securestream` with two tables, `raw_telemetry` and `flagged_events`
- A Pub/Sub to BigQuery subscription that lands every message in `raw_telemetry`
- A Firestore database used as the device key registry
- A service account `sa-ingest` for the Cloud Run ingest service, with least-privilege IAM

## Step 1 — Create the project

Open the Google Cloud Console and start Cloud Shell with the terminal icon in the top
right of the page.

Find your billing account ID:

```
gcloud billing accounts list
```

Copy the ID from the `ACCOUNT_ID` column. Then pick a globally unique project ID.
It must be lowercase, 6 to 30 characters. For example `securestream-iot-7f3k`. If the
name is taken the create command fails, so just pick another suffix.

```
gcloud projects create YOUR-PROJECT-ID --name="SecureStream IoT"
gcloud billing projects link YOUR-PROJECT-ID --billing-account=YOUR-BILLING-ID
gcloud config set project YOUR-PROJECT-ID
```

## Step 2 — Get these files into Cloud Shell

Easiest for now: in Cloud Shell click the three-dot menu, choose Upload, and upload
this whole `securestream` folder.

Better for the long run: push this folder to the group's GitHub repo and run
`git clone` in Cloud Shell. The proposal lists a GitHub repo as a deliverable anyway,
so doing it now saves work later.

## Step 3 — Set your project ID

Open `terraform.tfvars` and replace the placeholder with the project ID from step 1.
You can edit it in Cloud Shell with `nano terraform.tfvars` or the built-in editor.

## Step 4 — Apply

```
cd securestream
terraform init
terraform plan
terraform apply
```

Type `yes` when prompted. The first apply takes a few minutes because it enables APIs.

If the BigQuery subscription step fails on the very first run, just run `terraform apply`
again. GCP service agents sometimes take a minute to become available after an API is
enabled, and a second run picks them up.

## Step 5 — Check it worked

```
terraform output
```

You should see the topic name, the dataset, the Firestore database and the ingest
service account. You can also browse to Pub/Sub, BigQuery and Firestore in the console
and see them there.

## Smoke test

This checks that the topic to BigQuery path works, before the ingest service exists.
Publish a fake message by hand:

```
gcloud pubsub topics publish telemetry \
  --message='{"device_id":"test-01","metric":"temperature","value":21.5,"ts":"2026-06-01T12:00:00Z"}'
```

Wait about a minute, then run this in the BigQuery console:

```
SELECT * FROM securestream.raw_telemetry ORDER BY publish_time DESC LIMIT 10;
```

Your test message should appear, with the JSON in the `data` column.

## Tearing it down

To remove everything and stop all usage:

```
terraform destroy
```

## What is next

Once this foundation is up, the next pieces are the Cloud Run ingest service and the
Python device simulator. Both plug into the `telemetry` topic and the `sa-ingest`
service account created here. Ask Claude to generate them when you are ready.
