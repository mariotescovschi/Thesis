#!/usr/bin/env python3
"""
Collector for traffic and incident data from TomTom APIs.
Extracts: street geometry + traffic levels, and incident reports.
"""
import math
import requests
import json
import time
from datetime import datetime
import mapbox_vector_tile
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TOMTOM_API_KEY")
if not API_KEY:
    raise ValueError("TOMTOM_API_KEY not found in .env file")

ZOOM = 15

# Iasi bounding box
MIN_LAT, MIN_LON = 47.10, 27.52
MAX_LAT, MAX_LON = 47.22, 27.66

OUTPUT_DIR = "iasi_data_complete"

TRAFFIC_FLOW_TILE_URL = "https://api.tomtom.com/traffic/map/4/tile/flow/relative"
TRAFFIC_INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"


def latlon_to_tile_xy(lat, lon, z):
    """Convert lat/lon to tile coordinates (tx, ty)."""
    n = 2 ** z
    xtile = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    ytile = (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n
    return int(xtile), int(ytile)


def tile_pixel_to_lonlat(z, tx, ty, px, py, extent=4096):
    """Convert pixel coordinates within a tile to GPS coordinates."""
    n = 2 ** z
    x_norm = (tx + (px / extent)) / n
    y_norm = (ty + (py / extent)) / n
    lon = x_norm * 360.0 - 180.0
    merc_n = math.pi - 2.0 * math.pi * y_norm
    lat = math.degrees(math.atan(math.sinh(merc_n)))
    return lon, lat


def tiles_for_bbox(min_lat, min_lon, max_lat, max_lon, z):
    """Calculate all tiles covering the bounding box."""
    tx_min, ty_max = latlon_to_tile_xy(min_lat, min_lon, z)
    tx_max, ty_min = latlon_to_tile_xy(max_lat, max_lon, z)
    return [(tx, ty) for tx in range(min(tx_min, tx_max), max(tx_min, tx_max) + 1)
            for ty in range(min(ty_min, ty_max), max(ty_min, ty_max) + 1)]


def ensure_output_dir():
    """Create output directory if missing."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def save_json(data, filename):
    """Save data as JSON."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_ndjson(records, filename):
    """Save records as NDJSON (one JSON per line)."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def convert_geometry(geom, z, tx, ty, extent=4096):
    """Convert tile geometry (pixels) to GPS coordinates."""
    if not geom or 'type' not in geom or 'coordinates' not in geom:
        return None

    typ = geom['type']
    coords = geom['coordinates']

    def conv_point(pt):
        px, py = pt
        return tile_pixel_to_lonlat(z, tx, ty, px, py, extent)

    if typ == 'Point':
        return {"type": "Point", "coordinates": conv_point(coords)}
    elif typ == 'LineString':
        return {"type": "LineString", "coordinates": [conv_point(p) for p in coords]}
    elif typ == 'MultiLineString':
        return {"type": "MultiLineString", "coordinates": [[conv_point(p) for p in part] for part in coords]}
    elif typ == 'Polygon':
        return {"type": "Polygon", "coordinates": [[conv_point(p) for p in ring] for ring in coords]}
    return None


def collect_traffic_flow():
    """
    Collect traffic flow data from vector tiles.
    Extracts: street geometry, traffic levels, road types.
    """
    print("Collecting traffic flow tiles...")
    tiles = tiles_for_bbox(MIN_LAT, MIN_LON, MAX_LAT, MAX_LON, ZOOM)

    all_features = []
    all_records = []

    for tx, ty in tiles:
        try:
            params = {"key": API_KEY}
            url = f"{TRAFFIC_FLOW_TILE_URL}/{ZOOM}/{tx}/{ty}.pbf"
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()

            decoded = mapbox_vector_tile.decode(resp.content)

            for layer_name in decoded.keys():
                layer_obj = decoded[layer_name]
                features = layer_obj.get("features", [])
                extent = layer_obj.get("extent", 4096)

                for feat in features:
                    geom_raw = feat.get("geometry")
                    if not geom_raw or 'type' not in geom_raw:
                        continue

                    geom = convert_geometry(geom_raw, ZOOM, tx, ty, extent)
                    if not geom:
                        continue

                    props = feat.get("properties", {})
                    props.update({
                        "layer": layer_name,
                        "tile_x": tx,
                        "tile_y": ty,
                        "tile_z": ZOOM,
                        "timestamp": datetime.now().isoformat()
                    })

                    feature = {
                        "type": "Feature",
                        "geometry": geom,
                        "properties": props
                    }
                    all_features.append(feature)
                    all_records.append(props)

        except Exception as e:
            print(f"   Error tile {tx},{ty}: {e}")
            continue

        time.sleep(0.2)

    fc = {"type": "FeatureCollection", "features": all_features}
    save_json(fc, "traffic_flow_tiles.geojson")
    save_ndjson(all_records, "traffic_flow_records.ndjson")
    print(f"   Saved {len(all_features)} street segments")


def collect_traffic_incidents():
    """
    Collect traffic incident reports (accidents, closures, roadwork).
    """
    print("Collecting traffic incidents...")

    params = {
        "key": API_KEY,
        "bbox": f"{MIN_LON},{MIN_LAT},{MAX_LON},{MAX_LAT}",
        "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code,iconCategory},startTime,endTime,from,to,length,delay,roadNumbers,aci{probabilityOfOccurrence,numberOfReports,lastReportTime}}}}",
        "language": "ro-RO",
        "t": "1111111111"
    }

    try:
        resp = requests.get(TRAFFIC_INCIDENTS_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        save_json(data, "traffic_incidents_raw.json")

        features = []
        records = []

        if "incidents" in data:
            for incident in data["incidents"]:
                feature = {
                    "type": "Feature",
                    "geometry": incident.get("geometry"),
                    "properties": {**incident.get("properties", {}),
                                   "timestamp": datetime.now().isoformat()}
                }
                features.append(feature)
                records.append(feature["properties"])

        fc = {"type": "FeatureCollection", "features": features}
        save_json(fc, "traffic_incidents.geojson")
        save_ndjson(records, "traffic_incidents_records.ndjson")
        print(f"   Saved {len(features)} incidents")

    except Exception as e:
        print(f"   Error collecting incidents: {e}")


def generate_summary():
    """Generate collection summary with file sizes."""
    print("Generating summary...")

    summary = {
        "collection_time": datetime.now().isoformat(),
        "location": "Iasi, Romania",
        "bounding_box": {
            "min_lat": MIN_LAT,
            "min_lon": MIN_LON,
            "max_lat": MAX_LAT,
            "max_lon": MAX_LON
        },
        "files_collected": []
    }

    if os.path.exists(OUTPUT_DIR):
        for file in os.listdir(OUTPUT_DIR):
            filepath = os.path.join(OUTPUT_DIR, file)
            size = os.path.getsize(filepath)
            summary["files_collected"].append({
                "filename": file,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2)
            })

    save_json(summary, "collection_summary.json")
    total_size = sum(f['size_bytes'] for f in summary['files_collected'])
    print(f"   Total: {len(summary['files_collected'])} files, {total_size / (1024 * 1024):.2f} MB")


def main():
    """Main flow - collect traffic data and incidents."""
    print("=" * 60)
    print("Traffic data collector - TomTom APIs")
    print("=" * 60)

    ensure_output_dir()
    collect_traffic_flow()
    collect_traffic_incidents()
    generate_summary()

    print("Done!")


if __name__ == "__main__":
    main()
