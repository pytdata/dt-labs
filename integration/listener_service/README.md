# Analyzer Listener Service

Runs as a separate process to listen to configured analyzers (TCP/Serial) and post results into the LIS via FastAPI.


## Identifier strategy
The listener will try to match inbound results using the analyzer's configured identifier strategy:
- **patient_id_source**: `patient_no` (default), `sample_id`, or `order_id`
- **patient_id_fallbacks**: optional comma-separated fallbacks, e.g. `sample_id,order_id`

The resolved value is included in the ingest payload as `match_identifier` and `match_identifier_source`.
