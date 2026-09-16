
# PEXIF

A bulk EXIF and metadata poisoner for images and videos.

Instead of deleting metadata, **pexif** poisons false metadata into your files: fake GPS coordinates, vintage camera hardware, and scrambled dates.

---

### Why poison instead of strip?

When you upload an image with completely stripped metadata, automated crawlers and platforms immediately know it was erased. 

Poisoning does the opposite:
- Your real location, hardware, and timestamps are overwritten.
- Automated scrapers and OSINT tools ingest junk poisoned data (e.g. photos placed in the Bermuda Triangle or the middle of the Pacific).
- The file looks like a normal, unmodified photo taken on an everyday device.

---

## Run Instantly (No Installation)

No need to install packages or clone this repo. If you have Python 3 on your system, run one of the commands below in your terminal.

### macOS & Linux (Bash, Zsh, Fish)
```bash
curl -sSL https://raw.githubusercontent.com/asinghtric/pexif/main/pexif.py | python3 - ~/Pictures/Decoys

# Say, you wanna spoof data to Area 51 for fun.

curl -sSL https://raw.githubusercontent.com/asinghtric/pexif/main/pexif.py | python3 - -p area51 ~/Pictures/Decoys
```

### Windows 11 (PowerShell)
```powershell
irm https://raw.githubusercontent.com/asinghtric/pexif/main/pexif.py | py - "$HOME\Pictures"
```

### Windows 11 (Command Prompt / CMD)
```cmd
curl -sSL https://raw.githubusercontent.com/asinghtric/pexif/main/pexif.py | python - "C:\Users\%USERNAME%\Pictures"
```

### With `uv`
```bash
uvx --from git+https://github.com/asinghtric/pexif pexif ~/Pictures
```

---

## Local Usage

If you prefer keeping a local script:

```bash
python3 pexif.py /path/to/your/folder
```

### Built-in Presets (`-p` / `--preset`)

| Preset | Coordinates | Camera Spoofed |
| :--- | :--- | :--- |
| `random` *(default)* | Random spot on Earth | Random vintage/classic camera & scrambled year |
| `point-nemo` | Middle of the South Pacific Ocean | Hasselblad H6D-100c |
| `area51` | Groom Lake, Nevada test site | FLIR Systems Recon V |
| `bermuda` | Bermuda Triangle | Nikonos-V Underwater |
| `mariana` | Mariana Trench (-10,994m) | DeepSea Power SeaCam |
| `north-pole` | 90°N Geographic North Pole | Kodak DC210 Plus |

### Custom Flags

You can override any specific value:

```bash
# Custom GPS coords (Lat, Lon)
python3 pexif.py --gps "51.5074,-0.1278" ./vacation

# Custom camera name
python3 pexif.py --camera "Nintendo GameBoy" ./photos

# Custom timestamp
python3 pexif.py --date "1999:12:31 23:59:59" ./photos
```

---

## How It Treats Your Files

- Images (`.jpg`, `.png`, `.webp`) are modified at binary container level. They are **NOT** opened and re-saved through an imaging library, meaning your pixel data is untouched and compression artifacts are impossible.
- Metadata is poisoned using an `ffmpeg` stream copy (`-c copy`). The audio and video streams are copied byte-for-byte without any re-encoding.
- Files are written to an isolated temporary file first and swapped only after writing succeeds, preventing half-written or corrupted files if the process is cancelled.

---

## Requirements

- **Python 3.8+** (Standard library only, no `pip` installs needed).
- **ffmpeg** *(Optional)*: Only needed if you want to poison video files. If missing, videos are skipped and images are still processed.

---

## Companion Tool

If you prefer to strip metadata completely rather than fake it, check out [bexif](https://github.com/asinghtric/bexif).

---