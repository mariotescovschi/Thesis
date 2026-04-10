# RL-Based Traffic Signal Optimization — Iași

Bachelor's thesis project. The goal is to train a Reinforcement Learning agent (PPO) to optimize traffic signal
timings in a realistic SUMO simulation of Iași, using real-world traffic flow data collected from TomTom.

No real deployment. The platform is validated entirely in simulation.

---

## What this project does

1. Collects real traffic flow data from TomTom APIs (automated via GitHub Actions)
2. Builds a calibrated SUMO road network for Iași (OpenStreetMap + manual refinement)
3. Generates realistic Origin-Destination traffic flows from the collected data
4. Trains a PPO agent (stable-baselines3) to control traffic lights
5. Compares RL-controlled vs. static signal timing on metrics: delay, queue length, average speed

---

## Repository structure

```
.
├── data/                        # Raw and processed data
│   └── tomtom/                  # TomTom flow snapshots (moved from iasi_data_complete/)
├── sumo/                        # SUMO network and simulation configs
│   ├── network/                 # .net.xml, .nod.xml, .edg.xml files
│   ├── routes/                  # .rou.xml — generated O/D flows
│   └── config/                  # .sumocfg files
├── rl/                          # RL environment and training
│   ├── env/                     # Gymnasium environment wrapping SUMO via TraCI
│   └── train/                   # PPO training scripts
├── scripts/                     # Data collection and preprocessing utilities
│   ├── collect_speed_data.py    # TomTom Flow Segment API collector
│   └── collect_all_data.py      # Full TomTom data collector (tiles, incidents, POIs)
├── docs/                        # Project documentation
│   ├── SCOPE.md                 # Objectives and boundaries
│   ├── PIPELINE.md              # End-to-end pipeline description
│   ├── CHECKPOINTS.md           # Milestones and done criteria
│   └── DATA.md                  # Data inventory and format reference
├── RelevantStudies/             # Papers and references
├── iasi_data_complete/          # Raw TomTom data (legacy location, to be migrated)
├── .github/workflows/           # GitHub Actions — automated data collection
└── visualize_traffic.py         # Quick visualization of collected data
```

---

## How to run each module

### 1. Data collection (automated)

Runs automatically via GitHub Actions on a weekly schedule. To run manually:

```bash
cp .env.example .env  # add your TOMTOM_API_KEY
pip install -r requirements.txt
python scripts/collect_speed_data.py
```

### 2. SUMO network

Requires SUMO installed (`sumo`, `netconvert`, `netedit`).

```bash
# Import OSM data and generate network
netconvert --osm-files sumo/network/iasi.osm -o sumo/network/iasi.net.xml

# Open in editor
netedit sumo/network/iasi.net.xml
```

### 3. Generate traffic flows

```bash
python scripts/generate_od_flows.py  # (to be implemented)
```

### 4. Run simulation

```bash
sumo-gui -c sumo/config/iasi.sumocfg
```

### 5. Train RL agent

```bash
python rl/train/train_ppo.py  # (to be implemented)
```

---

## Key decisions

- **Algorithm**: PPO (stable-baselines3) — stable, no hyperparameter hell, standard in traffic RL literature
- **Simulator**: SUMO + TraCI — open source, scriptable, well-documented
- **Data source**: TomTom Flow Segment API — real speed/freeflow data for Iași road segments
- **Traffic lights**: approximated from OSM; timings to be calibrated manually or via on-site observation
- **Scope**: single intersection or small corridor first, then scale if time allows

---

## Status

See [docs/CHECKPOINTS.md](docs/CHECKPOINTS.md) for current progress.

---

## References

- [SUMO Documentation](https://sumo.dlr.de/docs/)
- [stable-baselines3](https://stable-baselines3.readthedocs.io/)
- [TomTom Traffic API](https://developer.tomtom.com/traffic-api/documentation)
- RelevantStudies/ — papers on dataset effects, RL for traffic control
