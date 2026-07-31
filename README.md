# Divithy Highlight Lab

Lokalny zestaw narzędzi do analizy nagrań z gier, wybierania dynamicznych
fragmentów oraz tworzenia kompilacji i pionowych shortsów. Materiały źródłowe
są wyłącznie odczytywane — wyniki trafiają do osobnego katalogu.

## Możliwości

- inwentaryzacja nagrań: czas, rozdzielczość, FPS i rozmiar;
- punktowanie ruchu i zmian obrazu przy pomocy OpenCV;
- wybieranie fragmentów z dodatkowym kontekstem przed akcją;
- montaż kompilacji z intro/outro przez FFmpeg;
- pionowe shortsy 9:16 z pełnym kadrem gry i rozmytym tłem;
- normalizacja głośności i limiter chroniący przed nagłymi krzykami;
- opcjonalna transkrypcja i wypikanie przekleństw przez faster-whisper.

## Instalacja

Wymagany jest Python 3.11 lub nowszy. W katalogu projektu:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

FFmpeg jest dostarczany przez `imageio-ffmpeg`, dlatego osobna instalacja
zwykle nie jest potrzebna. Kodowanie `h264_nvenc` wymaga zgodnej karty NVIDIA;
na pozostałych komputerach można wybrać `libx264`.

## Najważniejsze polecenia

```powershell
python inventory_videos.py "D:\Nagrania" --output inventory.json
python analyze_package.py --help
python render_shorts.py --help
python censor_profanity.py --help
```

Pliki wideo, transkrypcje, raporty z prywatnymi ścieżkami i środowisko `.venv`
są ignorowane przez Git.

## Prywatność

Analiza obrazu i montaż odbywają się lokalnie. Pobrania modeli transkrypcji
wymagają internetu, ale nagrania nie są automatycznie wysyłane do usług
zewnętrznych.

