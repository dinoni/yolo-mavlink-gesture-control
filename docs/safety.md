# Sigurnosne napomene

Ovaj projekt nije spreman za nekontrolirani stvarni let. Sva testiranja upravljanja letom trebaju se najprije provesti u SITL-u i zatim u sigurnom, zakonito odobrenom okruženju uz odgovornog pilota.

## Dosad zabilježeno ponašanje

Prema spremljenim SITL logovima, postojeća Pi implementacija ima sljedeću zamišljenu logiku:

- RC5 prekidač gasi AI upravljanje.
- Kod ručnog overridea sustav traži prijelaz iz `GUIDED` u `LOITER` i čeka potvrdu ArduPilot heartbeat porukom.
- Nakon overridea, ponovna autorizacija AI-a tijekom leta je blokirana do slijetanja, disarma i reseta.

Ove stavke bit će provjerene prema stvarnom kodu `SafetyManager` prije nego što se opišu kao konačno implementirano ponašanje.

## Otvorene provjere

- ponašanje pri gubitku MAVLink veze
- ponašanje LOITER moda pri položaju gasa koji nije neutralan
- ograničenja brzine, visine i dopuštenih komandi
- ponovljeni SITL testovi i dokumentirani rezultati

Niti jedan model niti aplikacijski kod ne smije samostalno armati letjelicu ili zaobilaziti pilotsku kontrolu.
