import os
import sys
import zlib
import random
import shutil
import struct
import tempfile
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict

# Enable colors
if sys.platform == "win32":
    os.system("")

C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_DIM    = "\033[2m"
C_MAGENTA= "\033[35m"
C_CYAN   = "\033[36m"
C_GREEN  = "\033[32m"
C_YELLOW = "\033[33m"
C_RED    = "\033[31m"


PRESETS = {
    "point-nemo": {
        "name": "Point Nemo (Oceanic Pole of Inaccessibility)",
        "lat": -48.8767, "lon": -123.3933,
        "make": "Hasselblad", "model": "H6D-100c",
        "software": "Phocus 3.6",
    },
    "area51": {
        "name": "Area 51 / Groom Lake, NV",
        "lat": 37.2431, "lon": -115.7930,
        "make": "FLIR Systems", "model": "Recon V Ultra-Long Range",
        "software": "MilSpec ThermalOS 4.1",
    },
    "bermuda": {
        "name": "Bermuda Triangle",
        "lat": 25.0000, "lon": -71.0000,
        "make": "Nikon", "model": "Nikonos-V Underwater",
        "software": "Film Scan v1.0",
    },
    "north-pole": {
        "name": "North Pole (90°N)",
        "lat": 90.0000, "lon": 0.0000,
        "make": "Kodak", "model": "DC210 Plus",
        "software": "Kodak Picture Easy 3.1",
    },
    "mariana": {
        "name": "Mariana Trench Challenger Deep",
        "lat": 11.3493, "lon": 142.1996,
        "make": "DeepSea Power & Light", "model": "SeaCam 6000",
        "software": "Submersible Capture 2.0",
    }
}

DEC_CAM = [
    ("Nintendo", "Game Boy Camera"),
    ("Sony", "Cyber-shot DSC-P10"),
    ("Apple", "QuickTake 100"),
    ("Canon", "EOS-1D X Mark III"),
    ("Hasselblad", "500C/M Digital Back"),
    ("Kodak", "DC290 Zoom"),
    ("Fujifilm", "FinePix S5 Pro"),
    ("Nokia", "808 PureView"),
]

DEC_SW = [
    "Adobe Photoshop 4.0 (Macintosh)",
    "GIMP 2.8.22",
    "Paint Shop Pro 7.04",
    "Windows Movie Maker 2.1",
    "Picasa 3.0",
    "Apple Aperture 1.5",
]

def gen_poison(pres_k=None, cgps=None, ccam=None, cdate=None):
    if pres_k and pres_k in PRESETS:
        base = PRESETS[pres_k]
        lat, lon = base["lat"], base["lon"]
        make, model = base["make"], base["model"]
        software = base["software"]
    else:
        make, model = random.choice(DEC_CAM)
        software = random.choice(DEC_SW)
        # random coords
        lat = round(random.uniform(-75.0, 75.0), 4)
        lon = round(random.uniform(-170.0, 170.0), 4)

    if cgps:
        lat, lon = cgps
    if ccam:
        parts = ccam.split(" ", 1)
        make = parts[0]
        model = parts[1] if len(parts) > 1 else "Unknown"

    if cdate:
        dt_str = cdate
    else:
        
        y = random.randint(1999, 2021)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        hh = random.randint(0, 23)
        mm = random.randint(0, 59)
        ss = random.randint(0, 59)
        dt_str = f"{y:04d}:{m:02d}:{d:02d} {hh:02d}:{mm:02d}:{ss:02d}"

    return {
        "lat": lat,
        "lon": lon,
        "make": make,
        "model": model,
        "software": software,
        "date": dt_str
    }



def degdms(deg_float):
    
    val = abs(deg_float)
    d = int(val)
    m = int((val - d) * 60)
    s = int(round((val - d - m / 60.0) * 3600.0 * 100.0))
    return (d, 1), (m, 1), (s, 100)

def build_expl(poison):
    
    tiff_header = b"II\x2a\x00\x08\x00\x00\x00"
    
    str_make = poison["make"].encode("ascii", "replace") + b"\x00"
    str_model = poison["model"].encode("ascii", "replace") + b"\x00"
    str_soft = poison["software"].encode("ascii", "replace") + b"\x00"
    str_date = poison["date"].encode("ascii", "replace") + b"\x00"

    lat_dms = degdms(poison["lat"])
    lon_dms = degdms(poison["lon"])
    lat_ref = b"N\x00" if poison["lat"] >= 0 else b"S\x00"
    lon_ref = b"E\x00" if poison["lon"] >= 0 else b"W\x00"

    lat_byte = struct.pack("<IIIIII", lat_dms[0][0], lat_dms[0][1], lat_dms[1][0], lat_dms[1][1], lat_dms[2][0], lat_dms[2][1])
    lon_byte = struct.pack("<IIIIII", lon_dms[0][0], lon_dms[0][1], lon_dms[1][0], lon_dms[1][1], lon_dms[2][0], lon_dms[2][1])

    ifd0_ds = 8 + 2 + (5 * 12) + 4

    ifd0_data = bytearray()
    
    def pack_entry(tag, dtype, count, data_bytes):
        nonlocal ifd0_data
        if len(data_bytes) <= 4:
            vfield = data_bytes.ljust(4, b"\x00")
        else:
            offset = ifd0_ds + len(ifd0_data)
            vfield = struct.pack("<I", offset)
            ifd0_data.extend(data_bytes)
        return struct.pack("<HHI", tag, dtype, count) + vfield

    e_make  = pack_entry(0x010F, 2, len(str_make), str_make)
    e_model = pack_entry(0x0110, 2, len(str_model), str_model)
    e_soft  = pack_entry(0x0131, 2, len(str_soft), str_soft)
    e_date  = pack_entry(0x0132, 2, len(str_date), str_date)

    gi_off = ifd0_ds + len(ifd0_data)
    if gi_off % 2 != 0:
        ifd0_data.extend(b"\x00")
        gi_off += 1

    gps_ptr = pack_entry(0x8825, 4, 1, struct.pack("<I", gi_off))

    ifd0_bytes = (
        struct.pack("<H", 5) +
        e_make + e_model + e_soft + e_date + gps_ptr +
        b"\x00\x00\x00\x00" +  # Next IFD = 0
        ifd0_data
    )


    gpsd_st = gi_off + 2 + (5 * 12) + 4
    gpsd = bytearray()

    def gpsb(tag, dtype, count, data_bytes):
        nonlocal gpsd
        if len(data_bytes) <= 4:
            vfield = data_bytes.ljust(4, b"\x00")
        else:
            offset = gpsd_st + len(gpsd)
            vfield = struct.pack("<I", offset)
            gpsd.extend(data_bytes)
        return struct.pack("<HHI", tag, dtype, count) + vfield

    g_ver  = gpsb(0x0000, 1, 4, b"\x02\x03\x00\x00")
    g_lref = gpsb(0x0001, 2, 2, lat_ref)
    g_lat  = gpsb(0x0002, 5, 3, lat_byte)
    g_loref= gpsb(0x0003, 2, 2, lon_ref)
    g_lon  = gpsb(0x0004, 5, 3, lon_byte)

    gps_ifd_bytes = (
        struct.pack("<H", 5) +
        g_ver + g_lref + g_lat + g_loref + g_lon +
        b"\x00\x00\x00\x00" +
        gpsd
    )

    return tiff_header + ifd0_bytes + gps_ifd_bytes


def poison_jpeg(filepath, poison):
    
    with open(filepath, "rb") as f:
        data = f.read()

    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return False


    tiff_bytes = build_expl(poison)
    app1_payload = b"Exif\x00\x00" + tiff_bytes
    app1_marker = b"\xff\xe1" + struct.pack(">H", len(app1_payload) + 2) + app1_payload

    out = bytearray(b"\xff\xd8")
    out.extend(app1_marker)

    idx = 2
    while idx < len(data):
        if data[idx] != 0xFF:
            out.extend(data[idx:])
            break
        marker = data[idx + 1]
        if marker == 0xDA:  # SOS
            out.extend(data[idx:])
            break
        if marker in (0xD8, 0xD9):
            idx += 2
            continue

        length = struct.unpack(">H", data[idx + 2 : idx + 4])[0]
        
        if marker not in (0xE1, 0xED):
            out.extend(data[idx : idx + 2 + length])
        idx += 2 + length

    atw(filepath, out)
    return True


def poison_png(filepath, poison):
    
    with open(filepath, "rb") as f:
        data = f.read()

    sig = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(sig):
        return False

    tiff_bytes = build_expl(poison)

    def make_chunk(ctype, cdata):
        crc = zlib.crc32(ctype + cdata) & 0xFFFFFFFF
        return struct.pack(">I", len(cdata)) + ctype + cdata + struct.pack(">I", crc)

    exif_chunk = make_chunk(b"eXIf", tiff_bytes)
    soft_chunk = make_chunk(b"tEXt", b"Software\x00" + poison["software"].encode("latin1", "replace"))

    out = bytearray(sig)
    idx = 8
    injected = False

    while idx < len(data):
        if idx + 8 > len(data):
            break
        length = struct.unpack(">I", data[idx : idx + 4])[0]
        ctype = data[idx + 4 : idx + 8]
        total_len = 12 + length
        
        if ctype in (b"eXIf", b"tEXt", b"zTXt", b"iTXt"):
            idx += total_len
            continue

        out.extend(data[idx : idx + total_len])
        idx += total_len

        if ctype == b"IHDR" and not injected:
            out.extend(exif_chunk)
            out.extend(soft_chunk)
            injected = True

    atw(filepath, out)
    return True


def poison_webp(filepath, poison):
    
    with open(filepath, "rb") as f:
        data = f.read()

    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return False

    tiff_bytes = build_expl(poison)

    idx = 12
    chunks = []
    while idx < len(data):
        if idx + 8 > len(data):
            break
        fourcc = data[idx : idx + 4]
        size = struct.unpack("<I", data[idx + 4 : idx + 8])[0]
        pad = size % 2
        dchunk = data[idx + 8 : idx + 8 + size]

        if fourcc != b"EXIF":
            chunks.append((fourcc, dchunk, pad))
        idx += 8 + size + pad

    # append pexif
    chunks.append((b"EXIF", tiff_bytes, len(tiff_bytes) % 2))

    body = bytearray()
    for fourcc, cdata, pad in chunks:
        body.extend(fourcc)
        body.extend(struct.pack("<I", len(cdata)))
        body.extend(cdata)
        if pad:
            body.extend(b"\x00")

    header = b"RIFF" + struct.pack("<I", len(body) + 4) + b"WEBP"
    atw(filepath, header + body)
    return True


def poison_video(filepath, poison):
    
    if not shutil.which("ffmpeg"):
        return False, "ffmpeg not found"

    tmp_out = filepath.with_name(f".poison_{filepath.name}")
    gps_str = f"{poison['lat']:+.4f}{poison['lon']:+.4f}/"

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(filepath),
        "-c", "copy",
        "-metadata", f"title=Surveillance Feed Decoy",
        "-metadata", f"artist={poison['make']} {poison['model']}",
        "-metadata", f"comment={poison['software']}",
        "-metadata", f"date={poison['date'].replace(':', '-')}",
        "-metadata", f"location={gps_str}",
        str(tmp_out)
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if res.returncode == 0 and tmp_out.exists():
            shutil.move(str(tmp_out), str(filepath))
            return True, None
        else:
            if tmp_out.exists():
                tmp_out.unlink()
            return False, "ffmpeg injection failed"
    except Exception as e:
        if tmp_out.exists():
            tmp_out.unlink()
        return False, str(e)


def atw(filepath, byte_content):
    dir_name = filepath.parent
    with tempfile.NamedTemporaryFile(delete=False, dir=dir_name) as tf:
        tf.write(byte_content)
        temp_name = tf.name
    shutil.move(temp_name, str(filepath))


def progrender(done, total, current_filename):
    term_width = shutil.get_terminal_size((80, 20)).columns
    percent = (done / total) if total > 0 else 1.0
    bar_width = 24
    filled = int(bar_width * percent)
    bar = f"{C_MAGENTA}{'█' * filled}{C_DIM}{'░' * (bar_width - filled)}{C_RESET}"

    prefix = f"[{bar}] {int(percent * 100):>3}% ({done}/{total}) "
    remaining = term_width - len(prefix) - 2

    if remaining > 10:
        clean_name = current_filename if len(current_filename) <= remaining else f"...{current_filename[-(remaining - 3):]}"
    else:
        clean_name = ""

    sys.stdout.write(f"\r{prefix}{C_CYAN}{clean_name}{C_RESET}")
    sys.stdout.flush()


SUPP_IMG = {".jpg", ".jpeg", ".png", ".webp"}
SUPP_VID = {".mp4", ".mov", ".m4v", ".mkv"}

def main():
    parser = argparse.ArgumentParser(
        description="Poison EXIF metadata across images and videos with realistic decoy data."
    )
    parser.add_argument("target", help="Directory or file path to poison")
    parser.add_argument(
        "-p", "--preset",
        choices=["random", "point-nemo", "area51", "bermuda", "north-pole", "mariana"],
        default="random",
        help="Decoy location preset (default: random)"
    )
    parser.add_argument("--gps", help="Custom GPS coords as 'lat,lon' (e.g. '37.7749,-122.4194')")
    parser.add_argument("--camera", help="Custom camera hardware (e.g. 'Nintendo GameBoy')")
    parser.add_argument("--date", help="Custom date as 'YYYY:MM:DD HH:MM:SS'")
    parser.add_argument("-r", "--recursive", action="store_true", default=True, help="Scan directories recursively (default: on)")

    args = parser.parse_args()

    target_path = Path(args.target).expanduser().resolve()
    if not target_path.exists():
        sys.stderr.write(f"{C_RED}Error: Path '{target_path}' does not exist.{C_RESET}\n")
        sys.exit(1)

    cgps = None
    if args.gps:
        try:
            parts = [float(x.strip()) for x in args.gps.split(",")]
            cgps = (parts[0], parts[1])
        except Exception:
            sys.stderr.write(f"{C_RED}Error: GPS must be format 'lat,lon' (e.g. 51.5074,-0.1278){C_RESET}\n")
            sys.exit(1)

    if target_path.is_file():
        files = [target_path]
    else:
        pattern = "**/*" if args.recursive else "*"
        files = [p for p in target_path.glob(pattern) if p.is_file()]

    valid_files = [f for f in files if f.suffix.lower() in (SUPP_IMG | SUPP_VID)]

    if not valid_files:
        print(f"{C_YELLOW}No supported image or video files found in {target_path}{C_RESET}")
        sys.exit(0)

    preset_name = PRESETS[args.preset]["name"] if args.preset in PRESETS else "Dynamic Randomized Noise"
    print(f"\n{C_BOLD}{C_MAGENTA}pexif{C_RESET} {C_DIM}: poisoning decoy metadata across {len(valid_files)} file(s){C_RESET}")
    print(f"  {C_DIM}Preset Profile: {C_CYAN}{preset_name}{C_RESET}\n")

    pois_cnt = 0
    skipped_count = 0
    pll = set()
    pld = set()
    warnings = []
    has_ffmpeg = bool(shutil.which("ffmpeg"))

    for i, file_path in enumerate(valid_files, start=1):
        progrender(i, len(valid_files), file_path.name)
        ext = file_path.suffix.lower()

        # poison gen
        p_data = gen_poison(
            pres_k=args.preset if args.preset != "random" else None,
            cgps=cgps,
            ccam=args.camera,
            cdate=args.date
        )

        ok = False
        try:
            if ext in {".jpg", ".jpeg"}:
                ok = poison_jpeg(file_path, p_data)
            elif ext == ".png":
                ok = poison_png(file_path, p_data)
            elif ext == ".webp":
                ok = poison_webp(file_path, p_data)
            elif ext in SUPP_VID:
                if not has_ffmpeg:
                    warnings.append(f"{file_path.name}: skipped (ffmpeg required for video)")
                else:
                    ok, err = poison_video(file_path, p_data)
                    if err:
                        warnings.append(f"{file_path.name}: {err}")

            if ok:
                pois_cnt += 1
                pll.add(f"{p_data['lat']:.2f}, {p_data['lon']:.2f}")
                pld.add(f"{p_data['make']} {p_data['model']}")
            else:
                skipped_count += 1

        except Exception as e:
            warnings.append(f"{file_path.name}: {e}")
            skipped_count += 1

    # Clear 
    sys.stdout.write("\r" + " " * shutil.get_terminal_size((80, 20)).columns + "\r")
    sys.stdout.flush()

    # summary
    print(f"{C_BOLD}{C_GREEN}✓ Complete{C_RESET}")
    print(f"  Files scanned : {len(valid_files)}")
    print(f"  Poisoned      : {pois_cnt}")
    print(f"  Skipped       : {skipped_count}")

    if pois_cnt > 0:
        print(f"\n{C_BOLD}Decoy Signatures Injected:{C_RESET}")
        loc_sample = list(pll)[:3]
        dev_sample = list(pld)[:3]
        print(f"  • GPS Decoys   : {', '.join(loc_sample)}{' (+more)' if len(pll) > 3 else ''}")
        print(f"  • Hardware     : {', '.join(dev_sample)}{' (+more)' if len(pld) > 3 else ''}")
        print(f"  • Timestamps   : Scrambled across decoy years")

    if warnings:
        print(f"\n{C_YELLOW}Warnings:{C_RESET}")
        for w in warnings[:5]:
            print(f"  {C_DIM}! {w}{C_RESET}")
    print("")
main()