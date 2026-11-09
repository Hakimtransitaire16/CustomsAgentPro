"""Analyse 360° d'un dossier : le même dossier vu par chaque métier.

Coût de revient, logistique (transit, séjour, surestaries), finance et banque (change, délais de paiement),
fiscalité (pression réelle, effet de l'exonération) et commerce (prix unitaire, programme d'importation).

Tout chiffre vient de dossier.json ; une estimation est marquée comme telle, et ce qui manque pour
conclure est listé à part. Réservé au déclarant : jamais dans la fiche remise au service.
"""
from __future__ import annotations

import datetime as dt
import re

from .data import n


def _date(s: str) -> dt.date | None:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    if m:
        return dt.date(int(m[3]), int(m[2]), int(m[1]))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    return dt.date(int(m[1]), int(m[2]), int(m[3])) if m else None


def surestaries(d: dict, au: dt.date | None = None) -> dict | None:
    """Surestaries du conteneur selon le barème de l'armateur (transport.surestaries), de l'accostage à la date `au`."""
    tr = d.get("transport", {})
    bar = tr.get("surestaries")
    acc = _date(tr.get("date_accostage", ""))
    au = au or _date(d["declaration"].get("date_heure", ""))
    if not (bar and acc and au):
        return None
    jours = (au - acc).days
    lignes, total, dernier = [], 0.0, bar.get("franchise_jours", 0)
    for debut, fin, taux in bar.get("paliers", []):
        nb = max(0, min(jours, fin) - debut + 1)
        lignes.append((debut, fin, taux, nb, nb * taux))
        total += nb * taux
        dernier = max(dernier, fin)
    taux_da = bar.get("taux_da")
    return dict(jours=jours, franchise=bar.get("franchise_jours", 0), lignes=lignes, total=total, devise=bar.get("devise", "USD"),
                taux_da=taux_da, total_da=round(total * taux_da, 2) if taux_da else None,
                au_dela=max(0, jours - dernier), dernier=dernier, hypothese=bar.get("hypothese", ""),
                gestion_da=bar.get("frais_gestion_da") if jours > bar.get("seuil_gestion_jours", 10 ** 6) else 0,
                source=bar.get("source", ""), categorie=bar.get("categorie", ""), au=au)


def analyse(d: dict) -> dict:
    """Sections de l'analyse : listes de (libellé, valeur, commentaire) et liste des données manquantes."""
    dec, liq, arts = d["declaration"], d["liquidation"], d["articles"]
    v = dec["valeur_da"]
    qte = sum(a["quantite"]["nombre"] for a in arts if isinstance(a.get("quantite", {}).get("nombre"), (int, float)))
    unite = arts[0].get("quantite", {}).get("unite", "unités")
    par = 1000 if qte >= 10000 else 1
    lib_par = f"pour {n(par)} {unite}" if par > 1 else f"par {unite.rstrip('s')}"
    sec, manque = {}, []

    # 1. Coût de revient : ce qui est connu, puis ce qui est estimé
    s = surestaries(d)
    frais = d.get("frais_locaux", [])
    lignes = [("Valeur en douane", v, f"{dec.get('incoterm', '')} — D10"), ("Droits et taxes payés", liq["total"], "récapitulatif du D10")]
    lignes += [(f["libelle"], f["ht"], f"hors TVA — {f.get('piece', '')}") for f in frais]
    connu = sum(x[1] for x in lignes)
    est = []
    if s and s["total_da"]:
        est.append((f"Surestaries du conteneur, jours {s['franchise'] + 1} à {min(s['jours'], s['dernier'])} (estimation)", s["total_da"],
                    f"{n(s['total'], 2)} {s['devise']} × {n(s['taux_da'], 4)} — {s['source']}"))
        if s["gestion_da"]:
            est.append(("Frais de gestion de l'armateur (conteneur non restitué à 90 jours)", s["gestion_da"], f"hors TVA — {s['source']}"))
    total = connu + sum(x[1] for x in est)
    rev = [(l, f"{n(m, 2)} DA", c) for l, m, c in lignes]
    rev.append(("Coût connu", f"{n(connu, 2)} DA", f"{n(connu / qte * par, 2)} DA {lib_par}" if qte else ""))
    rev += [(l, f"{n(m, 2)} DA", c) for l, m, c in est]
    if est:
        rev.append(("Coût connu + estimé", f"{n(total, 2)} DA",
                    (f"{n(total / qte * par, 2)} DA {lib_par} · " if qte else "") + f"+{n((total / v - 1) * 100, 1)} % sur la valeur en douane"))
    sec["Coût de revient"] = rev
    manque += ["magasinage au lieu de dépôt (tarif et nombre de jours)", "transport intérieur port → lieu de visite → usine",
               "honoraires du commissionnaire", "frais bancaires (domiciliation, remise documentaire)"]

    # 2. Logistique
    log = []
    bl, acc, d10 = _date(d.get("transport", {}).get("date_bl", "")), _date(d.get("transport", {}).get("date_accostage", "")), _date(dec.get("date_heure", ""))
    if bl and acc:
        log.append(("Transit maritime", f"{(acc - bl).days} jours", f"B/L {bl:%d/%m/%Y} → accostage {acc:%d/%m/%Y}"))
    if acc and d10:
        log.append(("Séjour avant déclaration", f"{(d10 - acc).days} jours", f"accostage {acc:%d/%m/%Y} → D10 {d10:%d/%m/%Y}"))
    if s:
        log.append(("Hors franchise conteneur", f"{max(0, s['jours'] - s['franchise'])} jours", f"franchise {s['franchise']} jours ({s['categorie']})"))
        for debut, fin, taux, nb, m in s["lignes"]:
            log.append((f"Surestaries jours {debut} à {fin}", f"{nb} j × {n(taux)} {s['devise']} = {n(m)} {s['devise']}", "barème de l'avis d'arrivée"))
        if s["au_dela"]:
            log.append((f"Au-delà du jour {s['dernier']}", f"{s['au_dela']} jours", "barème non indiqué sur l'avis : à demander à l'armateur"))
            manque.append(f"barème des surestaries après {s['dernier']} jours et date de restitution du conteneur")
    else:
        manque.append("barème des surestaries de l'armateur (franchise, paliers)")
    sec["Logistique"] = log

    # 3. Finance et banque
    fin = []
    fac = next((_date(x.get("date", "")) for x in d.get("documents", []) if x.get("code") == "FAC"), None)
    dom = _date((dec.get("domiciliation") or {}).get("date", ""))
    if fac and dom:
        fin.append(("Facture → domiciliation", f"{(dom - fac).days} jours", f"{fac:%d/%m/%Y} → {dom:%d/%m/%Y}"))
    if dom and bl:
        fin.append(("Domiciliation → expédition", f"{(bl - dom).days} jours", "domiciliation antérieure au B/L" if dom <= bl else "B/L antérieur à la domiciliation"))
    fin.append(("Taux de change du D10", f"{n(dec['taux_change'], 4)} DA / {dec['devise']}", "D10"))
    autre = (d.get("transport", {}).get("surestaries") or {}).get("taux_devise_facture")
    if autre:
        fin.append(("Taux à l'arrivée (avis de l'armateur)", f"{n(autre, 4)} DA / {dec['devise']}",
                    f"écart {n((dec['taux_change'] / autre - 1) * 100, 2)} % avec le taux du D10"))
    un = dec["montant_facture"] * dec["taux_change"] * 0.01
    taux_ad = sum(t["quotite"] for a in arts[:1] for t in a.get("taxes", []) if not t.get("exonere") and t["code"] in ("DD", "CS"))
    fin.append((f"Sensibilité au change : 1 % sur {dec['devise']}/DZD", f"± {n(un)} DA de valeur", f"± {n(un * taux_ad / 100)} DA de droits payés ({n(taux_ad)} %)"))
    if (d.get("valeur") or {}).get("paiement_fournisseur"):
        fin.append(("Paiement du fournisseur", d["valeur"]["paiement_fournisseur"], "facture"))
    sec["Finance et banque"] = fin
    manque.append("règlement de la Banque d'Algérie sur la domiciliation et les délais de paiement (absent de la base)")

    # 4. Fiscalité
    fis = [("Pression fiscale payée", f"{n(liq['total'] / v * 100, 2)} % de la valeur", f"{n(liq['total'])} DA")]
    exo = [t for a in arts for t in a.get("taxes", []) if t.get("exonere")]
    if exo:
        cs = sum(t["montant"] for a in arts for t in a.get("taxes", []) if t["code"] == "CS")
        dd = sum(t["montant"] for t in exo if t["code"] == "DD")
        tva = round((v + dd + cs) * 0.19, 2) if any(t["code"] == "TVA" for t in exo) else 0
        plein = liq["total"] + dd + tva
        fis.append(("Sans exonération (estimation)", f"{n(plein / v * 100, 2)} % de la valeur", f"{n(plein, 2)} DA : DD + TVA sur (valeur + DD + CS)"))
        fis.append(("Économie due à l'exonération", f"{n(dd + tva, 2)} DA", f"{n((dd + tva) / qte * par, 2)} DA {lib_par}" if qte else ""))
    sec["Fiscalité"] = fis

    # 5. Commerce et programme
    com = []
    if qte:
        com.append(("Prix de revient douane", f"{n(v / qte * par, 2)} DA {lib_par}", f"{n(dec['montant_facture'] / qte * par, 2)} {dec['devise']} {dec.get('incoterm', '')} {lib_par}"))
    p = d.get("programme")
    if p and qte:
        part = qte / p["quantite"]
        solde = p["quantite"] - qte
        com.append(("Imputation sur le programme", f"{n(part * 100, 2)} %", f"{n(qte)} sur {n(p['quantite'])} {unite}"))
        com.append(("Solde du programme", f"{n(solde)} {unite}", f"≈ {n(solde / qte, 1)} expéditions de cette taille, si aucune autre imputation"))
        finv = _date(p.get("validite_fin", ""))
        if finv and d10:
            com.append(("Fin de validité du visa", f"{finv:%d/%m/%Y}", f"{(finv - d10).days} jours après le D10 : programme suivant à préparer"))
        if p.get("prix_unitaire") and arts[0].get("valeur_facture"):
            pu = arts[0]["valeur_facture"] / qte
            com.append(("Prix facturé / prix du programme", f"{n(pu, 5)} / {n(p['prix_unitaire'], 5)} {p.get('devise', dec['devise'])}",
                        "identiques" if abs(pu - p["prix_unitaire"]) < 5e-6 else f"écart {n((pu / p['prix_unitaire'] - 1) * 100, 2)} %"))
        manque.append("imputations antérieures sur le programme (feuille d'imputation)")
    sec["Commerce et programme"] = com
    return dict(sections=sec, manque=manque, surestaries=s)


def texte(d: dict) -> str:
    a = analyse(d)
    L = [f"# Analyse 360° — dossier {d['meta']['id']}", "", "Réservé au déclarant. Estimations signalées ; la facture de chaque prestataire fait foi.", ""]
    for titre, lignes in a["sections"].items():
        if not lignes:
            continue
        L += [f"## {titre}", "", "| Élément | Valeur | Base |", "|---|---|---|"]
        L += [f"| {l} | {val} | {c} |" for l, val, c in lignes]
        L.append("")
    L += ["## Données à obtenir pour compléter", ""] + [f"- {m}" for m in a["manque"]] + [""]
    return "\n".join(L)
