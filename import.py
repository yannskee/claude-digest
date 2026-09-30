#!/usr/bin/env python3
"""Sessions Claude Code archivées du dépôt courant.

  import.py            liste les sessions, la plus récente d'abord
  import.py --count    nombre de sessions passées et date de la plus ancienne
  import.py <id>       conversation seule d'une session (un préfixe d'id suffit)
  import.py --jours    jours de travail : les jours où l'utilisateur a écrit sur ce projet

La session en cours est la plus récente et s'écrit encore : elle est marquée
dans la liste et exclue du compte.
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Un fichier modifié il y a moins de ce délai est considéré comme la session en cours.
CURRENT_SESSION_WINDOW = 600
# Au-delà, un message est tronqué : un collage de logs n'apporte rien à l'import.
MAX_MESSAGE_CHARS = 3000

NOISE = re.compile(
    r"<(system-reminder|local-command-stdout|local-command-caveat|bash-stdout|bash-stderr)>.*?</\1>",
    re.S,
)


def archive_dir():
    """Claude Code range les sessions sous <config>/projects/<chemin du projet, non alphanumériques → ->.

    <config> vaut ~/.claude, ou le dossier de CLAUDE_CONFIG_DIR quand un second compte l'utilise.
    """
    config_dir = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
    candidates = [os.getcwd()]
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
        ).stdout.strip()
        candidates.append(root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    for path in candidates:
        d = config_dir / "projects" / re.sub(r"[^A-Za-z0-9-]", "-", path)
        if d.is_dir():
            return d
    return None


def sessions():
    d = archive_dir()
    if d is None:
        return [], None
    files = sorted(d.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    current = files[0] if files and time.time() - files[0].stat().st_mtime < CURRENT_SESSION_WINDOW else None
    return files, current


def entries(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def summary(path):
    title, prompts, start = "", 0, None
    for o in entries(path):
        if o.get("type") == "ai-title":
            title = o.get("aiTitle", title)
        elif is_prompt(o):
            prompts += 1
            start = start or o.get("timestamp")
    return title, prompts, start


def is_prompt(o):
    if o.get("type") != "user" or o.get("isMeta") or o.get("isSidechain") or o.get("isCompactSummary"):
        return False
    return bool(user_text(o))


def user_text(o):
    content = (o.get("message") or {}).get("content")
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
    if not isinstance(content, str):
        return ""
    content = NOISE.sub("", content)
    content = re.sub(r"<bash-input>(.*?)</bash-input>", r"! \1", content, flags=re.S)
    content = re.sub(
        r"<command-name>(.*?)</command-name>.*?(?:<command-args>(.*?)</command-args>)?",
        lambda m: f"{m.group(1)} {m.group(2) or ''}".strip(),
        content,
        flags=re.S,
    )
    content = re.sub(r"</?command-[a-z]+>", "", content)
    return content.strip()


def working_days():
    """Les jours où l'utilisateur a écrit au moins un message sur ce projet, session en cours comprise."""
    files, _ = sessions()
    days = set()
    for f in files:
        with open(f, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                # Filtre textuel d'abord : parser chaque ligne des archives coûterait dix fois plus.
                if '"type":"user"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if is_prompt(o) and o.get("timestamp"):
                    days.add(o["timestamp"][:10])
    return sorted(days)


def assistant_text(o):
    content = (o.get("message") or {}).get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(b.get("text", "") for b in content if b.get("type") == "text").strip()


def clip(text):
    return text if len(text) <= MAX_MESSAGE_CHARS else text[:MAX_MESSAGE_CHARS] + " […]"


def day(ts):
    return ts[:10] if ts else "?"


def list_sessions():
    files, current = sessions()
    if not files:
        sys.exit(f"Aucune session archivée pour {os.getcwd()}")
    for f in files:
        title, prompts, start = summary(f)
        mark = "  ← session en cours" if f == current else ""
        size = f.stat().st_size / 1_000_000
        print(f"{f.stem[:8]}  {day(start)}  {prompts:3d} messages  {size:5.1f} Mo  {title}{mark}")


def count_sessions():
    files, current = sessions()
    past = [f for f in files if f != current]
    starts = [summary(f)[2] for f in past]
    oldest = min((s for s in starts if s), default=None)
    print(len(past), day(oldest))


def extract(prefix):
    files, _ = sessions()
    matches = [f for f in files if f.stem.startswith(prefix)]
    if len(matches) != 1:
        sys.exit(f"{len(matches)} session(s) pour « {prefix} »")
    last_speaker = None
    for o in entries(matches[0]):
        if o.get("isSidechain") or o.get("isMeta"):
            continue
        if o.get("isCompactSummary"):
            speaker, text = "Résumé de compaction", user_text(o)
        elif o.get("type") == "user":
            speaker, text = "Utilisateur", user_text(o)
        elif o.get("type") == "assistant":
            speaker, text = "Claude", assistant_text(o)
        else:
            continue
        if not text:
            continue
        if speaker != last_speaker:
            print(f"\n### {speaker} — {o.get('timestamp', '')[:16].replace('T', ' ')}\n")
            last_speaker = speaker
        print(clip(text))


if __name__ == "__main__":
    # Sortie coupée par un `head` : se taire au lieu d'afficher une trace.
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg is None:
        list_sessions()
    elif arg == "--count":
        count_sessions()
    elif arg == "--jours":
        print("\n".join(working_days()))
    else:
        extract(arg)
