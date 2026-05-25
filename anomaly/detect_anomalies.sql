-- SecureStream anomaly detection
--
-- Rebuilds the flagged_events table from every reading in raw_telemetry
-- that breaches the temperature threshold rule. A normal sensor reads
-- roughly 18 to 26 degrees, so anything outside the 0 to 40 range is
-- treated as an out-of-range anomaly, for example a spoofed or faulty
-- reading.
--
-- This is a full rebuild, so running it any number of times never
-- creates duplicate rows. Run it on a schedule, or by hand for a demo.

TRUNCATE TABLE `securestream-iot-7f3k.securestream.flagged_events`;

INSERT INTO `securestream-iot-7f3k.securestream.flagged_events`
  (device_id, metric, value, reason, event_time, detected_at)
SELECT
  JSON_VALUE(data, '$.device_id')              AS device_id,
  JSON_VALUE(data, '$.metric')                 AS metric,
  CAST(JSON_VALUE(data, '$.value') AS FLOAT64) AS value,
  'temperature_out_of_range'                   AS reason,
  TIMESTAMP(JSON_VALUE(data, '$.ts'))          AS event_time,
  CURRENT_TIMESTAMP()                          AS detected_at
FROM `securestream-iot-7f3k.securestream.raw_telemetry`
WHERE JSON_VALUE(data, '$.metric') = 'temperature'
  AND CAST(JSON_VALUE(data, '$.value') AS FLOAT64) NOT BETWEEN 0 AND 40;
