# Plan arhitectural to CAD structurat

Pipeline care ia o imagine de plan arhitectural (poză, scan, PDF) și scoate o reprezentare
structurată: poligoane de camere cu etichetă semantică, pereți, uși, ferestre, balustrade,
plus relațiile dintre ele. Peste pipeline am construit o aplicație (Mappa) în care poți vedea
rezultatul pe un canvas tip CAD, îl poți edita și poți vorbi cu un model local despre plan.

## Ce am vrut și unde am ajuns

Ideea inițială era un pipeline cât mai general care să mapeze orice fel de plan (arhitectural
sau nu), să îl înțeleagă spațial și, mai departe, să meargă spre planuri mai complexe. N-am
reușit forma generală, așa că am restrâns scope-ul la planuri rezidențiale și am dus efortul
spre ceva care chiar funcționează cap-coadă pe acest domeniu.

Punctul de plecare a fost ideea din FloorplanVLM (fine-tuning plus RL pe un VLM care emite
direct geometrie). Am vrut un PoC asemănător, dar mult mai mic, pe un dataset public.

## Experimentele rulate

### Faza 1: VLM direct (abandonată)

Am vrut un singur model care, din imagine, să scoată direct JSON cu coordonatele exacte ale
camerelor, pereților, ușilor. Am antrenat pe CubiCasa5k (cam 5k planuri rezidențiale finlandeze
adnotate manual).

- Qwen3-VL-32B, QLoRA 4-bit, r=64, pe un A100. Dădea OOM repetat pe aceeași
  imagine mare, era prea greu pentru un singur A100 și inferența era lentă. N-am terminat niciodată
  fine-tuning-ul și nici nu vedeam un improvement clar.
- Qwen3-VL-8B (full bf16 și apoi retrain pe Modal). Aici am reușit să termin antrenări, loss
  scădea, token accuracy a ajuns la ~91.5%. Problema reală: modelul învață sintaxa JSON
  și vocabularul de tipuri de cameră, dar coordonatele erau greșite. Înțelege *ce* e în imagine,
  nu *unde* precis.
- Un side-test cu StarVector (image to SVG), output complet halucinant, dead end în sub 2 ore.

Concluzia după vreo 100 de dolari cheltuiți pe 3 platforme: VLM-urile ating token accuracy mare
și învață formatul, dar estimează pozițiile prin raționament, nu le percep la nivel de pixel.
FloorplanVLM raportează că merge end-to-end, dar cu un training loop (SFT plus GRPO, date masive,
zeci de GPU-uri) care e mult peste buget.

### Faza 2: pipeline hibrid (curentul)

Am pivotat la o arhitectură unde fiecare componentă face ce știe mai bine.

1. Segmentare clasică cu un model Detectron2 (Mask2Former plus Swin-B), fine-tunat pe CubiCasa5k
   pe cele 5 clase (cameră, perete, ușă, fereastră, balustradă). Asta face maparea geometrică
   efectivă, măști precise la nivel de pixel. Rulează local pe CPU.
2. Un layer de VLM (Qwen3-VL-8B, momentan cel simplu, prin endpoint Modal) care pune eticheta
   semantică pe camere, compune relațiile dintre ele și aproximează suprafețele. Ăsta e și motivul
   pentru care am păstrat modelul de 8B din faza 1: pe înțelegere spațială generală și etichetare
   se descurcă bine pentru cât e de mic.
3. Un layer de LLM (model local prin Ollama) folosit pentru interogare pe date și pentru a edita
   planul prin tool-urile disponibile în aplicație. Modelul nu vede pixeli, acționează doar peste
   o descriere de scenă normalizată (camere, segmente, adiacențe).

Cele 3 ieșiri se fuzionează într-un Document structurat pe care aplicația îl poate desena, edita
și exporta (DXF, SVG, JSON).

## Ce am obținut până acum

Trei suite de benchmark (detalii în `benchmarks/RESULTS.md`):

- Geometrie, hibrid vs model monolitic (Claude Opus 4.8 care încearcă tot într-o trecere): IoU
  cameră 0.889 vs 0.672, perete 0.749 vs 0.248. Diferența la pereți e categorică. Modelul
  monolitic scoate câteva dreptunghiuri grosolane unde segmentarea trasează scheletul real.
- Antrenarea contează: modelul fine-tunat bate baseline-ul CNN din CubiCasa pe fiecare clasă, iar
  varianta neantrenată (weights COCO) scorează aproape 0 pe planuri.
- Semantică, head to head pe aceleași 50 de planuri: Claude e marginal mai bun (F1 0.520 vs 0.451,
  p=0.012, semnificativ dar mic). Citire onestă: pierdem puțin la semantică, dar modelul nostru e
  mic, local și ieftin.
- Cost: hibridul e cam de 6 ori mai ieftin per imagine (~$0.014 vs ~$0.088).
- Generalizare OOD (FloorPlanCAD, calitativ): modelul fine-tunat încă găsește pereți (~11%) unde
  baseline-ul CNN se prăbușește (~4%).

Argumentul lucrării: hibridul câștigă decisiv pe geometrie, pierde marginal pe semantică și costă
de câteva ori mai puțin. Împărțirea muncii e justificată.

## Aplicația (Mappa)

Aplicație locală, single-user, fără auth (deliberat). Layout pe 3 panouri: explorer de proiecte, canvas central, panou de chat plus semantică.

Ce face acum:
- Upload imagine, detectare și split multi-floor, analiză prin pipeline.
- Canvas tip CAD cu editare (mută elemente, vertex edit, adaugă pereți, split de cameră,
  calibrare scară, adnotări), optimistic updates, undo/redo.
- Model base imutabil plus overlay editabil. Pipeline-ul scrie baza, toate editările intră în
  overlay, revert înseamnă ștergerea overlay-ului.
- Chat local peste descrierea de scenă, cu preview și confirm pe comenzile de editare propuse.
- Export DXF (layere per clasă), SVG, JSON.
- Calibrare automată a scării din lățimea mediană a ușilor, adiacențe derivate cu shapely.

## Ce urmează (work in progress)

Pasul final, încă neimplementat, e agregarea tuturor datelor (planuri plus alte informații legate
de ele) ca să poți face o căutare smart peste o bază de planuri. Use-case-ul concret pe care vreau
să-l duc la ceva palpabil e în achizițiile imobiliare: un cumpărător sau un agent să poată căuta
prin toate variantele dintr-un database (cerințe pe număr de camere, suprafață, configurație) și
să găsească mult mai ușor ce vrea. Documents-urile pe care le produce Mappa acum sunt deja
input-ul perfect pentru asta.

## Structura repo-ului

```
pipeline/        inferență geometrie (Mask2Former) + baseline CNN CubiCasa
experiments/
  mask2former_training/   antrenare model geometrie (dataset build, evaluate, config)
  vlm_finetuning/         faza 1 abandonată (notițe, config de referință)
benchmarks/      cele 3 suite (before_after, generalization, three_way) + RESULTS.md
app/             aplicația Mappa (frontend + backend), vezi app/docs/repo-map.md
studies/         papers de referință + note
docs/            EXPERIMENT_HISTORY.md (istoricul rulărilor, costuri, decizii), references.md
vendor/          Mask2Former + CubiCasa5k (upstream, vendorizate)
model/           model_final.pth (greutățile antrenate)
```

## Rulare rapidă

Aplicația (din `app/`):

```bash
cd app/frontend && bun install && bun run dev      # SPA pe :5173
cd app/backend  && python3 -m uvicorn main:app --reload   # API pe :8000
```

Inferența de geometrie standalone:

```bash
python3 pipeline/mask2former_infer.py
```

Benchmark-urile sunt re-rulabile, scripturile sunt în `benchmarks/*/`. Detalii și tabele complete
în `benchmarks/RESULTS.md` și `docs/EXPERIMENT_HISTORY.md`. Orice experiment poate fi refacut pe orice set de date.
