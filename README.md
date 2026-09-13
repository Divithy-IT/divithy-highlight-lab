# Divithy Highlight Lab

[![Checks](https://github.com/Divithy-IT/divithy-highlight-lab/actions/workflows/checks.yml/badge.svg)](https://github.com/Divithy-IT/divithy-highlight-lab/actions/workflows/checks.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-local-007808?logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-39e7ff)

Lokalny warsztat do przeglądania nagrań z gier, wyszukiwania dynamicznych
fragmentów i renderowania kompilacji oraz pionowych Shortsów. Materiały
źródłowe są tylko odczytywane, a wyniki trafiają do osobnego katalogu.

![Schemat działania](docs/workflow.svg)

## Czym to jest, a czym nie jest

To **pierwszy etap** dwuczęściowego łańcucha produkcyjnego kanału Divithyツ.
Highlight Lab odpowiada za produkcję materiału: analizę nagrań, wybór akcji i
render. Za drugi etap — harmonogram, metadane i wysyłkę na YouTube — odpowiada
osobne narzędzie,
[divithy-youtube-publisher](https://github.com/Divithy-IT/divithy-youtube-publisher).
Te dwa repozytoria nie dublują się; stykają się na katalogu gotowych paczek.

To repozytorium jest **publicznym wycinkiem** większego, prywatnego środowiska
roboczego kanału. Zawiera rdzeń narzędzi w wersji nadającej się do uruchomienia
u kogokolwiek. Nie zawiera prywatnych ścieżek, materiałów, transkrypcji ani
narzędzi operacyjnych pisanych pod jeden konkretny kanał. Wersja robocza jest
rozwijana dalej i rozjeżdża się z tą publiczną — jeżeli zależy Ci na
konkretnej poprawce, załóż issue.

## Możliwości

- raport czasu, rozdzielczości, FPS i rozmiaru wszystkich nagrań;
- punktowanie ruchu i zmian obrazu przy pomocy OpenCV;
- wybór fragmentów z kontekstem przed akcją i po niej;
- kompilacje 16:9 z intro i outro przez FFmpeg;
- Shortsy 9:16 z pełnym kadrem gry na rozmytym tle;
- normalizacja głośności i limiter chroniący przed nagłymi krzykami;
- opcjonalna transkrypcja i wypikanie przekleństw przez faster-whisper;
- kodowanie programowe `libx264` albo sprzętowe `h264_nvenc` na NVIDIA.

## Szybki start na Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python inventory_videos.py "D:\Nagrania" --output inventory.json
python analyze_package.py --help
```

Naturalniejsze, dłuższe sceny można uzyskać przez ustawienie celu 50 sekund,
większego kontekstu przed kulminacją oraz adaptacyjnego zakończenia:

```powershell
python analyze_package.py "D:\Nagrania" "C:\Wyniki\Film" `
  --segment-seconds 50 --lead-seconds 14 `
  --adaptive-end-window-seconds 2
```

W tym wariancie narzędzie szuka spokojniejszego punktu zakończenia mniej więcej
między 46. a 52. sekundą, ograniczając urwane dialogi i akcje bez nadmiernego
wydłużania całego odcinka.

FFmpeg jest dostarczany przez `imageio-ffmpeg`, więc osobna instalacja zwykle
nie jest potrzebna. Pierwsze użycie transkrypcji pobiera wybrany model i wymaga
internetu; same nagrania nie są automatycznie wysyłane do zewnętrznej usługi.

## Typowy przebieg

1. Uruchom inwentaryzację katalogu i sprawdź raport.
2. Przeanalizuj paczkę, aby znaleźć kandydatów na najlepsze akcje.
3. Zweryfikuj proponowane zakresy przed renderem.
4. Zbuduj film główny i trzy Shortsy.
5. Opcjonalnie przeanalizuj dialogi i utwórz ocenzurowaną kopię.

Najważniejsze polecenia:

```powershell
python inventory_videos.py --help
python analyze_package.py --help
python render_shorts.py --help
python censor_profanity.py --help
```

Dla cenzury dostępne są też `Analizuj_przeklenstwa.bat` i
`Utworz_wersje_ocenzurowana.bat`. Szczegóły opisuje
[CENZURA_README.md](CENZURA_README.md).

## Prywatność i bezpieczeństwo

Wideo, audio, transkrypcje, raporty zawierające prywatne ścieżki oraz katalogi
wynikowe są ignorowane przez Git. Nie dodawaj prawdziwych materiałów do
zgłoszeń. Zasady raportowania opisuje [SECURITY.md](SECURITY.md).

## Rozwój

```powershell
python -m compileall -q .
python inventory_videos.py --help
python analyze_package.py --help
python render_shorts.py --help
python censor_profanity.py --help
```

Każdy push i pull request przechodzi te kontrole automatycznie. Informacje o
wersjach są w [CHANGELOG.md](CHANGELOG.md), a zasady zmian w
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licencja

[MIT](LICENSE) © 2026 Michał Lemanczyk.

---

## English

A local Python toolkit for turning long gaming recordings into publishable
material: it inventories footage, scores visual activity, selects highlight
candidates and renders both 16:9 compilations and 9:16 Shorts. Source
recordings are read-only and are never uploaded anywhere automatically.

### What this is, and what it is not

This is the **first stage** of a two-part production chain for the Divithyツ
channel. Highlight Lab produces the material; scheduling, metadata and the
actual YouTube upload are handled by a separate tool,
[divithy-youtube-publisher](https://github.com/Divithy-IT/divithy-youtube-publisher).
The two repositories do not overlap — they meet at a directory of finished
content packages.

This repository is a **public excerpt** of a larger private working
environment. It contains the core tooling in a form anyone can run, without
private paths, footage, transcripts or channel-specific operational scripts.
The working version keeps moving and drifts from this one; if you need a
specific fix backported, open an issue.

### Features

- a report of duration, resolution, FPS and size for every recording;
- motion and scene-change scoring with OpenCV;
- segment selection with lead-in and follow-through context;
- 16:9 compilations with intro and outro via FFmpeg;
- 9:16 Shorts keeping the full gameplay frame over a blurred background;
- loudness normalization with a limiter that tames sudden shouting;
- optional transcription and profanity bleeping via faster-whisper;
- software `libx264` or hardware `h264_nvenc` encoding on NVIDIA.

### Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python inventory_videos.py "D:\Recordings" --output inventory.json
python analyze_package.py --help
```

For longer, more natural scenes, target 50 seconds with extra lead-in and let
the tool pick a calmer ending point:

```powershell
python analyze_package.py "D:\Recordings" "C:\Output\Episode" `
  --segment-seconds 50 --lead-seconds 14 `
  --adaptive-end-window-seconds 2
```

FFmpeg ships with `imageio-ffmpeg`, so a separate install is usually
unnecessary. The first transcription run downloads the selected model and needs
an internet connection; the recordings themselves stay local.

### Workflow

Inventory the directory, analyse the package to find highlight candidates,
review the proposed ranges, render the main episode plus three Shorts, and
optionally produce a censored copy. Every command supports `--help`.

Issues and pull requests in English are welcome. Licensed under
[MIT](LICENSE) © 2026 Michał Lemanczyk.
