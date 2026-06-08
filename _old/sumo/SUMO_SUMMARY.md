# SUMO Traffic Simulation — Iași (Rezumat)

## Ce s-a făcut

Simulare trafic SUMO pentru orașul Iași, cu scopul de a calibra un model RL pentru optimizare semafoare.

## Rețea
- Sursă: BBBike Extract (OSM XML) — bounding box complet Iași
- Conversie: `netconvert` cu `--proj.utm`, geometry.remove, roundabouts.guess, tls.guess-signals
- Rezultat: 4344 noduri, 10109 edges, 16 semafoare
- Fișiere: `iasi_bbbike.osm` (134MB), `iasi.net.xml` (188MB)

## Rute
- OD matrix generat din date TomTom + TAZ-uri definite manual
- `od2trips` → `duarouter` → routes_weekday.xml
- ~158K trips/zi simulat

## Configurare
- `iasi_weekday.sumocfg` — simulare 6:00-10:00 (morning peak)
- Output: summary_morning.xml, stats_morning.xml

## De ce s-a abandonat
- Ground truth imposibil de validat — datele TomTom nu sunt suficient de granulare
- TomTom a răspuns la email după 6 luni, fără acces extins la API
- Rezultatele simulării rămân ipoteze necalibrate
