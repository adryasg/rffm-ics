#!/usr/bin/env python3
"""Genera docs/ligas.json: clasificación (calculada con los resultados) y partidos de cada jornada."""
import argparse, json, re, sys
from datetime import datetime, date
from generar_ics import norm, extraer_calendario, descargar, txt, bonito

def iso(f):
    try: return datetime.strptime(f, "%d-%m-%Y").date().isoformat()
    except Exception: return ""

def num(v):
    v = str(v if v is not None else "").strip()
    return int(v) if v.isdigit() else None

def limpio(n):
    return re.sub(r"\s+", " ", str(n or "")).strip()

def campo(c):
    return re.sub(r"\s*\(\s*[A-Za-z]{1,3}\s*\)", "", str(c or "")).replace("(", "").replace(")", "").strip()

def construir_liga(cal, t):
    mio = norm(t["equipo"])
    es_mio = lambda n: mio in norm(n)
    jornadas, tabla = [], {}
    def fila(n):
        return tabla.setdefault(n, {"equipo": n, "pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0, "pts": 0, "mio": es_mio(n)})
    for r in cal["rounds"]:
        m = re.match(r"\s*(\d+)", str(r.get("jornada", "")))
        n = int(m.group(1)) if m else int(r.get("codjornada") or 0)
        partidos, fechas = [], []
        for p in r.get("equipos", []):
            l, v = limpio(p.get("equipo_local")), limpio(p.get("equipo_visitante"))
            if not l and not v: continue
            gl, gv = num(p.get("goles_casa")), num(p.get("goles_visitante"))
            f = iso(p.get("fecha", ""))
            if f: fechas.append(f)
            partidos.append({"l": l, "v": v, "gl": gl, "gv": gv, "f": f, "h": (p.get("hora") or "").strip(),
                             "c": campo(p.get("campo")), "mio": es_mio(l) or es_mio(v)})
            for nom in (l, v):
                if nom and "no asignado" not in nom.lower(): fila(nom)
            if gl is not None and gv is not None and "no asignado" not in (l + v).lower():
                a, b = fila(l), fila(v)
                a["pj"] += 1; b["pj"] += 1; a["gf"] += gl; a["gc"] += gv; b["gf"] += gv; b["gc"] += gl
                if gl > gv: a["g"] += 1; b["p"] += 1; a["pts"] += 3
                elif gl < gv: b["g"] += 1; a["p"] += 1; b["pts"] += 3
                else: a["e"] += 1; b["e"] += 1; a["pts"] += 1; b["pts"] += 1
        fj = ""
        mm = re.search(r"\((\d{2}-\d{2}-\d{4})\)", str(r.get("jornada", "")))
        if mm: fj = iso(mm.group(1))
        ini = min(fechas) if fechas else fj
        fin = max(fechas) if fechas else fj
        jornadas.append({"n": n, "ini": ini, "fin": fin, "partidos": partidos})
    clas = sorted(tabla.values(), key=lambda x: (-x["pts"], -(x["gf"] - x["gc"]), -x["gf"], norm(x["equipo"])))
    for i, x in enumerate(clas, 1):
        x["pos"] = i; x["dg"] = x["gf"] - x["gc"]
    hoy = date.today().isoformat()
    actual = next((j["n"] for j in jornadas if j["fin"] and j["fin"] >= hoy), jornadas[-1]["n"] if jornadas else 0)
    return {"id": t["nombre"], "nombre": t["nombre"], "competicion": txt(cal.get("competicion")), "grupo": txt(cal.get("grupo")),
            "equipo": t["equipo"], "actual": actual, "jornadas": jornadas, "clasificacion": clas}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.json"); ap.add_argument("--out", default="docs/ligas.json")
    ap.add_argument("--html-fixture", action="append")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")); ligas = []
    for i, t in enumerate(cfg["equipos"]):
        if "PEGA_AQUI" in t["equipo"] + t["url"]: continue
        try:
            html = open(a.html_fixture[i], encoding="utf-8").read() if a.html_fixture else descargar(t["url"])
            ligas.append(construir_liga(extraer_calendario(html), t))
        except Exception as ex:
            print(f'Error con {t["nombre"]}: {ex}', file=sys.stderr)
    if not ligas: sys.exit("Sin datos: no se sobrescribe ligas.json")
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"actualizado": datetime.now().astimezone().isoformat(timespec="minutes"), "ligas": ligas}, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(ligas)} ligas -> {a.out}")

if __name__ == "__main__":
    main()
