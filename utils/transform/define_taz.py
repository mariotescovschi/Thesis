"""
define_taz.py

Defines the 12 Traffic Analysis Zones (TAZ) for Iași as GPS polygons.
Exports them as GeoJSON for visualization and downstream use.

Output: data/processed/taz.geojson

Each zone has:
  - id: short code (Z01..Z12)
  - name: human-readable name
  - type: residential / commercial / mixed / external
  - weight: relative traffic generation/attraction strength (1-10)
            higher = more vehicles originate/terminate here
  - polygon: list of [lon, lat] coordinates (GeoJSON order)
"""

import json
from pathlib import Path

OUTPUT = Path("data/processed/taz.geojson")

# ---------------------------------------------------------------------------
# Zone definitions
# Polygons are approximate bounding boxes per neighborhood.
# Coordinates are [longitude, latitude] (GeoJSON standard).
#
# Weight rationale:
#   - Large residential blocks (Tătărași, Nicolina, Tudor) → high weight (8-9)
#   - City center (commercial attractor) → high weight (9)
#   - University area (Copou) → medium-high (7), peak at different hours
#   - Smaller/peripheral zones → lower weight (4-6)
#   - External zone (city entry/exit roads) → medium (6), always active
# ---------------------------------------------------------------------------

ZONES = [
    {
        # Nominatim bbox: 47.1543-47.1700, 27.5743-27.5997
        "id": "Z01",
        "name": "Centru",
        "type": "commercial",
        "weight": 9,
        "polygon": [
            [27.574, 47.154], [27.600, 47.154],
            [27.600, 47.170], [27.574, 47.170],
            [27.574, 47.154],
        ],
    },
    {
        # Nominatim: 47.1505, 27.5865 — Podu Roș bridge area, east of centru
        "id": "Z02",
        "name": "Podu Ros",
        "type": "mixed",
        "weight": 6,
        "polygon": [
            [27.577, 47.141], [27.600, 47.141],
            [27.600, 47.155], [27.577, 47.155],
            [27.577, 47.141],
        ],
    },
    {
        # Nominatim: 47.1610, 27.6113 — east of centru, near Tudor
        "id": "Z03",
        "name": "Tatarasi Nord",
        "type": "residential",
        "weight": 8,
        "polygon": [
            [27.595, 47.158], [27.625, 47.158],
            [27.625, 47.175], [27.595, 47.175],
            [27.595, 47.158],
        ],
    },
    {
        # South part of Tătărași, below centru — trimmed to stay within network
        "id": "Z04",
        "name": "Tatarasi Sud",
        "type": "residential",
        "weight": 7,
        "polygon": [
            [27.595, 47.141], [27.618, 47.141],
            [27.618, 47.158], [27.595, 47.158],
            [27.595, 47.141],
        ],
    },
    {
        # Nominatim: 47.1488, 27.5776 — south-west of centru
        "id": "Z05",
        "name": "Nicolina",
        "type": "residential",
        "weight": 9,
        "polygon": [
            [27.555, 47.140], [27.585, 47.140],
            [27.585, 47.155], [27.555, 47.155],
            [27.555, 47.140],
        ],
    },
    {
        # Nominatim bbox: 47.1675-47.1928, 27.5498-27.5859 — north-west
        "id": "Z06",
        "name": "Copou",
        "type": "mixed",
        "weight": 7,
        "polygon": [
            [27.550, 47.168], [27.586, 47.168],
            [27.586, 47.193], [27.550, 47.193],
            [27.550, 47.168],
        ],
    },
    {
        # Nominatim: 47.1740, 27.5578 — north-west, above Nicolina
        "id": "Z07",
        "name": "Pacurari",
        "type": "residential",
        "weight": 7,
        "polygon": [
            [27.538, 47.158], [27.562, 47.158],
            [27.562, 47.178], [27.538, 47.178],
            [27.538, 47.158],
        ],
    },
    {
        # CUG — below Nicolina, where road segments exist
        "id": "Z08",
        "name": "CUG",
        "type": "residential",
        "weight": 8,
        "polygon": [
            [27.555, 47.125], [27.585, 47.125],
            [27.585, 47.140], [27.555, 47.140],
            [27.555, 47.125],
        ],
    },
    {
        # Galata — small zone on the western hill, has some road segments
        "id": "Z09",
        "name": "Galata",
        "type": "residential",
        "weight": 5,
        "polygon": [
            [27.538, 47.148], [27.556, 47.148],
            [27.556, 47.162], [27.538, 47.162],
            [27.538, 47.148],
        ],
    },
    {
        # Nominatim: 47.1707, 27.5974 — north, above centru (Moara de Vânt area)
        "id": "Z10",
        "name": "Tudor Vladimirescu",
        "type": "residential",
        "weight": 8,
        "polygon": [
            [27.574, 47.170], [27.615, 47.170],
            [27.615, 47.190], [27.574, 47.190],
            [27.574, 47.170],
        ],
    },
    {
        # Train station area, west of centru
        "id": "Z11",
        "name": "Gara Vest",
        "type": "mixed",
        "weight": 5,
        "polygon": [
            [27.555, 47.155], [27.574, 47.155],
            [27.574, 47.168], [27.555, 47.168],
            [27.555, 47.155],
        ],
    },
    {
        # Covers all major entry/exit roads — large outer ring around the city
        "id": "Z12",
        "name": "Exterior",
        "type": "external",
        "weight": 6,
        "polygon": [
            [27.505, 47.098], [27.665, 47.098],
            [27.665, 47.215], [27.505, 47.215],
            [27.505, 47.098],
        ],
    },
]


def zone_centroid(polygon):
    """Compute centroid of a polygon as (lon, lat)."""
    coords = polygon[:-1]  # drop closing point
    lon = sum(c[0] for c in coords) / len(coords)
    lat = sum(c[1] for c in coords) / len(coords)
    return lon, lat


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    features = []
    for zone in ZONES:
        clon, clat = zone_centroid(zone["polygon"])
        features.append({
            "type": "Feature",
            "properties": {
                "id":       zone["id"],
                "name":     zone["name"],
                "type":     zone["type"],
                "weight":   zone["weight"],
                "centroid": [clon, clat],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [zone["polygon"]],
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}

    with open(OUTPUT, "w") as f:
        json.dump(geojson, f, indent=2)

    print(f"Exported {len(ZONES)} zones to {OUTPUT}")
    for z in ZONES:
        clon, clat = zone_centroid(z["polygon"])
        print(f"  {z['id']} {z['name']:<22} weight={z['weight']}  centroid=({clat:.4f}, {clon:.4f})")


if __name__ == "__main__":
    main()
