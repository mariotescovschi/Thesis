"""
build_od_matrix.py

Builds an Origin-Destination matrix for Iași using a gravity model.
No real volume data required — uses zone weights and TomTom congestion
profiles to distribute a total daily vehicle count across O/D pairs
and time buckets.

Inputs:
  - data/processed/taz.geojson         (zone definitions)
  - data/processed/tomtom_buckets.csv  (hourly congestion profile)

Output:
  - data/processed/od_matrix.csv

Output columns:
  origin, destination, bucket, day_type, flow_veh_per_hour

Formula (gravity model):
  flow(A→B) = K * weight_A * weight_B / distance(A,B)^2

  K is a scaling constant chosen so that total daily flow across all
  O/D pairs equals TOTAL_DAILY_VEHICLES.

The hourly shape comes from TomTom: we compute the city-wide mean
congestion per bucket and invert it — more congestion = more vehicles.
This gives a realistic demand curve without needing absolute counts.
"""

import json
import csv
import math
from pathlib import Path
from collections import defaultdict

TAZ_FILE     = Path("data/processed/taz.geojson")
BUCKETS_FILE = Path("data/processed/tomtom_buckets.csv")
OUTPUT       = Path("data/processed/od_matrix.csv")

# Total vehicles entering the network per day (weekday estimate for Iași).
# This is a reasonable order-of-magnitude for a city of ~300k people.
# Will be replaced with Primărie data once parsed.
TOTAL_DAILY_VEHICLES = 150_000

# Z12 (Exterior) acts as both source and sink for through-traffic,
# but we reduce its self-flow since it's not a real residential zone.
EXTERNAL_ZONE_ID = "Z12"


def haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance in km between two GPS points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def load_zones():
    with open(TAZ_FILE) as f:
        gj = json.load(f)
    zones = {}
    for feat in gj["features"]:
        p = feat["properties"]
        zones[p["id"]] = {
            "name":     p["name"],
            "weight":   p["weight"],
            "centroid": p["centroid"],  # [lon, lat]
            "type":     p["type"],
        }
    return zones


def load_hourly_profile():
    """
    Compute city-wide mean congestion per (bucket, day_type).
    Returns dict: {(bucket, day_type): mean_congestion}
    Only uses measured rows (n_samples > 0).
    """
    profile = defaultdict(list)
    with open(BUCKETS_FILE) as f:
        for row in csv.DictReader(f):
            if row["interpolated"] == "False":
                key = (row["bucket"], row["day_type"])
                profile[key].append(float(row["avg_congestion"]))

    return {k: sum(v) / len(v) for k, v in profile.items()}


def demand_shape(profile, bucket, day_type):
    """
    Convert congestion ratio to a demand multiplier.
    Lower congestion = fewer vehicles; higher congestion = more vehicles.
    We use (1 - congestion) inverted: demand ∝ 1 / congestion.
    Clamped to avoid division by zero.
    """
    cong = profile.get((bucket, day_type), 0.85)
    cong = max(cong, 0.3)
    # More congestion → more demand. Normalize later.
    return 1.0 / cong


def build_gravity_matrix(zones):
    """
    Compute raw gravity flows between all zone pairs.
    Returns dict: {(origin_id, dest_id): raw_flow}
    """
    flows = {}
    zone_ids = list(zones.keys())

    for o_id in zone_ids:
        for d_id in zone_ids:
            if o_id == d_id:
                continue

            o = zones[o_id]
            d = zones[d_id]

            olon, olat = o["centroid"]
            dlon, dlat = d["centroid"]

            dist_km = haversine_km(olon, olat, dlon, dlat)
            dist_km = max(dist_km, 0.5)  # minimum 500m to avoid huge values

            raw = (o["weight"] * d["weight"]) / (dist_km ** 2)

            # Reduce flows to/from external zone slightly
            if o_id == EXTERNAL_ZONE_ID or d_id == EXTERNAL_ZONE_ID:
                raw *= 0.5

            flows[(o_id, d_id)] = raw

    return flows


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    zones   = load_zones()
    profile = load_hourly_profile()

    print(f"Loaded {len(zones)} zones, {len(profile)} measured (bucket, day_type) pairs")

    gravity = build_gravity_matrix(zones)
    total_gravity = sum(gravity.values())

    # All possible buckets and day types from the profile
    buckets   = sorted(set(b for b, _ in profile))
    day_types = ["weekday", "weekend"]

    # Demand shape per bucket — normalized so weekday sums to 1.0 across all buckets
    shapes = {}
    for dt in day_types:
        raw_shape = {b: demand_shape(profile, b, dt) for b in buckets}
        total = sum(raw_shape.values())
        shapes[dt] = {b: v / total for b, v in raw_shape.items()}

    # Weekend total is ~60% of weekday
    weekend_factor = 0.6

    rows = []
    for (o_id, d_id), grav in gravity.items():
        base_daily = (grav / total_gravity) * TOTAL_DAILY_VEHICLES

        for dt in day_types:
            daily = base_daily * (1.0 if dt == "weekday" else weekend_factor)
            for bucket in buckets:
                flow = daily * shapes[dt][bucket]
                if flow < 0.1:
                    continue  # skip negligible flows
                rows.append({
                    "origin":            o_id,
                    "destination":       d_id,
                    "bucket":            bucket,
                    "day_type":          dt,
                    "flow_veh_per_hour": round(flow, 2),
                })

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["origin", "destination", "bucket", "day_type", "flow_veh_per_hour"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows to {OUTPUT}")

    # Quick sanity check
    weekday_total = sum(r["flow_veh_per_hour"] for r in rows if r["day_type"] == "weekday")
    print(f"Total weekday vehicle-hours across all O/D pairs: {weekday_total:,.0f}")
    print(f"(Expected ~{TOTAL_DAILY_VEHICLES:,} daily vehicles distributed across {len(buckets)} buckets)")


if __name__ == "__main__":
    main()
