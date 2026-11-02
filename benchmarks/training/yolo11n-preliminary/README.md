# Arhiva: lokalni YOLO11n probni trening

Ova mapa čuva kratki lokalni probni eksperiment s modelom `yolo11n.pt`. Nije glavni rezultat projekta; za stvarni 100-epohni Supek trening vidi `../supek-yolo11n-100e/`.

## Konfiguracija

- broj klasa: 8
- veličina slike: 512 px
- batch: 8
- uređaj: GPU `0`
- epohe: 2
- seed: 0
- determinističko izvođenje: uključeno

`results.csv` je izvorni zapis metrika po epohi, a `args.yaml` je originalna konfiguracija izvođenja. Naziv izvorne mape sadržavao je `gesture_yolo26n_test`, no konfiguracija potvrđuje da je korišten `yolo11n.pt`; mapa je ovdje namjerno preimenovana radi jasnijeg portfolija.

## Ograničenja

Rezultat nije predstavljen kao završna evaluacija: trening je trajao dvije epohe, a u ovom zapisu nisu potvrđeni točan GPU model, verzije paketa, potrošnja memorije ni end-to-end latencija. Te će se vrijednosti nadopuniti ponovljenim, dokumentiranim mjerenjem.
