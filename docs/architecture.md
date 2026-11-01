# Arhitektura sustava

Projekt je podijeljen na tri sloja.

1. **ML razvoj** — HaGRID v2 anotacije se validiraju, pretvaraju u YOLO format i koriste za treniranje modela za osam gesti.
2. **Edge inferencija** — model se priprema za ciljni uređaj. Dio s Raspberry Pi 4 i kvantiziranim modelom bit će dodan nakon pregleda izvornog koda.
3. **Upravljanje letom** — potvrđena gesta prolazi kroz sigurnosnu logiku prije ikakve MAVLink naredbe prema ArduPilotu.

Lokalne skripte za 2D simulaciju dokumentiraju rani korak razvoja: stabilizaciju geste kroz više uzastopnih frameova, dead zone i proporcionalno upravljanje virtualnim položajem.

## Plan nadopune

Nakon uvoza koda s Pi-ja, ova dokumentacija će navesti stvarni tok podataka, format modela, postavke inferencije, MAVLink transport, dozvoljene naredbe i sigurnosna stanja.
