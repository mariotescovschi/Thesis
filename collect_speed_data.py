#!/usr/bin/env python3
"""
Collector for RAW speed data from TomTom Flow Segment Data API.
Extracts: current speed, free flow speed, road type, confidence, road status.
"""
import json
import requests
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TOMTOM_API_KEY")
if not API_KEY:
    raise ValueError("TOMTOM_API_KEY not found in .env file")

# Input file with geometry of all streets in Iasi area (from tiles)
INPUT_FILE = "iasi_data_complete/traffic_flow_tiles.geojson"
OUTPUT_DIR = "iasi_data_complete"


def get_flow_segment_data(lat, lon):
    """
    Call TomTom Flow Segment Data API for a specific coordinate.

    Returns detailed information for the street segment at that coordinate:
    - currentSpeed: estimated current speed (km/h)
    - freeFlowSpeed: speed in no-traffic conditions (km/h)
    - frc: road functional classification (FRC1=motorway, FRC4=local street)
    - confidence: how reliable the data is (0-1)
    - roadClosure: boolean - whether street is closed
    - coordinates: complete list of exact segment coordinates
    - currentTravelTime / freeFlowTravelTime: traversal times
    """
    params = {
        "key": API_KEY,
        "point": f"{lat},{lon}"  # Map point for which to request traffic data
    }

    try:
        url = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    Error: {e}")
        return None


def extract_center_point(geometry):
    """
    Extract geometric center of a street.

    Input: GeoJSON geometry of a street (LineString or MultiLineString)
    Output: (lat, lon) - point from middle of street

    TomTom API requires a single point to query.
    We choose the midpoint for better representation.
    """
    if geometry['type'] == 'LineString':
        coords = geometry['coordinates']
        mid_idx = len(coords) // 2
        lon, lat = coords[mid_idx]
        return lat, lon
    elif geometry['type'] == 'MultiLineString':
        coords = geometry['coordinates'][0]
        mid_idx = len(coords) // 2
        lon, lat = coords[mid_idx]
        return lat, lon
    elif geometry['type'] == 'Point':
        lon, lat = geometry['coordinates']
        return lat, lon
    return None, None


def main():
    """
    Main flow - Collect RAW traffic data for ALL streets in Iasi.
    """
    print("=" * 60)
    print("Traffic data collector - TomTom Flow Segment API")
    print("=" * 60)

    # 1. READ GEOMETRY OF ALL STREETS
    print(f"\nReading input data: {INPUT_FILE}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Process ALL segments (no longer limited to 400)
    features = data['features']
    print(f"   Total street segments found: {len(features)}")

    # 2. COLLECT RAW DATA FROM EACH STREET
    print("\nCollecting traffic data from API...")
    raw_data = []

    for idx, feature in enumerate(features[:1], 1):  # LIMIT TO 1 FOR TESTING
        # Extract geometric center of street
        lat, lon = extract_center_point(feature['geometry'])
        if not lat or not lon:
            continue

        print(f"   [{idx}/{len(features)}] Coordinates: {lat:.5f}, {lon:.5f}")

        # Call API
        tomtom_response = get_flow_segment_data(lat, lon)

        if tomtom_response:
            # 3. SAVE COMPLETE RESPONSE (with ALL data)
            record = {
                'query_timestamp': datetime.now().isoformat(),  # When collected
                'query_lat': lat,  # Lat where queried
                'query_lon': lon,  # Lon where queried
                'tomtom_raw_response': tomtom_response  # COMPLETE RAW API RESPONSE
            }
            raw_data.append(record)

            # Display info: current speed vs free flow speed
            if 'flowSegmentData' in tomtom_response:
                seg = tomtom_response['flowSegmentData']
                current_spd = seg.get('currentSpeed', 'N/A')
                free_spd = seg.get('freeFlowSpeed', 'N/A')
                print(f"      Current speed: {current_spd} km/h | Free flow speed: {free_spd} km/h")

        # Pause between calls (rate limiting)
        time.sleep(0.2)

    # 4. SAVE DATA TO FILES
    print(f"\nSaving {len(raw_data)} records...")

    # Generate timestamp and metadata
    execution_time = datetime.now()
    timestamp_str = execution_time.strftime('%Y%m%d_%H%M%S')  # Format: 20251107_143522

    metadata = {
        'execution_date': execution_time.strftime('%Y-%m-%d'),
        'execution_time': execution_time.strftime('%H:%M:%S'),
        'execution_datetime_iso': execution_time.isoformat(),
        'total_records': len(raw_data),
        'input_file': INPUT_FILE,
        'output_files': {
            'ndjson': f'tomtom_raw_flow_data_{timestamp_str}.ndjson',
            'json': f'tomtom_raw_flow_data_{timestamp_str}.json',
            'metadata': f'tomtom_raw_flow_metadata_{timestamp_str}.json'
        }
    }

    # Format NDJSON (JSON Lines) - one line per record
    # Good for step-by-step processing and ML training
    ndjson_path = os.path.join(OUTPUT_DIR, f"tomtom_raw_flow_data_{timestamp_str}.ndjson")
    with open(ndjson_path, 'w', encoding='utf-8') as f:
        for record in raw_data:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print(f"   Saved: {ndjson_path}")

    # Format JSON standard - single structure
    json_path = os.path.join(OUTPUT_DIR, f"tomtom_raw_flow_data_{timestamp_str}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)
    print(f"   Saved: {json_path}")

    # Save METADATA separately
    metadata_path = os.path.join(OUTPUT_DIR, f"tomtom_raw_flow_metadata_{timestamp_str}.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"   Saved: {metadata_path}")
    print(f"\nDate: {metadata['execution_date']}")
    print(f"Time: {metadata['execution_time']}")

    print(f"\nDone! Collected {len(raw_data)} RAW responses from API")


if __name__ == "__main__":
    main()
