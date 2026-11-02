# SRCE Supek PBS skripte

Ove PBS skripte dokumentiraju GPU trening i odvojenu testnu evaluaciju na SRCE Supek sustavu.

- `train_yolo11n.pbs` — 100-epohni YOLO11n trening
- `test_yolo11n.pbs` — evaluacija najboljih težina na testnom skupu
- `gpu_test.pbs` i `gpu_test_gpu.pbs` — provjere GPU okruženja

Skripte očekuju da su postavljene varijable `IMAGE_PATH` (Apptainer image) i `PROJECT_ROOT` (korijenska mapa projekta na Supeku). Lokalna korisnička imena i putanje nisu objavljeni.
