# YOLO MAVLink Gesture Control

Diplomski projekt sustava za prepoznavanje gesti i upravljanje dronom na rubnom uređaju (*edge AI*). Projekt povezuje pripremu podataka i treniranje YOLO modela s inferencijom na Raspberry Pi 4, MAVLink komunikacijom i sigurnosno ograničenim upravljanjem ArduPilotom.

> Status: aktivan razvoj. Trening dio i preliminarni rezultati su objavljeni; izvorni kod s Raspberry Pi-ja bit će dodan nakon pregleda konfiguracije i sigurnosne provjere.

## Što projekt obuhvaća

- pripremu HaGRID v2 anotacija za YOLO format
- validaciju anotacija, provjeru mogućeg preklapanja korisnika između skupova i analizu veličine bounding boxova
- treniranje YOLO11n modela za osam gesti
- lokalne prototipe detekcije i 2D simulacije praćenja dlana
- pripremu modela za Sony IMX500 target
- planiranu integraciju: ONNX/kvantizirana inferencija na Raspberry Pi 4, MAVLink, ArduPilot i `SafetyManager`

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

## Preliminarni rezultat treninga

Evidentirani test s YOLO11n, slikama veličine 512 px, osam klasa i GPU uređajem zabilježio je nakon dvije epohe:

| Metrika | Vrijednost |
| --- | ---: |
| Precision | 0.97689 |
| Recall | 0.96543 |
| mAP@50 | 0.98779 |
| mAP@50-95 | 0.81389 |

Ovo je kratki preliminarni test, a ne konačna usporedna evaluacija. Potpuni zapis i ograničenja nalaze se u [benchmark dokumentaciji](benchmarks/training/yolo11n-preliminary/README.md).

## Struktura

```text
training/                 Priprema podataka, validacija i trening
benchmarks/               Reproducibilni zapisi i rezultati eksperimenata
edge/sony-imx500/         Metadata za edge target; binarni model nije u repozitoriju
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
- Pi-specifične putanje, serijske portove, mrežne adrese, logove i eventualne tajne

Veliki modeli mogu se kasnije objaviti zasebno, uz verziju, checksum i upute za preuzimanje.

## Licenca

Licenca će biti odabrana prije javne objave konačne verzije.
