# SRCE Supek PBS skripte

Ove PBS skripte dokumentiraju GPU trening i odvojenu testnu evaluaciju na SRCE Supek sustavu.

- `train_yolo11n.pbs` — 100-epohni YOLO11n trening
- `test_yolo11n.pbs` — evaluacija najboljih težina na testnom skupu
- `gpu_test.pbs` i `gpu_test_gpu.pbs` — provjere GPU okruženja

Skripte očekuju da je Apptainer image postavljen kroz varijablu `IMAGE_PATH`. Putanje na Supeku su specifične za korisničko okruženje i služe kao povijesni zapis reproducibilnog procesa, a ne kao univerzalna naredba za pokretanje.
