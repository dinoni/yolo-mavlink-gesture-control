# Raspberry Pi 4 + Sony IMX500 edge benchmark

Ovaj reproducibilni benchmark mjeri puni camera-to-output ciklus bez MAVLinka, ArduPilota ili upravljanja letjelicom. Izveden je skriptom `edge/raspberry-pi/benchmark_imx500.py`.

## Konfiguracija

- uređaj: Raspberry Pi 4 (4 CPU jezgre)
- kamera: Sony IMX500
- model: `network.rpk`, 3,00 MiB
- izlaz kamere: 640 × 480 RGB888
- konfigurirani frame rate: 15 FPS
- warm-up: 30 frameova
- mjerenje: 300 frameova
- OS: Linux 6.18.50+rpt-rpi-v8-aarch64

## Rezultati

| Metrika | Rezultat |
| --- | ---: |
| Srednji pipeline ciklus | 66,59 ms |
| Medijan | 66,47 ms |
| P95 | 68,89 ms |
| Minimum | 62,36 ms |
| Maksimum | 71,00 ms |
| Promatrana propusnost | 15,02 FPS |

Rezultat potvrđuje da pipeline održava konfiguriranih 15 FPS. Vrijednosti su end-to-end mjerenje od preuzimanja framea do čitanja IMX500 izlaza i uključuju rad kamere/aplikacije. Ne predstavljaju izoliranu latenciju IMX500 akceleratora niti ukupnu latenciju kontrole leta.

## Ponovno pokretanje

```bash
python benchmark_imx500.py \
  --model /home/dino/imx500_output/network.rpk \
  --frames 300 \
  --warmup 30 \
  --fps 15 \
  --csv imx500_benchmark.csv
```

Za usporedbu većeg zadanog frame ratea može se ponoviti s `--fps 30`, ako kamera i model to podržavaju.
