#!/usr/bin/env python3
"""Dit s'il faut proposer le ménage du digest, et pourquoi. N'affiche rien sinon.

  check_clean.py [dossier du projet]

L'âge se compte en jours de travail — les jours où l'utilisateur a écrit sur
ce projet — et non en jours de calendrier : un projet repris tous les quinze
jours aurait sinon l'air abandonné en permanence.
"""
import importlib.util
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# Une question qui n'a pas bougé pendant ce nombre de jours de travail traîne.
STALE_AFTER = 10
# À partir de ce nombre de questions qui traînent, proposer le ménage.
STALE_QUESTIONS = 5
# Sans ménage depuis ce nombre de jours de travail, le proposer quand même.
MENAGE_EVERY = 20
# « Plus tard » fait taire le rappel pendant ce nombre de jours de travail.
SNOOZE = 3

ITEM_START = re.compile(r"^(?:[-*]|\d+\.)\s+")
HERE = Path(__file__).resolve().parent


def load_import():
    spec = importlib.util.spec_from_file_location("digest_import", HERE / "import.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def open_question_lines(path):
    """Numéros de ligne (à partir de 1) où commence chaque question de « ## Ouvert »."""
    lines, inside = [], False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## "):
            inside = line.strip() == "## Ouvert"
        elif inside and ITEM_START.match(line):
            lines.append(n)
    return lines


def line_dates(repo, relpath):
    """Date de dernière modification de chaque ligne, d'après git blame. Une ligne non commitée date d'aujourd'hui."""
    out = git(repo, "blame", "--line-porcelain", "--", relpath)
    dates, current = [], None
    for line in out.splitlines():
        if line.startswith("author-time "):
            current = date.fromtimestamp(int(line.split()[1])).isoformat()
        elif line.startswith("\t"):
            dates.append(current)
    return dates


def since(days, iso):
    """Jours de travail écoulés après une date."""
    return sum(1 for d in days if d > iso)


def main():
    project = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    digest = project / ".digest"
    if not (digest / "sujets").is_dir():
        return
    os.chdir(project)
    days = load_import().working_days()
    today = date.today().isoformat()

    # Dépôt à part ou versionné avec le projet : le blame et le log ne se lancent pas au même endroit.
    if (digest / ".git").exists():
        repo, prefix, scope = digest, "", []
    else:
        repo, prefix, scope = project, ".digest/", ["--", ".digest"]

    stale = 0
    for f in sorted((digest / "sujets").glob("*.md")):
        dates = line_dates(repo, f"{prefix}sujets/{f.name}")
        for n in open_question_lines(f):
            written = dates[n - 1] if n - 1 < len(dates) and dates[n - 1] else today
            if since(days, written) >= STALE_AFTER:
                stale += 1

    last = git(repo, "log", "--grep=^Ménage", "-1", "--format=%as", *scope).strip()
    first = git(repo, "log", "--reverse", "--format=%as", *scope).split("\n")[0].strip()
    without = since(days, last or first or today)

    snooze = digest / "rappel"
    if snooze.exists() and since(days, snooze.read_text(encoding="utf-8").strip()) < SNOOZE:
        return

    if stale >= STALE_QUESTIONS:
        why = f"{stale} questions n'ont pas bougé depuis {STALE_AFTER} jours de travail"
    elif without >= MENAGE_EVERY:
        why = f"{without} jours de travail sans ménage"
    else:
        return
    print(f"Rappel ménage : {why}. Propose `/digest clean` en une ligne au début de ta première réponse, "
          f"sans interrompre la demande. Si l'utilisateur répond « plus tard », écris la date du jour dans "
          f".digest/rappel.")


if __name__ == "__main__":
    main()
