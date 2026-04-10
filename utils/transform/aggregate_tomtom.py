"""
aggregate_tomtom.py

Reads all TomTom ndjson snapshots and aggregates speed data into
30-minute time buckets per road segment.

Output: data/processed/tomtom_buckets.csv
"""

import json
import glob
import hashlib
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# --- config ---
RAW_DIR = Path("raw data/iasi data tomtom")
OUTPUT   = Path("data/processed/tomtom_buckets.csv")
BUCKET_MINUTES = 30

# --- helpers ---

def segment_id(lat, lon):
    """Stable string ID for a (lat, lon) query point."""
    key = f"{lat:.4f},{lon:.4f}"
    return hashlib.md5(key.encode()).hexdigest()[:10]

def to_bucket(dt):
    """Round a datetime down to the nearest 30-min slot. Returns 'HH:MM' string."""
    minutes = (dt.hour * 60 + dt.minute) // BUCKET_MINUTES * BUCKET_MINUTES
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def day_type(dt):
    return "weekend" if dt.weekday() >= 5 else "weekday"

def interpolate_buckets(buckets_data):
    """
    For each (segment, day_type) pair, fill missing buckets by linear
    interpolation between the nearest known values.
    Returns the same structure with added interpolated entries.
    """
    # Generate all possible bucket labels for a full day
    all_buckets = []
    t = 0
    while t < 24 * 60:
        all_buckets.append(f"{t // 60:02d}:{t % 60:02d}")
        t += BUCKET_MINUTES

    filled = {}
    for key, bucket_map in buckets_data.items():
        filled[key] = {}
        known = {b: bucket_map[b] for b in bucket_map}

        for i, b in enumerate(all_buckets):
            if b in known:
                filled[key][b] = {**known[b], "interpolated": False}
            else:
                # find nearest known buckets before and after
                prev = next((all_buckets[j] for j in range(i - 1, -1, -1) if all_buckets[j] in known), None)
                nxt  = next((all_buckets[j] for j in range(i + 1, len(all_buckets)) if all_buckets[j] in known), None)

                if prev and nxt:
                    p, n = known[prev], known[nxt]
                    filled[key][b] = {
                        "avg_speed":       (p["avg_speed"] + n["avg_speed"]) / 2,
                        "avg_free_flow":   (p["avg_free_flow"] + n["avg_free_flow"]) / 2,
                        "avg_congestion":  (p["avg_congestion"] + n["avg_congestion"]) / 2,
                        "n_samples":       0,
                        "interpolated":    True,
                    }
                elif prev:
                    filled[key][b] = {**known[prev], "n_samples": 0, "interpolated": True}
                elif nxt:
                    filled[key][b] = {**known[nxt], "n_samples": 0, "interpolated": True}
                # if neither exists, skip (segment has no data at all)

    return filled

# --- main ---

def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # accumulator: {(seg_id, lat, lon, frc, bucket, day_type): [speeds, free_flows]}
    raw = defaultdict(lambda: {"speeds": [], "free_flows": [], "lat": 0, "lon": 0, "frc": ""})

    ndjson_files = sorted(RAW_DIR.glob("tomtom_raw_flow_data_*.ndjson"))
    print(f"Reading {len(ndjson_files)} snapshot files...")

    for filepath in ndjson_files:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts  = record.get("query_timestamp", "")
                lat = record.get("query_lat")
                lon = record.get("query_lon")
                fsd = record.get("tomtom_raw_response", {}).get("flowSegmentData", {})

                if not ts or lat is None or lon is None or not fsd:
                    continue
                if fsd.get("roadClosure"):
                    continue

                current   = fsd.get("currentSpeed")
                free_flow = fsd.get("freeFlowSpeed")
                frc       = fsd.get("frc", "")

                if current is None or free_flow is None or free_flow == 0:
                    continue

                try:
                    dt = datetime.fromisoformat(ts)
                except ValueError:
                    continue

                key = (segment_id(lat, lon), to_bucket(dt), day_type(dt))
                raw[key]["speeds"].append(current)
                raw[key]["free_flows"].append(free_flow)
                raw[key]["lat"] = lat
                raw[key]["lon"] = lon
                raw[key]["frc"] = frc

    print(f"Aggregating {len(raw)} (segment, bucket, day_type) combinations...")

    # build per-segment bucket maps for interpolation
    # structure: {(seg_id, day_type): {bucket: {...}}}
    buckets_data = defaultdict(dict)
    meta = {}  # seg_id -> (lat, lon, frc)

    for (seg_id_, bucket, dtype), vals in raw.items():
        speeds     = vals["speeds"]
        free_flows = vals["free_flows"]
        avg_s  = sum(speeds) / len(speeds)
        avg_ff = sum(free_flows) / len(free_flows)
        avg_c  = sum(s / ff for s, ff in zip(speeds, free_flows)) / len(speeds)

        buckets_data[(seg_id_, dtype)][bucket] = {
            "avg_speed":      round(avg_s, 2),
            "avg_free_flow":  round(avg_ff, 2),
            "avg_congestion": round(avg_c, 4),
            "n_samples":      len(speeds),
        }
        meta[seg_id_] = (vals["lat"], vals["lon"], vals["frc"])

    filled = interpolate_buckets(buckets_data)

    # write CSV
    fieldnames = [
        "segment_id", "query_lat", "query_lon", "frc",
        "bucket", "day_type",
        "avg_speed", "avg_free_flow", "avg_congestion",
        "n_samples", "interpolated"
    ]

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for (seg_id_, dtype), bucket_map in sorted(filled.items()):
            lat, lon, frc = meta.get(seg_id_, (0, 0, ""))
            for bucket, vals in sorted(bucket_map.items()):
                writer.writerow({
                    "segment_id":     seg_id_,
                    "query_lat":      lat,
                    "query_lon":      lon,
                    "frc":            frc,
                    "bucket":         bucket,
                    "day_type":       dtype,
                    "avg_speed":      vals["avg_speed"],
                    "avg_free_flow":  vals["avg_free_flow"],
                    "avg_congestion": vals["avg_congestion"],
                    "n_samples":      vals["n_samples"],
                    "interpolated":   vals["interpolated"],
                })

    print(f"Done. Output: {OUTPUT}")


if __name__ == "__main__":
    main()
