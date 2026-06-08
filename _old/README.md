# _old — Proiect trafic Iași (abandonat)

Simulare trafic + RL pentru optimizare semafoare. Abandonat din lipsă ground truth validabil.

## Foldere

| Folder | Ce conține |
|--------|-----------|
| `raw_data/tomtom/` | ~460 fișiere JSON/NDJSON — date trafic TomTom API (dec 2025 – apr 2026) |
| `raw_data/primarie/` | ~110 PDF-uri — contoare trafic de la Primăria Iași |
| `data/processed/` | OD matrix, TAZ GeoJSON, TomTom buckets agregate |
| `sumo/` | Rețea SUMO Iași (188MB .net.xml), rute, config, rezultate simulare |
| `scripts/` | Colectare date TomTom, vizualizare, transformări (aggregate, OD matrix, TAZ) |
| `studies/` | Paper relevant ("The effect of the dataset") |
| `images/` | Screenshots și vizualizări |
| `github_workflows/` | GitHub Actions pt colectare automată date |
