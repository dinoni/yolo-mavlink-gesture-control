# Arhitektura sustava

Projekt je podijeljen na tri sloja.

1. **ML razvoj** — HaGRID v2 anotacije se validiraju, pretvaraju u YOLO format i koriste za treniranje modela za osam gesti.
2. **Edge inferencija** — Raspberry Pi 4 koristi Sony IMX500 kameru i `network.rpk` model. Binarni model nije uključen, ali su konfiguracija i redoslijed klasa dokumentirani.
3. **Upravljanje letom** — potvrđena gesta prolazi kroz `SafetyManager V2` prije ikakve MAVLink naredbe prema ArduPilotu. Glavna integracijska skripta trenutačno je označena za SITL.

Lokalne skripte za 2D simulaciju dokumentiraju rani korak razvoja: stabilizaciju geste kroz više uzastopnih frameova, dead zone i proporcionalno upravljanje virtualnim položajem.

## Trenutačna Pi konfiguracija

- model: Sony IMX500 `network.rpk` (izostavljen iz repozitorija)
- MAVLink: lokalni SITL UDP endpoint
- sigurnosna stanja: `DISABLED`, `READY`, `TAKEOFF`, `HOLD`, `TRACKING`, `RTL_LOCKED` i `MANUAL_OVERRIDE`
- testovi: samostalni test modula `SafetyManager V2`
