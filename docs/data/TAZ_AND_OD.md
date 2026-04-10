# TAZ și Matricea O/D

## Ce sunt zonele TAZ

Traffic Analysis Zones — împărțim Iașul în 12 zone geografice. Fiecare zonă e o sursă
și o destinație de trafic. Vehiculele pleacă dintr-o zonă și ajung în alta; SUMO calculează
ruta individuală prin rețea.

Zonele sunt definite în `utils/transform/define_taz.py` ca poligoane GPS și exportate în
`data/processed/taz.geojson`.

---

## Cele 12 zone

| ID | Nume | Tip | Weight |
|---|---|---|---|
| Z01 | Centru | commercial | 9 |
| Z02 | Podu Roș | mixed | 6 |
| Z03 | Tătărași Nord | residential | 8 |
| Z04 | Tătărași Sud | residential | 7 |
| Z05 | Nicolina | residential | 9 |
| Z06 | Copou | mixed | 7 |
| Z07 | Păcurari | residential | 7 |
| Z08 | CUG | residential | 8 |
| Z09 | Galata | residential | 5 |
| Z10 | Tudor Vladimirescu | residential | 8 |
| Z11 | Gară / Vest | mixed | 5 |
| Z12 | Exterior | external | 6 |

**Weight** = forța relativă de generare/atracție a traficului (1-10).
Zonele rezidențiale dense primesc weight mare (8-9). Zonele periferice sau mici primesc mai puțin.
Z12 (Exterior) captează traficul care intră/iese din oraș pe drumurile naționale.

Zonele sunt un proof-of-concept. Granularitatea poate fi mărită ulterior pe măsură ce
datele de calibrare devin disponibile.

---

## Matricea O/D

Definește câte vehicule pleacă din zona A spre zona B, per interval de 30 minute.

Generată de `utils/transform/build_od_matrix.py`, output în `data/processed/od_matrix.csv`.

### Formula — Gravity Model

```
flow(A→B) = K * weight_A * weight_B / distance(A,B)²
```

- `weight_A`, `weight_B` — forța de generare/atracție a zonelor
- `distance(A,B)` — distanța în km între centroizii zonelor (Haversine)
- `K` — constantă de scalare astfel încât suma totală = `TOTAL_DAILY_VEHICLES`

Zonele apropiate și cu weight mare schimbă mai mult trafic între ele.
Zonele îndepărtate schimbă mai puțin, indiferent de weight.

### Profilul orar

Distribuția pe intervale de 30 min vine din datele TomTom:

```
demand(bucket) ∝ 1 / avg_congestion(bucket)
```

Mai multă congestionare = mai mult trafic în acel interval.
Profilul e normalizat astfel încât suma pe o zi = 1.0.

Weekend-ul e scalat la 60% din weekday.

### Volumul total

`TOTAL_DAILY_VEHICLES = 150.000` — estimare pentru Iași (~300k locuitori).
Valoare placeholder, va fi înlocuită cu date reale din PDF-urile Primăriei.

---

## Limitări și decizii

- Poligoanele zonelor sunt bounding box-uri aproximative, nu granițe administrative exacte
- Weight-urile sunt estimate manual, nu din date demografice
- Gravity model nu distinge tipul de deplasare (muncă, cumpărături, etc.)
- Profilul orar e agregat city-wide, nu per zonă — în realitate Copou (universitar)
  are un peak diferit față de Nicolina (rezidențial pur)
- Toate aceste simplificări sunt acceptabile pentru un proof-of-concept;
  calibrarea cu date reale vine în pasul următor
