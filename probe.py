import json, re, requests
UA = "agenda-personal-rffm/1.0 (uso personal, pocas peticiones al dia)"
RX = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
cfg = json.load(open("config.json", encoding="utf-8"))
out = {}
def shape(o, d=0):
    if d > 4: return "..."
    if isinstance(o, dict): return {k: shape(v, d+1) for k, v in list(o.items())[:40]}
    if isinstance(o, list): return [shape(o[0], d+1), f"(+{len(o)-1} más)"] if o else []
    return o if not isinstance(o, str) or len(o) < 60 else o[:60]
for t in cfg["equipos"]:
    url = t["url"]; r = out[t["nombre"]] = {}
    html = requests.get(url, headers={"User-Agent": UA}, timeout=30).text
    r["links_clasif"] = sorted(set(re.findall(r'href="([^"]*clasific[^"]*)"', html, re.I)))[:20]
    m = RX.search(html); nd = json.loads(m.group(1))
    r["next_page"] = nd.get("page"); r["calendar_keys"] = list(nd["props"]["pageProps"].keys())
    cal = nd["props"]["pageProps"]["calendar"]
    r["calendar_shape"] = shape({k: v for k, v in cal.items() if k != "rounds"})
    r["round0"] = shape(cal["rounds"][0]); r["n_rounds"] = len(cal["rounds"])
    r["sample_round_all"] = cal["rounds"][4] if len(cal["rounds"]) > 4 else None
    for cand in ["clasificacion", "clasificaciones", "clasificacion-general"]:
        u = url.replace("/calendario", "/" + cand)
        try:
            rr = requests.get(u, headers={"User-Agent": UA}, timeout=30); r["try_" + cand] = rr.status_code
            m2 = RX.search(rr.text)
            if rr.status_code == 200 and m2:
                nd2 = json.loads(m2.group(1)); r["found"] = cand; r["clasif_shape"] = shape(nd2["props"]["pageProps"]); r["clasif_raw"] = nd2["props"]["pageProps"]; break
        except Exception as e: r["try_" + cand] = str(e)
json.dump(out, open("docs/debug.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
