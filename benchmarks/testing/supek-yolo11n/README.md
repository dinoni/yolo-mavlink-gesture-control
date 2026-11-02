# SRCE Supek: test najboljeg YOLO11n modela

Najbolji model iz 100-epohnog treninga evaluiran je na odvojenom testnom skupu s 35 500 slika i 42 965 instanci.

| Precision | Recall | mAP@50 | mAP@50-95 |
| ---: | ---: | ---: | ---: |
| 0.991 | 0.990 | 0.993996 | 0.854261 |

## Metrike po klasi

| Klasa | Precision | Recall | mAP@50 | mAP@50-95 |
| --- | ---: | ---: | ---: | ---: |
| dislike | 0.9936 | 0.9962 | 0.9949 | 0.8655 |
| fist | 0.9958 | 0.9956 | 0.9950 | 0.8387 |
| like | 0.9956 | 0.9948 | 0.9949 | 0.8559 |
| no_gesture | 0.9759 | 0.9608 | 0.9884 | 0.7353 |
| one | 0.9908 | 0.9921 | 0.9944 | 0.8729 |
| palm | 0.9955 | 0.9947 | 0.9948 | 0.9158 |
| three | 0.9914 | 0.9950 | 0.9947 | 0.8654 |
| two_up | 0.9924 | 0.9940 | 0.9949 | 0.8847 |

Grafikoni, matrice zabune i uzorci predikcija su izvorni artefakti testnog izvođenja. Sirovi terminalski log i `predictions.json` nisu objavljeni jer su nepotrebno veliki za portfolio.
