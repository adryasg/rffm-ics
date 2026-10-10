#!/usr/bin/env python3
"""Genera docs/partidos.ics a partir de calendarios de rffm.es (uso personal)."""
import argparse, hashlib, json, re, sys, unicodedata
from datetime import date, datetime, timedelta

UA = "agenda-personal-rffm/1.0 (uso personal, pocas peticiones al dia)"
RX = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)

def norm(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").upper().strip()

def extraer_calendario(html):
    m = RX.search(html)
    if not m:
        raise ValueError("No encuentro __NEXT_DATA__ en la pagina (la web puede haber cambiado)")
    cal = json.loads(m.group(1))["props"]["pageProps"].get("calendar")
    if not cal or "rounds" not in cal:
        raise ValueError("La pagina no trae calendar.rounds")
    return cal

def descargar(url):
    import requests
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    return r.text

def txt(v):
    if isinstance(v, dict):
        return str(v.get("nombre") or v.get("name") or v.get("descripcion") or "")
    return str(v or "")

def partidos_del_equipo(cal, equipo):
    q = norm(equipo)
    res, vistos = [], set()
    for r in cal["rounds"]:
        for p in r.get("equipos", []):
            l, v = p.get("equipo_local", ""), p.get("equipo_visitante", "")
            vistos.update([l, v])
            if q in norm(l) or q in norm(v):
                res.append((r, p))
    if not res:
        print(f"  ! Ningun partido para '{equipo}'. Equipos que aparecen:", file=sys.stderr)
        for e in sorted(x for x in vistos if x):
            print("    -", e, file=sys.stderr)
    return res

ROMANOS = {"I","II","III","IV","V","VI","VII","VIII","IX","X"}
def bonito(s):
    out = []
    for w in str(s).split():
        if "." in w or len(w) == 1 or w.upper() in ROMANOS:
            out.append(w.upper() if len(w) <= 4 else w)
        else:
            out.append(w.capitalize())
    return " ".join(out)

def minutos_parte(competicion, cfg):
    c = norm(competicion).lower()
    for k, v in cfg["duraciones"].items():
        if k != "defecto" and k in c:
            return v
    return cfg["duraciones"]["defecto"]

def construir_eventos(cal, equipo_cfg, cfg, hoy):
    comp = txt(cal.get("competicion")); grupo = txt(cal.get("grupo"))
    dur = 2 * minutos_parte(comp, cfg) + cfg["descanso"]
    evs = []
    for r, p in partidos_del_equipo(cal, equipo_cfg["equipo"]):
        try:
            d = datetime.strptime(p.get("fecha", ""), "%d-%m-%Y").date()
        except ValueError:
            continue
        if d < hoy:
            continue
        hora = (p.get("hora") or "").strip()
        campo = re.sub(r"\s*\(\w{1,3}\)\s*$", "", str(p.get("campo") or "")).strip()
        titulo = f'{equipo_cfg["nombre"]}: {bonito(p["equipo_local"])} - {bonito(p["equipo_visitante"])}'
        ev = {"uid": "rffm-" + hashlib.sha1("|".join(map(str, [comp, grupo, r.get("jornada"), p["equipo_local"], p["equipo_visitante"]])).encode()).hexdigest()[:16] + "@agenda",
              "fecha": d, "lugar": campo,
              "notas": f'Jornada {r.get("jornada")} · {comp} {grupo} · Fuente: RFFM'}
        try:
            h = datetime.strptime(hora, "%H:%M")
            ev["ini"] = datetime.combine(d, h.time()); ev["fin"] = ev["ini"] + timedelta(minutes=dur)
            ev["titulo"] = titulo; ev["estado"] = "CONFIRMED"
        except ValueError:
            ev["ini"] = None; ev["titulo"] = titulo + " (hora por confirmar)"; ev["estado"] = "TENTATIVE"
        evs.append(ev)
    return evs

def esc(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def fold(line):
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > (75 if not out else 74):
            out.append(cur.decode("utf-8")); cur = c
        else:
            cur += c
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)

TZ = ("BEGIN:VTIMEZONE\nTZID:Europe/Madrid\nBEGIN:DAYLIGHT\nTZOFFSETFROM:+0100\nTZOFFSETTO:+0200\nTZNAME:CEST\n"
      "DTSTART:19700329T020000\nRRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU\nEND:DAYLIGHT\nBEGIN:STANDARD\nTZOFFSETFROM:+0200\n"
      "TZOFFSETTO:+0100\nTZNAME:CET\nDTSTART:19701025T030000\nRRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU\nEND:STANDARD\nEND:VTIMEZONE").split("\n")

def construir_ics(evs, nombre):
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//agenda-personal//rffm//ES", "CALSCALE:GREGORIAN",
         "X-WR-CALNAME:" + esc(nombre), "X-WR-TIMEZONE:Europe/Madrid"] + TZ
    for e in sorted(evs, key=lambda x: (x["fecha"], x["ini"] or datetime.min)):
        L += ["BEGIN:VEVENT", "UID:" + e["uid"], "DTSTAMP:" + e["fecha"].strftime("%Y%m%dT000000Z"),
              "SUMMARY:" + esc(e["titulo"])]
        if e["ini"]:
            L += ["DTSTART;TZID=Europe/Madrid:" + e["ini"].strftime("%Y%m%dT%H%M%S"),
                  "DTEND;TZID=Europe/Madrid:" + e["fin"].strftime("%Y%m%dT%H%M%S")]
        else:
            L += ["DTSTART;VALUE=DATE:" + e["fecha"].strftime("%Y%m%d"),
                  "DTEND;VALUE=DATE:" + (e["fecha"] + timedelta(days=1)).strftime("%Y%m%d")]
        if e["lugar"]: L.append("LOCATION:" + esc(e["lugar"]))
        L += ["DESCRIPTION:" + esc(e["notas"]), "STATUS:" + e["estado"], "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in L) + "\r\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--out", default="docs/partidos.ics")
    ap.add_argument("--html-fixture", help="HTML local para probar sin red")
    ap.add_argument("--hoy")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    hoy = datetime.strptime(a.hoy, "%Y-%m-%d").date() if a.hoy else date.today()
    evs, fallos = [], 0
    for t in cfg["equipos"]:
        if "PEGA_AQUI" in t["equipo"] + t["url"]:
            print("Config sin rellenar:", t["nombre"], file=sys.stderr); fallos += 1; continue
        try:
            html = open(a.html_fixture, encoding="utf-8").read() if a.html_fixture else descargar(t["url"])
            evs += construir_eventos(extraer_calendario(html), t, cfg, hoy)
        except Exception as ex:
            print(f'Error con {t["nombre"]}: {ex}', file=sys.stderr); fallos += 1
    if fallos and not evs:
        sys.exit("Sin datos: no se sobrescribe el .ics anterior")
    open(a.out, "w", encoding="utf-8", newline="").write(construir_ics(evs, cfg["nombre_calendario"]))
    print(f"{len(evs)} partidos -> {a.out}")

if __name__ == "__main__":
    main()
