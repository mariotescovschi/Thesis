# SUMO Network — Iași

## Fișiere

- `iasi_bbbike.osm` — date OSM brute descărcate via BBBike (OSM XML format)
- `iasi.net.xml` — rețeaua SUMO generată din OSM, folosită în simulare
- `iasi_network_preview.png` — preview vizual al rețelei (generat cu matplotlib)
- `bbbike/` — arhiva originală descărcată de la BBBike (păstrată ca referință)

## Cum a fost obținută rețeaua

### 1. Date OSM

Am încercat inițial Overpass API cu bounding box-ul complet al Iașului
(`47.0722, 27.4754 → 47.2217, 27.7075`), dar serverul returnează eroare
la peste 50.000 de noduri. Am descărcat în tile-uri 2×2 și am unit manual,
dar rețeaua rezultată avea erori de proiecție (`Point outside of projection domain`).

Soluția finală: **BBBike Extract** ([extract.bbbike.org](https://extract.bbbike.org)) —
format OSM XML, același bounding box, fișier complet fără limite.
Fișierul dezarhivat: `iasi_bbbike.osm` (1.8M linii).

### 2. Generare rețea SUMO

```bash
SUMO_HOME=/Library/Frameworks/EclipseSUMO.framework/Versions/1.26.0/EclipseSUMO/share/sumo
SUMO_BIN=/Library/Frameworks/EclipseSUMO.framework/Versions/1.26.0/EclipseSUMO/bin

$SUMO_BIN/netconvert \
  --osm-files iasi_bbbike.osm \
  --output-file iasi.net.xml \
  --geometry.remove \
  --roundabouts.guess \
  --junctions.join \
  --tls.guess-signals \
  --tls.discard-simple \
  --tls.join \
  --proj.utm
```

Rezultat: 4344 noduri, 10109 edges, 16 semafoare detectate automat.

### 3. Vizualizare

SUMO GUI nu funcționează pe macOS Sonoma/Tahoe din cauza unui bug nerezolvat
între XQuartz și noile versiuni de macOS (issue [#17272](https://github.com/eclipse-sumo/sumo/issues/17272)).

Preview generat cu matplotlib din `iasi.net.xml`:

```bash
venv/bin/python3.14 utils/transform/preview_network.py
```

## Note

- `--proj.utm` e necesar pentru proiecție corectă; fără el apar erori de coordonate
- Warning-urile din netconvert (turning radius, intersecting left turns) sunt normale pentru OSM
- Rețeaua include toate tipurile de drumuri din BBBike, inclusiv rezidențiale
