# utils/transform

Scripts that take raw data and turn it into something usable for simulation.

---

## What's in here

### aggregate_tomtom.py

Reads all TomTom ndjson snapshots from `raw data/iasi data tomtom/` and aggregates
them into 30-minute time buckets per road segment.

**Input:** `raw data/iasi data tomtom/tomtom_raw_flow_data_*.ndjson`

**Output:** `data/processed/tomtom_buckets.csv`

```
segment_id, query_lat, query_lon, frc, bucket, day_type,
avg_speed, avg_free_flow, avg_congestion, n_samples, interpolated
```

- `segment_id` — hash of (query_lat, query_lon), stable identifier per segment
- `bucket` — 30-min slot, e.g. "07:00", "07:30", "08:00"
- `day_type` — "weekday" or "weekend"
- `avg_congestion` — mean of (currentSpeed / freeFlowSpeed) across all samples in bucket
- `n_samples` — how many snapshots fell into this bucket (low = less reliable)
- `interpolated` — True if no samples exist and value was linearly interpolated

---

## What comes next

Once `tomtom_buckets.csv` exists:

1. **Define TAZ polygons** — 12 zones covering Iași (see `docs/data/DATA_PIPELINE.md`)
2. **Build O/D matrix** — estimate flows between zones using gravity model,
   anchored to Primărie sensor volumes where available
3. **Generate SUMO routes** — convert O/D matrix to `.rou.xml` via `od2trips`
4. **Calibrate** — run simulation, compare segment speeds to TomTom buckets, adjust

---

## Notes

- Only `.ndjson` files are read (not `.json`) — line-by-line parsing, memory efficient
- Weekends are separated from weekdays — traffic patterns differ significantly
- Buckets with fewer than 3 samples are flagged but kept; interpolated ones are marked
- The script is idempotent — safe to re-run, overwrites output
