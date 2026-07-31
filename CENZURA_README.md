# Automatyczna cenzura dialogów

Narzędzie rozpoznaje polską mowę, zapisuje pełną transkrypcję i raport
znalezionych przekleństw. Pliku wejściowego nigdy nie modyfikuje.

## Zalecany przebieg

1. Najpierw wykonaj samą analizę:

   `python censor_profanity.py "film.mp4"`

2. Otwórz plik CSV w podfolderze `analiza_cenzury` i sprawdź słowa oraz czasy.
3. Dopiero potem utwórz ocenzurowaną kopię:

   `python censor_profanity.py "film.mp4" --render`

Tryb domyślny `balanced` cenzuruje mocne przekleństwa w całym filmie, a łagodne
tylko w pierwszych 15 sekundach. `--mode strict` cenzuruje również wszystkie
łagodne określenia.

Wynik z dopiskiem `_CENZURA.mp4` kopiuje obraz bez ponownego kodowania i
przetwarza jedynie dźwięk. Piknięcie jest krótkie i celowo ciche.
