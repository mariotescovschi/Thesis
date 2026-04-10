# Optimizarea Semafoarelor cu Reinforcement Learning — Iași

Proiect de licență. Antrenăm un agent PPO să controleze semafoarele într-o simulare SUMO calibrată pe date reale din Iași.
Totul rămâne în simulare — nu există deployment real.

---

## Ce vrem să demonstrăm

Că un agent RL (PPO) poate reduce întârzierea medie și lungimea cozilor față de timinguri statice fixe,
pe o rețea rutieră reală din Iași simulată în SUMO.

---

## Date disponibile

| Sursă | Ce conține | Status |
|---|---|---|
| `iasi_data_complete/` | ~140 snapshot-uri TomTom Flow (viteză curentă vs. freeflow, per segment) | ✅ colectat |
| `iasi_data_primarie/` | ~100 PDF-uri cu date primare de trafic (numărători pe artere) | ✅ disponibil, neprelucrat |
| TomTom Flow Segment API | Colectare automată săptămânală via GitHub Actions | ✅ activ |
| Rețea OSM | Harta rutieră Iași (noduri, muchii, semafoare) | ⏳ de importat în SUMO |

---

## Pipeline (în ordine)

```
Date TomTom + PDF-uri primare
        ↓
  Calibrare fluxuri O/D
        ↓
  Rețea SUMO (OSM + ajustări manuale)
        ↓
  Simulare baseline (timinguri statice)
        ↓
  Antrenare PPO (stable-baselines3 + TraCI)
        ↓
  Comparație RL vs. static (delay, queue, speed)
```

---

## Structura repo

```
data/           # date procesate
iasi_data_complete/   # snapshot-uri TomTom raw
iasi_data_primarie/   # PDF-uri numărători trafic
sumo/           # rețea + rute + config simulare
rl/             # mediu Gymnasium + training PPO
scripts/        # colectare și preprocesare date
docs/           # SCOPE, PIPELINE, CHECKPOINTS, DATA
```

---

## Întrebări deschise (de discutat)

1. **Scop geografic**: o singură intersecție, un coridor (ex. Bd. Independenței), sau mai multe?
2. **Date primare PDF**: ce format au exact? Pot fi digitizate automat sau manual?
3. **Metrici de succes**: ce îmbunătățire minimă față de static considerăm relevantă pentru lucrare?
4. **Intersecție țintă**: există una cu date suficiente din ambele surse (TomTom + PDF)?
5. **Timinguri semafoare reale**: avem acces la planurile actuale sau le aproximăm din OSM?

---

## Decizii luate

- Algoritm: PPO (stable-baselines3) — standard în literatura de traffic RL
- Simulator: SUMO + TraCI
- Sursă date: TomTom Flow Segment API + date primare municipiu
- Validare: doar în simulare
