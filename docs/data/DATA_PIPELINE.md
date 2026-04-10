# Data Pipeline — de la date brute la simulare SUMO

## Obiectiv

Transformăm datele TomTom și Primărie într-un set de fluxuri O/D calibrate,
pe care SUMO le folosește pentru a genera trafic realist.

---

## Pasul 1 — Agregarea datelor TomTom pe bucket-uri orare

Fiecare snapshot zilnic are un timestamp. Împărțim ziua în bucket-uri de 30 de minute
și fiecare snapshot intră în bucket-ul corespunzător orei lui.

**Bucket-uri definite:**
```
06:00–06:30 / 06:30–07:00 / 07:00–07:30 / 07:30–08:00
08:00–08:30 / 08:30–09:00
...
17:00–17:30 / 17:30–18:00 / 18:00–18:30 / 18:30–19:00
```

Per fiecare bucket și per fiecare segment, calculăm:
- `avg_speed` — media vitezelor curente din toate snapshot-urile din acel bucket
- `avg_congestion` — media raportului `currentSpeed / freeFlowSpeed`
- `n_samples` — câte snapshot-uri au intrat în bucket (pentru a ști cât de fiabil e)

Bucket-urile fără niciun snapshot sunt marcate explicit ca interpolate (medie liniară
între bucket-urile vecine cu date).

**Output:** `data/processed/tomtom_buckets.csv`
```
segment_id, day_type, bucket, avg_speed, avg_congestion, n_samples, interpolated
```

---

## Pasul 2 — Definirea zonelor TAZ (Traffic Analysis Zones)

Împărțim Iașul în zone geografice. Fiecare zonă reprezintă o sursă/destinație de trafic.

Zone propuse (de rafinat pe hartă):
- Centru
- Copou
- Tătărași Nord / Sud
- Nicolina
- Păcurari
- CUG
- Bucium
- Zona industrială Est

Fiecare zonă e definită ca un poligon GPS. Fiecare edge din rețeaua SUMO e asignat
unei zone în funcție de locația lui geografică.

**Output:** `data/processed/taz.xml` (format SUMO)

---

## Pasul 3 — Construirea matricei O/D

Matricea O/D specifică câte vehicule pleacă din zona A spre zona B per interval orar.

**Estimare inițială** via gravity model:
- Zonele rezidențiale (landuse=residential din OSM) generează trafic dimineața
- Zonele comerciale/de birouri (landuse=commercial, office) atrag trafic dimineața
- Invers seara

**Calibrare** iterativă față de datele TomTom:
1. Rulăm simularea cu matricea estimată
2. Comparăm `avg_speed` per segment din SUMO cu `avg_speed` din TomTom
3. Ajustăm volumele O/D până erorile scad sub un prag acceptabil

Tool SUMO folosit: `od2trips` pentru conversia matricei în rute individuale.

**Output:** `data/processed/od_matrix_{interval}.csv`

---

## Pasul 4 — Integrarea datelor Primărie

Datele Primăriei dau **volume absolute** (veh/h) și **distribuția pe tipuri**
(Car / Truck / Long / Bike) pentru senzorii lor specifici.

Folosim asta pentru:
1. **Ancorarea matricei O/D** — în loc să estimăm volumele din gravity model,
   le ancorăm pe arterele unde avem senzori reali
2. **Distribuția tipurilor de vehicule** — procentul de camioane și vehicule lungi
   per arteră, per interval orar

**Output:** `data/processed/primarie_flows.csv`
```
sensor_id, artera, interval, volume_car, volume_truck, volume_long, volume_bike
```

---

## Strategie de lucru

Începem cu un singur interval orar — **peak AM (07:00–09:00)** — și construim
tot pipeline-ul de la capăt până la simulare funcțională. Odată validat, replicăm
pentru celelalte intervale.

Nu avem nevoie de toate intervalele pentru a valida arhitectura.

**Ordinea:**
1. Agregare TomTom → buckets peak AM
2. Definire TAZ pe hartă
3. Matrice O/D estimată + calibrată pe peak AM
4. Simulare SUMO funcțională pe peak AM
5. Antrenare PPO pe peak AM
6. Replicare pentru off-peak și peak PM
 