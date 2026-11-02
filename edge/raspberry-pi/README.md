# Raspberry Pi 4: kontrola i sigurnost

Ova mapa čuva postojeći kod s Raspberry Pi-ja, bez izmjena njegove upravljačke logike.

- `gesture_control_v5_4_2_rtl_landing.py` — integracija Sony IMX500 kamere, prepoznavanja gesti, MAVLinka i ArduPilota; označena je za SITL.
- `safety_manager_v2.py` — state-machine za autorizaciju, polijetanje, praćenje, ručni override i RTL zaključavanje.
- `test_safety_v2.py` — samostalni test sigurnosnog modula bez kamere, MAVLink veze ili ArduPilota.
- `benchmark_imx500.py` — samostalno mjeri Sony IMX500 camera-to-output pipeline bez MAVLinka i upravljanja letjelicom.

## Test sigurnosnog modula

Iz ove mape može se pokrenuti:

```bash
python test_safety_v2.py
```

Glavnu kontrolnu skriptu ne pokretati na stvarnoj letjelici iz ovog repozitorija. Zahtijeva Sony IMX500 `network.rpk` model, Pi-specifične pakete (`picamera2`) i zasebno provjerenu ArduPilot/SITL konfiguraciju.

Prije pokretanja integracijske skripte postavi putanju modela izvan Git-a:

```bash
export IMX500_MODEL_PATH="/putanja/do/network.rpk"
export MAVLINK_ADDRESS="udpin:0.0.0.0:14550"
```

## IMX500 benchmark

Zaustavi glavnu gesture-control skriptu prije pokretanja, zatim na Pi-ju izvrši:

```bash
python benchmark_imx500.py --model /putanja/do/network.rpk --frames 300 --warmup 30 --fps 15 --csv imx500_benchmark.csv
```

Skripta ne koristi MAVLink. Izmjeri prosjek, medijan, P95 i FPS za puni put od preuzimanja framea do IMX500 izlaza; to nije izolirana latencija samog AI akceleratora.

## Model i konfiguracija

`network.rpk` nije uključen jer je binarni artefakt. MAVLink endpoint je namjerno zadržan kao lokalni SITL UDP endpoint; stvarne serijske ili mrežne postavke treba čuvati izvan Git-a.
