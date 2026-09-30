#!/usr/bin/env python3
"""Dit s'il faut proposer le relevé de la session précédente. N'affiche rien sinon.

  echo '<json du hook>' | check_recap.py [dossier du projet]

Claude ne voit pas la fin d'une session : on rattrape donc au début de la
suivante. Le JSON que Claude Code passe au hook SessionStart donne l'id de la
session qui démarre, pour ne pas la prendre pour la précédente.
"""
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# En dessous, la session précédente n'a sans doute rien tranché : un « ok » ne mérite pas un relevé.
MIN_MESSAGES = 3
HERE = Path(__file__).resolve().parent


def load_import():
    spec = importlib.util.spec_from_file_location("digest_import", HERE / "import.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def last_update(project, digest):
    """Date du dernier commit du digest, quel que soit son mode de versionnement."""
    if (digest / ".git").exists():
        cmd = ["git", "-C", str(digest), "log", "-1", "--format=%cI"]
    else:
        cmd = ["git", "-C", str(project), "log", "-1", "--format=%cI", "--", ".digest"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    return datetime.fromisoformat(out) if out else None


def main():
    project = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    digest = project / ".digest"
    if not (digest / "sujets").is_dir():
        return
    try:
        hook = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        hook = {}
    # Après une compaction, c'est la même session qui continue : rien à rattraper.
    if hook.get("source") == "compact":
        return
    since = last_update(project, digest)
    if since is None:
        return

    os.chdir(project)
    imp = load_import()
    files, _ = imp.sessions()
    done = set()
    handled = digest / "releves"
    if handled.exists():
        done = set(handled.read_text(encoding="utf-8").split())
    previous = next((f for f in files if f.stem != hook.get("session_id")), None)
    if previous is None or previous.stem[:8] in done:
        return

    count, last = 0, None
    for o in imp.entries(previous):
        if imp.is_prompt(o) and o.get("timestamp"):
            ts = datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00"))
            if ts > since:
                count += 1
                last = ts
    if count < MIN_MESSAGES:
        return
    print(f"Relevé à proposer : la session précédente ({previous.stem[:8]}, {last.date().isoformat()}) compte "
          f"{count} messages après la dernière mise à jour du digest. Lance en arrière-plan un agent de relevé "
          f"(section « Faire un relevé » du skill) sur `import.py {previous.stem[:8]}`, réponds à la demande de "
          f"l'utilisateur, puis propose le résultat en une ligne. Une fois traité ou refusé, ajoute "
          f"{previous.stem[:8]} à .digest/releves.")


if __name__ == "__main__":
    main()
