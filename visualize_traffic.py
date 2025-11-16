#!/usr/bin/env python3
"""
Visualize all streets in Iași on a map with colors based on traffic levels.
Extracts geometry from traffic_flow_tiles.geojson and renders to PNG.
"""
import json
import cv2
import numpy as np

INPUT_FILE = "iasi_data_complete/traffic_flow_tiles.geojson"
OUTPUT_FILE = "traffic_visualization.png"

MIN_LAT, MIN_LON = 47.0342, 27.5010
MAX_LAT, MAX_LON = 47.2852, 27.6943

IMG_WIDTH, IMG_HEIGHT = 5000, 5000


def latlon_to_pixel(lat, lon, min_lat, max_lat, min_lon, max_lon, img_width, img_height):
    """Convert lat/lon to pixel coordinates on image."""
    norm_lon = (lon - min_lon) / (max_lon - min_lon)
    norm_lat = (lat - min_lat) / (max_lat - min_lat)
    pixel_x = int(norm_lon * img_width)
    pixel_y = int((1 - norm_lat) * img_height)
    return pixel_x, pixel_y


def get_color_for_traffic_level(traffic_level):
    """
    Color based on traffic level (0.0 = red/blocked, 1.0 = green/free flow).
    Returns BGR tuple.
    """
    level = max(0, min(1, traffic_level))
    if level >= 0.7:
        return (0, 255, 0)  # Green
    elif level >= 0.5:
        return (0, 255, 255)  # Yellow
    elif level >= 0.3:
        return (0, 165, 255)  # Orange
    else:
        return (0, 0, 255)  # Red


def load_segments(geojson_data):
    """Extract and convert all street segments to pixel coordinates."""
    segments = []
    features = geojson_data.get('features', [])

    for feature in features:
        geometry = feature.get('geometry', {})
        properties = feature.get('properties', {})
        traffic_level = properties.get('traffic_level', 0.5)
        color = get_color_for_traffic_level(traffic_level)
        geom_type = geometry.get('type')
        coords = geometry.get('coordinates', [])

        pixel_coords_list = []
        if geom_type == 'LineString':
            pixel_coords_list = [coords]
        elif geom_type == 'MultiLineString':
            pixel_coords_list = coords

        for line in pixel_coords_list:
            pixel_coords = []
            for lon, lat in line:
                px, py = latlon_to_pixel(lat, lon, MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, IMG_WIDTH, IMG_HEIGHT)
                if 0 <= px < IMG_WIDTH and 0 <= py < IMG_HEIGHT:
                    pixel_coords.append((px, py))

            if len(pixel_coords) > 1:
                segments.append({'coords': pixel_coords, 'color': color})

    return segments


def visualize():
    """Main: render all streets to image and save."""
    print("Visualizing traffic data...")

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)

    segments = load_segments(geojson_data)
    print(f"   Segments loaded: {len(segments)}")

    image = np.zeros((IMG_HEIGHT, IMG_WIDTH, 3), dtype=np.uint8)

    print("   Rendering...")
    total_lines = 0
    for segment in segments:
        coords = segment['coords']
        color = segment['color']
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            cv2.line(image, (x1, y1), (x2, y2), color, 3)
            total_lines += 1

    # Add legend
    cv2.putText(image, "RED: Heavy (0.0-0.3)", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    cv2.putText(image, "ORANGE: Moderate (0.3-0.5)", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
    cv2.putText(image, "YELLOW: Light (0.5-0.7)", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(image, "GREEN: Free flow (0.7-1.0)", (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(image, f"Segments: {len(segments)}", (20, 190), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imwrite(OUTPUT_FILE, image)
    print(f"   Saved: {OUTPUT_FILE}")
    print(f"   Rendered {total_lines} lines from {len(segments)} segments")


if __name__ == "__main__":
    visualize()
