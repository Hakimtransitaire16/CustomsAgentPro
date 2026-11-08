"""Contrôles automatiques d'un dossier : valeur, liquidation, poids, colis, dates.

Chaque contrôle renvoie un constat : {"id", "titre", "statut": ok|alerte|erreur, "detail"}.
"""
from .data import date, n

TOL_DA = 1.0          # tolérance d'arrondi en dinars
TOL_REL = 0.0001      # 0,01 % pour les conversions de devise


def _c(cid, titre, ok, detail, niveau="erreur"):
    return {"id": cid, "titre": titre, "statut": "ok" if ok else niveau, "detail": detail}


def controles(d):
    dec, arts, liq = d["declaration"], d["articles"], d["liquidation"]
    out = []

    # 1. Montant facture = marchandises + fret + autres frais
    marchandises = sum(a.get("valeur_facture", 0) for a in arts)
    attendu = marchandises + dec.get("fret", 0) + dec.get("autres_frais", 0)
    out.append(_c("VAL-1", "Montant facture = articles + fret + frais",
                  abs(attendu - dec["montant_facture"]) < 0.01,
                  f"{n(marchandises, 2)} + {n(dec.get('fret', 0), 2)} = {n(attendu, 2)} {dec['devise']} (déclaré {n(dec['montant_facture'], 2)})"))

    # 2. Conversion en dinars
    conv = (dec["montant_facture"] + dec.get("assurance", 0)) * dec["taux_change"]
    out.append(_c("VAL-2", "Valeur en DA = montant × taux",
                  abs(conv - dec["valeur_da"]) <= max(TOL_DA, conv * TOL_REL),
                  f"{n(dec['montant_facture'], 2)} × {dec['taux_change']} = {n(conv, 2)} DA (déclaré {n(dec['valeur_da'])})"))

    # 3. Somme des valeurs articles
    s = sum(a["valeur_da"] for a in arts)
    out.append(_c("VAL-3", "Somme des articles = valeur déclarée", abs(s - dec["valeur_da"]) <= TOL_DA,
                  f"{' + '.join(n(a['valeur_da']) for a in arts)} = {n(s)} DA"))

    # 4. Assurance déclarée
    out.append(_c("VAL-4", "Assurance déclarée", dec.get("assurance", 0) > 0 or dec.get("incoterm") in ("CIF", "CIP", "DAP", "DDP"),
                  f"assurance = {n(dec.get('assurance', 0), 2)} ; incoterm {dec.get('incoterm')} : préparer la police d'assurance", "alerte"))

    # 5. Liquidation par article
    for a in arts:
        t = {x["code"]: x for x in a["taxes"]}
        ok, det = True, []
        for code in ("CS", "DD"):
            if code in t:
                calc_ = t[code]["assiette"] * t[code]["quotite"] / 100
                ok &= abs(calc_ - t[code]["montant"]) <= TOL_DA and abs(t[code]["assiette"] - a["valeur_da"]) <= TOL_DA
                det.append(f"{code} {t[code]['quotite']} % = {n(calc_, 2)}")
        if "TVA" in t:
            base = a["valeur_da"] + t.get("DD", {}).get("montant", 0) + t.get("CS", {}).get("montant", 0)
            calc_ = t["TVA"]["assiette"] * t["TVA"]["quotite"] / 100
            ok &= abs(base - t["TVA"]["assiette"]) <= TOL_DA and abs(calc_ - t["TVA"]["montant"]) <= TOL_DA
            det.append(f"assiette TVA {n(base, 2)} → TVA {n(calc_, 2)}")
        out.append(_c(f"LIQ-{a['num']}", f"Liquidation article {a['num']}", ok, " · ".join(det)))

    # 6. Récapitulatif
    tot = {}
    for a in arts:
        for x in a["taxes"]:
            tot[x["code"]] = tot.get(x["code"], 0) + x["montant"]
    ok = all(abs(int(tot.get(k, 0)) - liq.get(k, 0)) <= TOL_DA for k in ("DD", "TVA", "CS"))
    total = sum(liq.get(k, 0) for k in ("DD", "TVA", "CS", "RPS"))
    ok &= abs(total - liq["total"]) <= TOL_DA
    out.append(_c("LIQ-T", "Liquidation récapitulative", ok,
                  " + ".join(f"{k} {n(liq.get(k, 0))}" for k in ("DD", "TVA", "CS", "RPS")) + f" = {n(total)} DA (déclaré {n(liq['total'])})"))

    # 7. Poids et colis
    col = d.get("colisage", [])
    if col:
        net = sum(c["net"] for c in col)
        brut = sum(c["brut"] for c in col)
        pal = sum(c["palettes"] for c in col)
        net_art = sum(a["poids_net"] for a in arts)
        out.append(_c("PDS-1", "Poids net colisage = articles", abs(net - net_art) < 0.5, f"colisage {n(net)} kg · articles {n(net_art)} kg"))
        out.append(_c("PDS-2", "Poids brut colisage = D10", abs(brut - dec["poids_brut"]) < 0.5, f"{' + '.join(n(c['brut']) for c in col)} = {n(brut)} kg (D10 {n(dec['poids_brut'])})"))
        out.append(_c("COL-1", "Nombre de colis", pal == dec["nb_colis"], f"{pal} palettes · D10 {dec['nb_colis']} colis"))
    for a in arts:
        q = a.get("quantite", {})
        if q.get("nombre") and q.get("contenance_kg"):
            v = q["nombre"] * q["contenance_kg"]
            out.append(_c(f"QTE-{a['num']}", f"Quantité × contenance art. {a['num']}", abs(v - a["poids_net"]) < 0.5,
                          f"{q['nombre']} × {n(q['contenance_kg'])} kg = {n(v)} kg (poids net {n(a['poids_net'])})"))

    # 8. Dates
    t = d.get("transport", {})
    dom = date(dec.get("domiciliation", {}).get("date"))
    bl = date(t.get("date_bl"))
    if dom and bl:
        out.append(_c("DAT-1", "Domiciliation avant expédition", dom <= bl, f"domiciliation {dom:%d/%m/%Y} · B/L {bl:%d/%m/%Y}"))
    acc, d10 = date(t.get("date_accostage")), date(dec.get("date_heure"))
    if acc and d10:
        j = (d10 - acc).days
        fr = t.get("franchise_jours")
        out.append(_c("DAT-2", "Délai accostage → D10", not fr or j <= fr, f"{j} jours (franchise conteneur {fr} jours)", "alerte"))

    # 9. Conteneur (chiffre de contrôle ISO 6346)
    c = t.get("conteneur", "")
    if len(c) == 11:
        out.append(_c("ISO-1", "Chiffre de contrôle du conteneur (ISO 6346)", iso6346_ok(c), c, "alerte"))
    return out


def iso6346_ok(code):
    vals, v = {}, 10
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if v % 11 == 0:
            v += 1
        vals[ch] = v
        v += 1
    s = sum((vals[ch] if ch.isalpha() else int(ch)) * (2 ** i) for i, ch in enumerate(code[:10]))
    return (s % 11) % 10 == int(code[10])


def resume(ctrls):
    return {k: sum(1 for c in ctrls if c["statut"] == k) for k in ("ok", "alerte", "erreur")}
