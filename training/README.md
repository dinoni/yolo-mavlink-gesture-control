# Trening i priprema podataka

Ova mapa čuva postojeće skripte projekta, prenesene bez izmjene njihove logike:

- `src/prepare_dataset.py` — pretvara odabrane HaGRID v2 anotacije u YOLO dataset
- `src/validate_hagrid.py` — provjerava strukturu anotacija, bounding boxove i moguće preklapanje korisnika među službenim splitovima
- `src/analyze_bboxes.py` — analizira raspodjelu veličina bounding boxova
- `src/train_yolo.py` — pokreće YOLO trening
- `src/visualize_yolo.py` — stvara pregled uzoraka s YOLO oznakama
- `src/webcam_test.py`, `src/drone_hand_follow.py`, `src/drone_gesture_control.py` — lokalni prototipi detekcije i 2D simulacije

Odabrane klase su: `dislike`, `fist`, `like`, `no_gesture`, `one`, `palm`, `three` i `two_up`.

## Podaci

Preuzmi HaGRID v2 prema njegovim službenim uvjetima korištenja. Očekivana lokalna struktura za postojeće skripte je:

```text
training/data/raw/hagrid/
  annotations/annotations/{train,val,test}/
  images_512/<gesture>/
```

Skripta `prepare_dataset.py` stvara `training/data/processed/yolo_gestures/`, koji je namjerno izostavljen iz Git-a.

## Reproducibilnost

Prije konačne objave ćemo parametrizirati putanje i parametre treninga te zaključati provjerene verzije ovisnosti. Trenutačne skripte čuvaju stvarni razvojni postupak diplomskog projekta.
