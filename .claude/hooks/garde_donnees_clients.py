#!/usr/bin/env python3
"""Hook PreToolUse (Bash) : bloque tout git add / commit / push qui ferait entrer des données clients dans le dépôt.

Bloqué :
- `git add` qui vise dossiers/, un dossier.json, sortie/, registre/, un scan PDF ou une visite exportée ;
- `git add -f/--force` (contournement du .gitignore) ;
- `git commit` / `git push` alors qu'un fichier client est indexé ou suivi ;
- `git add -A` / `git add .` alors que des fichiers clients non ignorés existent dans l'arbre.

Sortie : code 2 + message sur stderr → Claude Code annule la commande et affiche la raison.
Les exemples fictifs de visite/exemples/ sont autorisés.
"""
import json
import re
import subprocess
import sys

CLIENT = re.compile(
    r"(^|/)(dossiers|registre|sortie)(/|$)"
    r"|(^|/)dossier\.json$"
    r"|(^|/)visite_[^/]*\.json$"
    r"|(^|/)CamScanner[^/]*\.pdf$"
    r"|(^|/)(Fiche_technique|Dossier)_[^/]*\.(pdf|html)$"
    r"|(^|/)registre\.(csv|json)$",
    re.I,
)
AUTORISE = re.compile(r"^visite/exemples/|^visite/schema/|^visite/templates/|^\.claude/")


def client(path: str) -> bool:
    p = path.strip().strip('"').lstrip("./")
    return bool(CLIENT.search(p)) and not AUTORISE.search(p)


def git(*args) -> list[str]:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    return [l for l in out.splitlines() if l.strip()]


def bloquer(raison: str, fichiers=()) -> None:
    liste = "".join(f"\n  - {f}" for f in list(fichiers)[:15])
    sys.stderr.write(
        "BLOQUÉ — données clients (CLAUDE.md, Confidentialité) : " + raison + liste +
        "\nLes fichiers de dossiers/ (NIF, RC, banque, montants) ne sont jamais commités ni poussés. "
        "Retirer ces fichiers de l'index (git restore --staged <fichier>) et relancer.\n")
    sys.exit(2)


def main() -> None:
    try:
        evt = json.load(sys.stdin)
    except Exception:
        return
    if evt.get("tool_name") != "Bash":
        return
    cmd = (evt.get("tool_input") or {}).get("command", "")
    if not re.search(r"\bgit\b", cmd):
        return

    for seg in re.split(r"&&|\|\||;|\n|\|", cmd):
        seg = seg.strip()
        m = re.search(r"\bgit\s+(?:-C\s+\S+\s+)?(add|commit|push|stage)\b(.*)", seg)
        if not m:
            continue
        verbe, reste = m.group(1), m.group(2)
        if verbe in ("add", "stage"):
            if re.search(r"(^|\s)(-f|--force)(\s|$)", reste):
                cibles = [t for t in reste.split() if not t.startswith("-")]
                if any(client(t) for t in cibles) or not cibles:
                    bloquer("git add --force sur des fichiers clients", cibles)
            cibles = [t for t in reste.split() if not t.startswith("-")]
            vises = [t for t in cibles if client(t)]
            if vises:
                bloquer("git add vise des fichiers clients", vises)
            if re.search(r"(^|\s)(-A|--all|\.|:/)(\s|$)", reste) or "-u" in reste.split():
                expo = [l[3:] for l in git("status", "--porcelain", "--untracked-files=all") if client(l[3:])]
                if expo:
                    bloquer("git add global alors que des fichiers clients ne sont pas ignorés", expo)
        if verbe in ("commit", "push"):
            indexes = [f for f in git("diff", "--cached", "--name-only") if client(f)]
            suivis = [f for f in git("ls-files") if client(f)]
            if re.search(r"(^|\s)(-a|--all|-am)(\s|$)", reste):
                indexes += [f for f in git("diff", "--name-only") if client(f)]
            if indexes or suivis:
                bloquer(f"git {verbe} avec des fichiers clients indexés ou suivis", sorted(set(indexes + suivis)))


if __name__ == "__main__":
    main()
