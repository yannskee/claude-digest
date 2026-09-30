#!/bin/sh
# Hook SessionStart du digest, posé dans .claude/settings.local.json quand
# l'activation automatique est choisie. Ce qu'il affiche entre dans le
# contexte de Claude à l'ouverture de la session. Claude Code lui passe sur
# l'entrée standard un JSON avec l'id de la session qui démarre.
project="${CLAUDE_PROJECT_DIR:-$PWD}"
dir="$project/.digest"
[ -d "$dir" ] || exit 0
input=$(cat)
here="$(dirname "$0")"
open=$(cat "$dir"/sujets/*.md 2>/dev/null | awk '/^## /{o=/^## Ouvert/} o && /^- /{n++} END{print n+0}')
echo "Ce dépôt a un digest en activation automatique (.digest/, ${open:-0} question(s) ouverte(s)). Charge le skill digest avant ta première réponse, puis tiens-le à jour au fil de la conversation."
python3 "$here/check_clean.py" "$project" 2>/dev/null
printf '%s' "$input" | python3 "$here/check_recap.py" "$project" 2>/dev/null
echo "S'il y a plusieurs rappels ci-dessus, n'en fais qu'une ligne pour l'utilisateur."
