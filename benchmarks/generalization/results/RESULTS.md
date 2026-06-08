# Generalizare (OOD) — FloorPlanCAD

Aceleasi 3 modele ca before_after, pe stil complet diferit (CAD colorat chinezesc cu cote/mobilier).

**Calitativ.** FloorPlanCAD adnoteaza simboluri pe linii (semantic-id), NU poligoane de camera => NU exista GT comparabil pentru IoU room. Tabelul de mai jos = ACOPERIRE pixeli per clasa (cat picteaza fiecare model), NU acuratete. Semnalul principal sunt overlay-urile: cine gaseste structura pe un desen nevazut la antrenare, cine se prabuseste.

Overlay: original STANGA | predictie DREAPTA. Culori: room=verde, wall=rosu, door=albastru, window=galben, railing=mov.

| plan | model | %room | %wall | %door | %window | %railing |
|------|-------|------|------|------|------|------|
| 0001-0023 | before | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0001-0023 | after | 39.0 | 11.6 | 0.7 | 1.3 | 0.2 |
| 0001-0023 | cnn | 48.9 | 1.7 | 0.0 | 0.0 | 0.0 |
| 0001-0072 | before | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0001-0072 | after | 51.7 | 15.0 | 1.5 | 0.6 | 0.2 |
| 0001-0072 | cnn | 55.1 | 2.6 | 0.0 | 0.0 | 0.0 |
| 0007-0013 | before | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0007-0013 | after | 49.3 | 7.3 | 0.7 | 0.0 | 0.7 |
| 0007-0013 | cnn | 21.1 | 7.3 | 0.0 | 0.1 | 0.0 |

## Media pe cele 3 planuri OOD

| MEAN OOD | model | %room | %wall | %door | %window | %railing |
|------|-------|------|------|------|------|------|
| **MEAN** | **before** | **0.0** | **0.0** | **0.0** | **0.0** | **0.0** |
| **MEAN** | **after** | **46.7** | **11.3** | **1.0** | **0.6** | **0.4** |
| **MEAN** | **cnn** | **41.7** | **3.9** | **0.0** | **0.0** | **0.0** |
