# SRCE Supek: YOLO11n trening kroz 100 epoha

Ovaj eksperiment je glavni trening modela za osam klasa gesti. Izveden je na SRCE Supek GPU sustavu.

## Okruženje i parametri

- GPU: NVIDIA A100-SXM4-40GB
- CPU/RAM zahtjev: 8 CPU jezgri, 32 GB RAM-a, 1 GPU
- Python: 3.10.9
- PyTorch: 2.0.0
- Ultralytics: 8.4.150
- model: YOLO11n, prethodno trenirane težine
- epohe: 100
- veličina slike: 512 px
- batch: 64
- workers: 8
- seed: 42
- patience: 20

## Konačne validacijske metrike

| Precision | Recall | mAP@50 | mAP@50-95 |
| ---: | ---: | ---: | ---: |
| 0.99177 | 0.98809 | 0.99404 | 0.84537 |

`args.yaml` i `results.csv` su izvorni artefakti izvođenja. Grafikoni prikazuju konvergenciju, P/R/F1/PR krivulje i matricu zabune. Binarne težine modela nisu uključene.

Odvojeni test najboljeg modela dokumentiran je u `../../testing/supek-yolo11n/`.
