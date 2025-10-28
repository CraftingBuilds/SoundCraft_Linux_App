#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smith Equivalence Law — Cosmic → Audible (OWM)
Sidereal + Galactic Integration • Pyto iOS Edition • v6.1

- Added: Galactic Year cycle
- Added: ENTER EXACT prompt for Lat/Lon input
"""

import sys, os, math, datetime as dt, wave, struct

def say(msg): print(msg, flush=True)

try:
    import numpy as np, requests
except Exception:
    sys.exit("Install deps: pip install numpy requests")

# --- constants ----------------------------------------------------
F_MIN, F_MAX = 55.0, 1760.0
RA_GC_DEG, DEC_GC_DEG = 266.404988, -29.007807
RA_GC_H = RA_GC_DEG / 15.0
SAMPLE_RATE = 44100
DURATION = 60.0  # seconds

CYCLES = {
    "1": ("Sidereal Day", 86164.091, 11605.8),
    "2": ("Synodic Month", 2551443, 391.935),
    "3": ("Tropical Year", 31556925.2, 31.689),
    "4": ("Nodal Cycle (18.6 y)", 586953600, 1.704),
    "5": ("Precession (25,772 y)", 813532800000, 0.001229),
    "6": ("Galactic Year (~225M y)", 7.1e15, 1.41e-13),
}

# --- astronomy ----------------------------------------------------
def jd_from_datetime(t_utc):
    y, m = t_utc.year, t_utc.month
    d = t_utc.day + (t_utc.hour + t_utc.minute/60 + t_utc.second/3600)/24
    if m <= 2: y -= 1; m += 12
    A = y // 100; B = 2 - A + A // 4
    return int(365.25*(y+4716)) + int(30.6001*(m+1)) + d + B - 1524.5

def gmst_deg(jd): return (280.46061837 + 360.98564736629*(jd - 2451545.0)) % 360
def lst_hours(jd, lon): return (gmst_deg(jd) + lon) % 360 / 15
def hour_angle(lst, ra): return (lst - ra) % 24

def altitude_deg(lat, dec, H):
    φ, δ, H = map(math.radians, [lat, dec, H*15])
    s = math.sin(φ)*math.sin(δ)+math.cos(φ)*math.cos(δ)*math.cos(H)
    return math.degrees(math.asin(max(-1,min(1,s))))

def owm_to_audible(cosmic_hz, f0_hz, fmin=F_MIN, fmax=F_MAX):
    if f0_hz <= 0 or cosmic_hz <= 0: return 0.0
    f = cosmic_hz * (220.0 / f0_hz)
    if f < fmin:
        k = max(0, int(math.ceil(math.log(fmin/f, 2))))
        f *= (2.0 ** k)
    elif f > fmax:
        k = max(0, int(math.ceil(math.log(f/fmax, 2))))
        f /= (2.0 ** k)
    return f

# --- helpers -------------------------------------------------------
def ask(q, caster=str):
    v = input(q + ": ").strip()
    if caster is str: return v
    try: return caster(v)
    except: sys.exit(f"Invalid input for {q}")

def geocode_city(q):
    r = requests.get("https://nominatim.openstreetmap.org/search",
        params={"q":q,"format":"json","limit":1},
        headers={"User-Agent":"SmithEquivalencePyto/1.0"}, timeout=20)
    j = r.json()
    if not j: sys.exit("Location not found.")
    return float(j[0]["lat"]), float(j[0]["lon"])

def detect_utc_offset_hours(lat, lon):
    r = requests.get("https://api.open-meteo.com/v1/forecast",
        params={"latitude":lat,"longitude":lon,"timezone":"auto"},
        headers={"User-Agent":"SmithEquivalencePyto/1.0"}, timeout=20)
    j = r.json()
    return j.get("utc_offset_seconds", 0)/3600.0

def generate_sine_wave(filename, freq_hz):
    samples = (np.sin(2*np.pi*np.arange(int(SAMPLE_RATE*DURATION))*freq_hz/SAMPLE_RATE))
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        for s in samples:
            wf.writeframes(struct.pack('<h', int(max(-1,min(1,s))*32767)))

# --- main ----------------------------------------------------------
def main():
    say("🔮 Smith Equivalence — v6.1 (Galactic Year + Exact Input)\n")

    date_s = ask("Date (YYYY-MM-DD)")
    time_s = ask("Time (HH:MM 24h)")
    city   = ask("City, State (or type ENTER EXACT)")

    if city.strip().upper() == "ENTER EXACT":
        lat = ask("Latitude (decimal degrees)", float)
        lon = ask("Longitude (decimal degrees)", float)
    else:
        say("📡 Locating + timezone detection…")
        lat, lon = geocode_city(city)

    utc_off = detect_utc_offset_hours(lat, lon)
    local_dt = dt.datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M")
    utc_dt = local_dt - dt.timedelta(hours=utc_off)

    jd = jd_from_datetime(utc_dt)
    lst = lst_hours(jd, lon)
    H = hour_angle(lst, RA_GC_H)
    alt_gc = altitude_deg(lat, DEC_GC_DEG, H)

    say(f"🪐 JD={jd}  LST={lst}h  GC H={H}h  Alt={alt_gc}°")

    say("\nSelect cycle:")
    for k,v in CYCLES.items(): say(f"  {k}. {v[0]}")
    ckey = ask("Cycle", str)
    if ckey not in CYCLES: sys.exit("Invalid cycle")
    name, _, f0_nhz = CYCLES[ckey]
    n = ask("Harmonic n", int)

    f0_hz = f0_nhz * 1e-9
    fn_nhz_raw = n * f0_nhz
    fn_hz_raw = fn_nhz_raw * 1e-9

    W_phase = 0.5 * (1.0 + math.cos(2.0*math.pi*(H/24.0)))
    W_alt = max(0.0, (math.sin(math.radians(alt_gc)) + 1.0) * 0.5)
    W = max(1e-12, W_phase * W_alt)

    fn_nhz_repr = fn_nhz_raw * W
    fn_hz_repr  = fn_nhz_repr * 1e-9

    audible_repr = owm_to_audible(fn_hz_repr, f0_hz)
    audible_repr_out = f"{audible_repr:.6f}"

    say(f"\nWeights: phase={W_phase} altitude={W_alt} composite={W}")
    say(f"🎚 Represented Audible Frequency: {audible_repr_out} Hz")

    base = f"{name.replace(' ','_')}_n{n}_{local_dt.strftime('%Y%m%d_%H%M')}"
    md_path = os.path.abspath(base + "_GrimoireLog.md")
    wav_path = os.path.abspath(base + "_Tone.wav")

    say("🎧 Generating 60-second tone…")
    generate_sine_wave(wav_path, audible_repr)
    say(f"    Saved tone → {wav_path}")

    md = f"""# Cosmic → Audible Frequency Log (v6.1)

**Cycle:** {name}  
**Harmonic (n):** {n}  

**Local Date/Time:** {local_dt} (UTC{utc_off:+.2f})  
**UTC Date/Time:** {utc_dt}  
**Julian Date (UTC):** {jd}  

**Location:** {city}  
**Latitude:** {lat}°  
**Longitude:** {lon}°  
**Local Sidereal Time:** {lst} h  
**Galactic Center Hour Angle:** {H} h  
**Galactic Center Altitude:** {alt_gc}°  

**Weights**  
- Phase = {W_phase}  
- Altitude = {W_alt}  
- Composite = {W}  

**Base f₀:** {f0_nhz} nHz ({f0_hz} Hz)  
**Cosmic fₙ (Represented):** {fn_nhz_repr} nHz ({fn_hz_repr} Hz)  
**Audible (OWM):** {audible_repr_out} Hz  

**Tone File:** {wav_path}  
"""
    with open(md_path, "w", encoding="utf-8") as f: f.write(md)
    say(f"🪶 Log saved → {md_path}")
    say("✅ Complete.")

if __name__ == "__main__":
    main()