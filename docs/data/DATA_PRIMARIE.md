# Date Primare — Primăria Iași

## Ce sunt

Rapoarte de trafic generate de **DataCollect Webreporter v1.0** (F.I.P. Consulting SRL, București),
primite direct de la Primăria Iași. Măsurătorile au fost efectuate în **septembrie 2022** cu senzori
fizici de tip **SDR Traffic+** plasați pe arterele principale ale orașului.

Fișierele se află în `iasi_data_primarie/` — ~100 PDF-uri, fiecare reprezentând un senzor pe un sens
de circulație.

---

## Structura unui fișier

Numele fișierului codifică direct locația:
```
73.1 - din Str Stefan cel Mare si Sfant.pdf
 ^  ^    ^
 |  |    └── numele arterei / sensul de circulație
 |  └──────── direcția (1 = oncoming, 2 = outgoing)
 └─────────── numărul senzorului
```

Fiecare PDF conține:

### 1. Header cu metadata
- `Name` — numărul senzorului
- `Dir. Oncoming (name)` — numele direcției măsurate (ex: "Stefan cel Mare", "Iesire", "Intrare")
- Perioada măsurătorii (de obicei 24-48h, septembrie 2022)
- Limita de viteză postată: 50 km/h

### 2. Tabel volume agregate pe intervale orare

| Time | Σ | Bike | Car | Truck | Long |
|---|---|---|---|---|---|
| 00:00-06:00 | 320 | 0 | 225 | 55 | 40 |
| 06:00-09:00 | 1291 | 0 | 918 | 192 | 181 |
| 15:00-19:00 | 2528 | 0 | 1817 | 374 | 337 |
| 06:00-22:00 | 7839 | 0 | 5602 | 1191 | 1046 |
| 00:00-24:00 | 8346 | 0 | 5955 | 1286 | 1105 |

Intervalele fixe acoperă: noapte, peak AM, peak PM, zi, 24h.

### 3. Tabel viteze calculate

| | Vmin | Vmax | Vavg | V15 | V50 | V85 | Vexc% |
|---|---|---|---|---|---|---|---|
| Stefan cel Mare | 5 | 115 | 55 | 35 | 58 | 70 | 68.7 |

- **V85** = viteza sub care circulă 85% din vehicule (standard în ingineria traficului)
- **Vexc%** = procentul vehiculelor care depășesc limita de viteză

### 4. Date granulare la 15 minute
Fiecare PDF conține și datele brute la interval de 15 minute pentru întreaga perioadă de măsurătoare,
cu aceleași coloane (Σ, Bike, Car, Truck, Long + distribuție pe benzi de viteză).

---

## Limitări importante

**Nu avem coordonate GPS ale senzorilor.** Locația se deduce exclusiv din numele fișierului.

Maparea se face prin geocodare după numele arterei:
- `73.1 - din Str Stefan cel Mare si Sfant.pdf` → Str. Ștefan cel Mare și Sfânt
- `1 - Sens Iesire Iasi.pdf` → intrare/ieșire oraș (arteră principală)
- `29 - din Pod Rosu.pdf` → zona Pod Roșu

Această mapare introduce o incertitudine de poziționare — știm strada, dar nu știm exact
la ce kilometru/intersecție era senzorul.

---

## Cum ne ajută

### Volumele de trafic → input pentru simulare
Avem numărul real de vehicule care trec pe fiecare arteră, pe intervale orare.
Acestea sunt folosite ca **ground truth** pentru a calibra câte vehicule injectăm în simulatorul SUMO.

Exemplu concret:
- Pe Str. Ștefan cel Mare, în peak AM (06-09): **918 mașini + 192 camioane + 181 vehicule lungi**
- Asta înseamnă ~430 vehicule/oră în medie, cu vârf probabil în intervalul 07:30-08:30

### Distribuția pe tipuri → compoziția flotei în SUMO
SUMO permite definirea mai multor tipuri de vehicule cu parametri diferiți (lungime, accelerație, viteză).
Raportul Car/Truck/Long din date ne dă direct compoziția realistă a flotei per arteră.

### Vitezele → validare și calibrare
Viteza medie (Vavg) și V85 per arteră pot fi comparate cu datele TomTom (`freeFlowSpeed`)
pentru a valida că simularea produce viteze realiste.

### Pattern temporal → scenarii de simulare
Raportul `peak AM / 24h` și `peak PM / 24h` ne dă factorul de scalare pentru a genera
scenarii de simulare reprezentative (nu simulăm 24h, ci un interval de 1-2h de vârf).

---

## Acoperire geografică

Senzorii acoperă arterele principale din Iași, inclusiv:
- Bd. Tudor Vladimirescu, Bd. Independenței, Bd. Carol I
- Str. Ștefan cel Mare și Sfânt, Str. Sărăriei, Str. Elena Doamna
- Calea Chișinăului, Șos. Nicolina, Șos. Națională
- Pod Roșu, Pasaj Alexandru cel Bun, Pasaj Nicolina
- Intrări/ieșiri din oraș (sens intrare / sens ieșire)

Numerotarea senzorilor (1–100) sugerează o acoperire sistematică a rețelei principale.
