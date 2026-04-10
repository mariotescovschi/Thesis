# Date TomTom — iasi_data_complete

## Ce sunt

Date de trafic colectate zilnic via GitHub Actions din **TomTom Flow Segment API**,
din noiembrie 2025 până în aprilie 2026.

Fișierele se află în `iasi_data_complete/`.

---

## Structura unui snapshot

Fiecare snapshot are 3 fișiere:
```
tomtom_raw_flow_data_20260405_165606.json      # toate recordurile într-un array JSON
tomtom_raw_flow_data_20260405_165606.ndjson    # același conținut, câte un record per linie
tomtom_raw_flow_metadata_20260405_165606.json  # metadata: dată, oră, număr recorduri
```

### Metadata
```json
{
  "execution_date": "2026-04-05",
  "execution_time": "16:56:06",
  "total_records": 2469
}
```

### Un record (structura)
```json
{
  "query_timestamp": "2026-04-05T16:45:31.094075",
  "query_lat": 47.227,
  "query_lon": 27.511,
  "tomtom_raw_response": {
    "flowSegmentData": {
      "frc": "FRC3",
      "currentSpeed": 39,
      "freeFlowSpeed": 57,
      "currentTravelTime": 730,
      "freeFlowTravelTime": 510,
      "confidence": 1.0,
      "roadClosure": false,
      "coordinates": {
        "coordinate": [ {"latitude": ..., "longitude": ...}, ... ]
      }
    }
  }
}
```

**Câmpuri cheie:**
- `frc` — Functional Road Class (FRC1 = autostradă/arteră majoră → FRC5 = stradă locală)
- `currentSpeed` — viteza curentă la momentul colectării (km/h)
- `freeFlowSpeed` — viteza în condiții libere, fără trafic (km/h) — referința "normală"
- `currentTravelTime` / `freeFlowTravelTime` — timp de parcurs în secunde
- `confidence` — calitatea datei (0–1); 96% din recorduri au confidence=1
- `coordinates` — geometria segmentului rutier ca polyline (lista de puncte GPS)

---

## Statistici (snapshot tipic — 5 apr 2026, ora 16:45)

| Metrică               | Valoare             |
| --------------------- | ------------------- |
| Segmente per snapshot | ~2500               |
| Snapshots totale      | 147                 |
| Perioadă acoperită    | Nov 2025 – Apr 2026 |
| Confidence = 1        | 96% din segmente    |
| Drumuri închise       | 0                   |

**Distribuție FRC (tipuri de drum):**
| Clasă | Descriere | Segmente |
|---|---|---|
| FRC1 | Arteră majoră (bd. principale) | 719 |
| FRC2 | Arteră secundară | 173 |
| FRC3 | Stradă colectoare | 798 |
| FRC4 | Stradă locală | 767 |
| FRC5 | Stradă rezidențială | 12 |

**Viteze (snapshot tipic, după-amiază):**
- `currentSpeed`: 7–79 km/h, medie 39 km/h
- `freeFlowSpeed`: 10–79 km/h, medie 45 km/h
- Raport `current/freeflow`: 0.18–1.00, medie 0.85
- Segmente congestionate (raport < 0.7): ~22%

**Geometrie segmente:**
- Fiecare segment are între 2 și 709 puncte GPS (medie ~73 puncte)
- Segmentele sunt lungi — un record TomTom poate acoperi sute de metri sau chiar km

---

## Cum ne ajută

### 1. Indicatorul de congestionare per segment
`raport = currentSpeed / freeFlowSpeed`

- Raport = 1.0 → trafic liber
- Raport < 0.7 → congestionat
- Raport < 0.4 → blocat

Agregat pe toate snapshot-urile din același interval orar, ne dă un **profil de congestionare**
per segment, per oră din zi.

### 2. Geometria segmentelor → mapare pe rețeaua SUMO
Fiecare segment vine cu coordonatele GPS ale traseului. Asta permite maparea pe edge-urile
din rețeaua SUMO prin **nearest-edge matching**.

### 3. Distribuția temporală → scalare volume
Combinat cu datele de la Primărie (volume absolute), raportul de congestionare TomTom arată
cum variază traficul pe parcursul zilei — factor de scalare pentru scenariile de simulare.

### 4. freeFlowSpeed → viteza limită reală per segment
Viteza în condiții libere, folosită ca `maxSpeed` pentru edge-urile SUMO.

---

## Cum s-a ajuns la ~2500 de segmente

### Pasul 1 — Colectarea geometriei (o singură dată, nov 2025)
Scriptul `collect_all_data.py` a descărcat harta Iașului ca **vector tiles** (Tiles API) și a extras
geometria tuturor străzilor vizibile. Rezultat: `traffic_flow_tiles.geojson`.

### Pasul 2 — Definirea punctelor de query
Din fiecare feature din geojson, scriptul extrage **punctul de mijloc** al geometriei.
Acestea devin coordonatele GPS interogare zilnică — ~2500 de puncte.

### Pasul 3 — Query zilnic (Flow Segment API)
Scriptul `collect_speed_data.py` rulează zilnic via GitHub Actions:
```
pentru fiecare din cele ~2500 puncte:
    GET /flowSegmentData?point=lat,lon
    → TomTom returnează segmentul rutier cel mai apropiat + viteza curentă
```
TomTom nu returnează exact punctul interogat — returnează **segmentul rutier** pe care se află
acel punct, care poate fi mult mai lung. De aceea geometria e identică în toate cele 147
snapshot-uri — se schimbă doar `currentSpeed`.

Numărul de segmente a fost determinat de câte features a returnat Tiles API la prima colectare.
Nu s-a implementat o rotație între segmente, deci aceleași ~2500 de puncte sunt interogate zilnic.

**Consecință**: acoperim în principal **arterele principale și colectoarele** din Iași.
Segmentele din afara orașului (drumuri naționale) sunt prezente dar irelevante pentru simulare.

---

## Limitări

- Segmentele sunt lungi — un record poate acoperi mai multe intersecții, nu avem date per-intersecție
- Un singur snapshot per zi — profilul orar se construiește agregând zile diferite la aceeași oră
- Fără volume absolute — TomTom dă doar viteze, volumele vin din datele Primăriei
- Aceleași ~2500 de puncte interogate zilnic, fără rotație între segmente

---

## Strategia de interpolare pentru profilul orar

Avem un snapshot per zi, la ore diferite. Exemplu:
- Luni 20 ian, ora 09:45 → segment X: currentSpeed = 32 km/h
- Luni 27 ian, ora 10:30 → segment X: currentSpeed = 38 km/h

Pentru a construi un **profil orar continuu** per segment:

1. Grupăm toate snapshot-urile pe intervale orare
2. Calculăm media vitezei per segment per interval, peste toate zilele disponibile
3. Interpolăm liniar între intervalele adiacente pentru orele fără date

Exemplu concret:
```
08:00 → medie = 28 km/h  (peak AM)
10:00 → medie = 42 km/h
13:00 → medie = 45 km/h
16:00 → medie = 35 km/h  (peak PM)
09:00 → interpolat: (28 + 42) / 2 = 35 km/h
```

Rezultatul: un **profil de viteză orar per segment** — inputul pentru calibrarea fluxurilor O/D în SUMO.
