#!/usr/bin/env python3
"""Hook UserPromptSubmit : à chaque message qui touche la douane, le moteur consulte toutes les sources
(tarif, SH 2022, mise à jour 2020, DAPS, LF 2026, décisions de classement, codes, décrets, guides, veille)
et ajoute le résultat au contexte de Claude, avant même la réponse. Aucun fichier à désigner.

Silencieux (aucune sortie) si la demande ne concerne pas la douane ou en cas d'erreur : le hook ne bloque jamais.
"""
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

RACINE = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
MAX = 6000


def main() -> None:
    try:
        prompt = json.load(sys.stdin).get("prompt", "")
    except Exception:
        return
    if not prompt or len(prompt) > 4000:
        return
    sys.path.insert(0, str(RACINE))
    try:
        from visite import moteur
        if not moteur.utile(prompt):
            return
        with redirect_stdout(io.StringIO()):
            res = moteur.analyser(prompt, preparation=False)
        if not (res["positions"] or res["candidats"] or res["articles"] or res["passages"]):
            return
        print("[Moteur CustomsAgentPro — sources consultées automatiquement. Fonder la réponse sur ces éléments, "
              "les citer, et compléter avec `python -m visite demande` / `tarif --notes` si besoin.]")
        print(moteur.texte(res, max_car=MAX))
    except Exception:
        return


if __name__ == "__main__":
    main()
