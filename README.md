# YOLO MAVLink Gesture Control

Diplomski projekt sustava za prepoznavanje gesti i upravljanje dronom na rubnom uređaju (*edge AI*). Projekt povezuje pripremu podataka i treniranje YOLO modela s inferencijom na Raspberry Pi 4, MAVLink komunikacijom i sigurnosno ograničenim upravljanjem ArduPilotom.

> Status: aktivan razvoj. Objavljeni su trening dio, preliminarni rezultati i Pi kontrolna logika. Binarni model i hardverske konfiguracije ostaju izostavljeni.

## Što projekt obuhvaća

- pripremu HaGRID v2 anotacija za YOLO format
- validaciju anotacija, provjeru mogućeg preklapanja korisnika između skupova i analizu veličine bounding boxova
- treniranje YOLO11n modela za osam gesti
- lokalne prototipe detekcije i 2D simulacije praćenja dlana
- pripremu modela za Sony IMX500 target
- Raspberry Pi 4 kontrolnu logiku: Sony IMX500 inferenciju, MAVLink, ArduPilot i `SafetyManager V2`

## Arhitektura

```text
HaGRID v2 -> priprema/validacija podataka -> YOLO11n trening -> evaluacija
                                                        |
                                                        v
                                          edge model / Raspberry Pi 4
                                                        |
                                                        v
                                   potvrda geste + SafetyManager + MAVLink
                                                        |
                                                        v
                                                  ArduPilot drone
```

Detaljnije: [arhitektura](docs/architecture.md) i [sigurnosne napomene](docs/safety.md).

## Trening i testiranje na SRCE Supeku

Glavni model je treniran 100 epoha na SRCE Supek GPU sustavu s NVIDIA A100-SXM4-40GB grafičkom karticom. Korišteni su YOLO11n, slike od 512 px, batch 64, osam CPU jezgri, seed 42, PyTorch 2.0.0 i Ultralytics 8.4.150.

Neovisno testiranje najboljeg modela na testnom skupu s 35 500 slika i 42 965 instanci zabilježilo je:

| Metrika | Vrijednost |
| --- | ---: |
| Precision | 0.991 |
| Recall | 0.990 |
| mAP@50 | 0.993996 |
| mAP@50-95 | 0.854261 |

Potpuni artefakti treninga nalaze se u [trening benchmarku](benchmarks/training/supek-yolo11n-100e/README.md), a rezultati odvojenog testnog skupa u [test benchmarku](benchmarks/testing/supek-yolo11n/README.md).

## Raspberry Pi 4 edge benchmark

Sony IMX500 pipeline izmjeren je na Raspberry Pi 4 pri stvarnoj radnoj konfiguraciji od 640 × 480 i 15 FPS, s `network.rpk` modelom veličine 3,00 MiB.

| Metrika | Rezultat |
| --- | ---: |
| Srednji camera-to-output ciklus | 66,59 ms |
| Medijan | 66,47 ms |
| P95 | 68,89 ms |
| Propusnost | 15,02 FPS |

Mjerenje ne uključuje MAVLink ni upravljanje letjelicom. Ono pokriva puni put kamere i IMX500 izlaza, a ne izoliranu latenciju samog AI akceleratora. Detalji: [edge benchmark](benchmarks/edge/raspberry-pi-imx500-15fps/README.md).

## Struktura

```text
training/                 Priprema podataka, validacija i trening
benchmarks/               Reproducibilni zapisi i rezultati eksperimenata
training/hpc/supek/       PBS skripte za Supek GPU trening i testiranje
edge/sony-imx500/         Metadata za edge target; binarni model nije u repozitoriju
edge/raspberry-pi/        SafetyManager, SITL kontrolna logika i testovi
docs/                     Arhitektura i sigurnosne napomene
```

## Pokretanje trening dijela

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Zbog veličine i licence, HaGRID v2 slike, generirani YOLO dataset i težine modela nisu uključeni. Nakon preuzimanja podataka vidi [training/README.md](training/README.md).

## Što nije objavljeno

Repozitorij namjerno ne sadrži:

- izvorni HaGRID dataset i generirane slike/oznake
- `.pt`, `.onnx`, `.pbtxt` i druge velike binarne modele
- offline Python pakete
- binarni `network.rpk` model, lokalne logove i eventualne tajne

Veliki modeli mogu se kasnije objaviti zasebno, uz verziju, checksum i upute za preuzimanje.

## Licenca

Licenca će biti odabrana prije javne objave konačne verzije.
