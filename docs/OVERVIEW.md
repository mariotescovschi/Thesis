# Project Overview

Lucrare de licență — antrenarea unui agent PPO pentru optimizarea semafoarelor
într-o simulare SUMO calibrată pe date reale de trafic din Iași.

Agentul controlează timpii de verde/roșu la o intersecție sau un coridor și e evaluat
față de un baseline cu timpi statici. Totul rulează în simulare, fără deployment real.

---

## Date disponibile

- **TomTom Flow Segment API** — 147 snapshot-uri zilnice (nov 2025 – apr 2026),
  ~2500 segmente rutiere, viteze curente + free-flow
- **Primărie Iași** — 110 rapoarte PDF cu volume de trafic (veh/h) și distribuție
  pe tipuri (Car/Truck/Long/Bike), septembrie 2022, ~110 locații din oraș

Detalii în `docs/data/`.

---

## Stack

- **SUMO + TraCI** — simulator de trafic
- **stable-baselines3 PPO** — algoritmul RL
- **Gymnasium** — interfața environment
- **OSM** — sursa rețelei rutiere

---

## Next step

Agregarea datelor TomTom pe bucket-uri orare de 30 de minute, începând cu
intervalul **peak AM (07:00–09:00)**.

Output țintă: `data/processed/tomtom_buckets.csv` cu viteza medie și congestionarea
per segment per bucket, pe baza cărora construim matricea O/D și calibrăm simularea.

Pipeline complet descris în `docs/data/DATA_PIPELINE.md`.
