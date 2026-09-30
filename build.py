#!/usr/bin/env python3
"""Génère la vue d'ensemble d'un digest à partir de ses fiches.

  build.py <dossier .digest> --projet <nom>

Lit <dossier>/sujets/*.md, écrit <dossier>/tableau.html et tient à jour
<dossier>/etat.json : un instantané par jour, pour que la ligne « Depuis le … »
compare avec le dernier jour de travail, et non avec la génération d'il y a
cinq minutes.

La page est générée, jamais retouchée à la main : une page écrite à la main
dérive des fiches en une semaine.
"""
import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path

MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
ITEM_START = re.compile(r"^(?:[-*]|\d+\.)\s+")


# --- Lecture des fiches ------------------------------------------------------

def read_record(path):
    raw = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        raw = raw[m.end():]
    sections, current = {}, None
    for line in raw.splitlines():
        if current is None and line.startswith("# ") and "titre" not in meta:
            meta["titre"] = line[2:].strip()
            continue
        h = re.match(r"^##\s+(.+?)\s*$", line)
        if h:
            current = h.group(1)
            sections[current] = []
        elif current:
            sections[current].append(line)
    nom = meta.get("nom") or path.stem
    maj = meta.get("maj") or datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    record = {
        "nom": nom,
        "titre": meta.get("titre") or nom,
        "genre": meta.get("genre", ""),
        "maj": maj,
        "quoi": first_paragraph(sections.get("Ce que c'est", [])),
    }
    for key, section in (("ouvert", "Ouvert"), ("a_faire", "À faire"), ("fait", "Fait"),
                         ("decide", "Décidé"), ("ecarte", "Écarté")):
        record[key] = [split_item(t, record, i) for i, t in enumerate(items_of(sections.get(section, [])))]
    return record


def first_paragraph(lines):
    para = []
    for line in lines:
        if not line.strip():
            if para:
                break
            continue
        para.append(line.strip())
    return " ".join(para)


def items_of(lines):
    """Un élément commence par une puce en colonne 0 ; les lignes indentées ou vides le prolongent."""
    items, cur = [], None
    for line in lines:
        if ITEM_START.match(line):
            if cur:
                items.append(cur)
            cur = [ITEM_START.sub("", line, count=1)]
        elif cur is not None and (line.startswith((" ", "\t")) or not line.strip()):
            cur.append(line[2:] if line.startswith("  ") else line.lstrip("\t"))
        elif cur is not None:
            items.append(cur)
            cur = None
    if cur:
        items.append(cur)
    return ["\n".join(i).strip() for i in items]


def split_item(text, record, index):
    """Sépare le titre (le premier passage en gras) du détail."""
    t = text
    bloquant = False
    m = re.match(r"\(bloquant\)\s*", t, re.I)
    if m:
        bloquant, t = True, t[m.end():]
    m = re.match(r"\*\*\[[^\]]+\]\*\*\s*", t)
    if m:
        t = t[m.end():]
    m = re.match(r"\*\*(.+?)\*\*", t, re.S)
    # Un gras suivi d'une minuscule n'est qu'un début de phrase : le titre est alors la phrase entière.
    if m and t[m.end():].lstrip(" \n—–:-")[:1].islower():
        m = None
    if m and len(m.group(1)) <= 240:
        title = " ".join(m.group(1).split())
        detail = t[m.end():].lstrip(" \n—–:-")
    else:
        m = re.match(r"(.+?[.?!])(?=\s|$)", t, re.S)
        first = " ".join((m.group(1) if m else t).split())
        if len(first) > 180:
            title, detail = first[:170].rsplit(" ", 1)[0] + "…", t
        else:
            title, detail = first, t[m.end():].strip() if m else ""
    return {"titre": title, "detail": detail.strip(), "bloquant": bloquant,
            "sujet": record["nom"], "sujet_titre": record["titre"], "maj": record["maj"], "rang": index}


# --- Rendu markdown minimal --------------------------------------------------

def inline(s):
    s = html.escape(s, quote=False)
    codes = []

    def keep(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", keep, s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s, flags=re.S)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m.group(1))]}</code>", s)


def blocks(text):
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        if all(ITEM_START.match(l.lstrip()) or l.startswith("  ") for l in lines) and ITEM_START.match(lines[0].lstrip()):
            lis, cur = [], []
            for l in lines:
                if ITEM_START.match(l.lstrip()) and not l.startswith("    "):
                    if cur:
                        lis.append(" ".join(cur))
                    cur = [ITEM_START.sub("", l.lstrip(), count=1)]
                else:
                    cur.append(l.strip())
            lis.append(" ".join(cur))
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lis) + "</ul>")
        else:
            out.append(f"<p>{inline(' '.join(l.strip() for l in lines))}</p>")
    return "".join(out)


def plain(s):
    return re.sub(r"[*`]", "", s)


def norm(s):
    return re.sub(r"[^a-z0-9àâäéèêëïîôöùûüç]+", " ", plain(s).lower()).strip()


def jour(iso):
    d = datetime.fromisoformat(iso[:16])
    return f"{d.day} {MOIS[d.month - 1]}"


# --- Assemblage --------------------------------------------------------------

def statut(r):
    if r["ouvert"]:
        return "trancher", "À trancher"
    if r["a_faire"]:
        return "faire", "Décidé, à faire"
    return "fait", "Fait"


def by_recency(items, records):
    """Bloquant d'abord, puis le sujet modifié le plus récemment, puis l'ordre de la fiche."""
    order = {r["nom"]: i for i, r in enumerate(records)}
    return sorted(items, key=lambda it: (not it["bloquant"], order[it["sujet"]], it["rang"]))


def esc(s):
    return html.escape(s, quote=True)


def resume_button(it, primary=False):
    cmd = f"/digest {it['sujet']} — {plain(it['titre'])}"
    cls = "resume resume--primary" if primary else "resume"
    return f'<button type="button" class="{cls}" data-cmd="{esc(cmd)}">Copier la commande</button>'


def question(it, with_subject=True, with_flag=False, button=True):
    tag = f'<span class="tag">{esc(it["sujet_titre"])}</span>' if with_subject else ""
    flag = '<span class="flag">bloquant</span>' if with_flag and it["bloquant"] else ""
    body = blocks(it["detail"]) if it["detail"] else '<p class="muted">Pas de détail dans la fiche.</p>'
    btn = resume_button(it) if button else ""
    return (f'<li><details class="item{" item--bloc" if it["bloquant"] else ""}"><summary>'
            f'<span class="item-meta">{flag}{tag}</span>'
            f'<span class="item-title">{inline(it["titre"])}</span></summary>'
            f'<div class="item-body">{body}{btn}</div></details></li>')


def settled(items, label):
    """Décidé ou Écarté d'un sujet : replié, un titre par ligne, le détail au clic."""
    if not items:
        return ""
    lis = "".join(question(it, with_subject=False, button=False) for it in items)
    return (f'<details class="settled"><summary>{label}<span class="n">{len(items)}</span></summary>'
            f'<ul class="items">{lis}</ul></details>')


def diff(before, records):
    now_open = {(r["titre"], norm(it["titre"])) for r in records for it in r["ouvert"]}
    now_todo = {(r["titre"], norm(it["titre"])) for r in records for it in r["a_faire"]}
    prev_open = {tuple(x) for x in before["open"]}
    prev_todo = {tuple(x) for x in before["todo"]}
    titles = {(r["titre"], norm(it["titre"])): (it["titre"], r["titre"])
              for r in records for it in r["ouvert"] + r["a_faire"] + r["decide"] + r["fait"] + r["ecarte"]}

    def named(keys):
        return sorted((titles.get(k, (k[1].capitalize(), k[0])) for k in keys), key=lambda x: x[1])

    return {
        "depuis": before["generated"],
        "tranchees": named(prev_open - now_open),
        "faites": named(prev_todo - now_todo),
        "nouvelles": named(now_open - prev_open),
    }


def build(records, projet, before, generated):
    records.sort(key=lambda r: r["maj"], reverse=True)
    ouvert = by_recency([it for r in records for it in r["ouvert"]], records)
    a_faire = by_recency([it for r in records for it in r["a_faire"]], records)
    n_bloc = sum(it["bloquant"] for it in ouvert)

    parts = []
    # En-tête et « Depuis le … »
    changes = ('<div class="since since--first"><span class="since-label">Premier jour</span>'
               '<span class="muted">Dès le prochain jour de travail, cette ligne dira ce qui a été tranché, '
               'fait ou ajouté.</span></div>')
    if before:
        d = diff(before, records)
        chips = (f'<span class="chip chip--good">{len(d["tranchees"])} tranchées</span>'
                 f'<span class="chip chip--good">{len(d["faites"])} faites</span>'
                 f'<span class="chip chip--new">{len(d["nouvelles"])} nouvelles</span>')

        def lst(label, xs):
            if not xs:
                return ""
            li = "".join(f'<li><span class="tag">{esc(s)}</span> {inline(t)}</li>' for t, s in xs)
            return f'<h4>{label}</h4><ul class="changes-list">{li}</ul>'

        if d["tranchees"] or d["faites"] or d["nouvelles"]:
            changes = (f'<details class="since"><summary><span class="since-label">Depuis le {jour(d["depuis"])}</span>'
                       f'<span class="chips">{chips}</span></summary>'
                       f'<div class="since-body">{lst("Tranchées", d["tranchees"])}{lst("Faites", d["faites"])}'
                       f'{lst("Nouvelles", d["nouvelles"])}</div></details>')
        else:
            changes = (f'<div class="since since--first"><span class="since-label">Depuis le {jour(d["depuis"])}</span>'
                       f'<span class="muted">Rien n’a été tranché, fait ou ajouté.</span></div>')
    parts.append(
        f'<header class="mast"><p class="eyebrow">Digest · {esc(projet)}</p>'
        f'<h1>Ce qui t’attend</h1>'
        f'<div class="tally"><div class="t-q"><b>{len(ouvert)}</b><span>à trancher</span>'
        f'<em>dont {n_bloc} bloquantes</em></div>'
        f'<div class="t-w"><b>{len(a_faire)}</b><span>à faire</span></div></div>'
        f'{changes}</header>')

    # Prochaine décision
    if ouvert:
        nxt = ouvert[0]
        rule = ("Choisie parmi les bloquantes, dans le sujet modifié le plus récemment." if nxt["bloquant"] else
                "Aucune question n'est marquée bloquante : c'est la première du sujet modifié le plus récemment.")
        body = blocks(nxt["detail"]) if nxt["detail"] else ""
        flag = '<span class="flag">bloquant</span>' if nxt["bloquant"] else ""
        detail = f'<details class="next-detail"><summary>Lire le détail</summary>{body}</details>' if body else ""
        parts.append(
            f'<section class="next" aria-labelledby="next-h"><h2 id="next-h" class="label">Prochaine décision</h2>'
            f'<article class="next-card"><p class="item-meta">{flag}<span class="tag">{esc(nxt["sujet_titre"])}</span></p>'
            f'<h3>{inline(nxt["titre"])}</h3>{detail}{resume_button(nxt, primary=True)}'
            f'<p class="hint">Colle-la dans le terminal : Claude reprend la discussion sur cette question.</p>'
            f'<p class="rule">{rule}</p></article></section>')
    else:
        parts.append('<section class="next"><h2 class="label">Prochaine décision</h2>'
                     '<p class="empty">Rien à trancher. Les questions ouvertes apparaîtront ici.</p></section>')

    # Sujets : ceux qui ont encore quelque chose à trancher ou à faire, puis les terminés, repliés
    def subject_row(r):
        key, lab = statut(r)
        counts = f'{len(r["ouvert"])} à trancher · {len(r["a_faire"])} à faire'
        row = (
            f'<li><details class="subject"><summary>'
            f'<span class="s-name">{esc(r["titre"])}<small>{esc(r["genre"])}</small></span>'
            f'<span class="status status--{key}">{lab}</span>'
            f'<span class="s-counts">{counts}</span>'
            f'<span class="s-date">{jour(r["maj"])}</span></summary>'
            f'<div class="subject-body"><p>{inline(r["quoi"]) or "Pas de description dans la fiche."}</p>'
            f'{settled(r["decide"], "Décidé")}{settled(r["ecarte"], "Écarté")}'
            f'<p class="muted"><code>{esc(r["nom"])}</code></p></div></details></li>')
        return row

    actifs = [r for r in records if statut(r)[0] != "fait"]
    termines = [r for r in records if statut(r)[0] == "fait"]
    liste = f'<ul class="subjects">{"".join(subject_row(r) for r in actifs)}</ul>' if actifs else ""
    if termines:
        liste += (f'<details class="group group--done"><summary>Terminés<span class="n">{len(termines)}</span></summary>'
                  f'<ul class="subjects">{"".join(subject_row(r) for r in termines)}</ul></details>')
    parts.append(f'<section aria-labelledby="sujets-h"><h2 id="sujets-h" class="label">Sujets '
                 f'<span class="n">{len(records)}</span></h2>{liste}</section>')

    # Bloquantes, puis les autres questions groupées par sujet
    rest = ouvert[1:]
    bloc = [it for it in rest if it["bloquant"]]
    if bloc:
        parts.append(f'<section aria-labelledby="bloc-h"><h2 id="bloc-h" class="label">Bloquantes '
                     f'<span class="n">{len(bloc)}</span></h2><ul class="items">'
                     + "".join(question(it) for it in bloc) + "</ul></section>")
    others = [it for it in rest if not it["bloquant"]]
    if others:
        groups = []
        for r in records:
            its = [it for it in others if it["sujet"] == r["nom"]]
            if its:
                groups.append(f'<li><details class="group"><summary>{esc(r["titre"])}<span class="n">{len(its)}</span>'
                              f'</summary><ul class="items">{"".join(question(it, with_subject=False) for it in its)}'
                              f'</ul></details></li>')
        parts.append(f'<section aria-labelledby="autres-h"><h2 id="autres-h" class="label">Autres questions '
                     f'<span class="n">{len(others)}</span></h2><ul class="groups">{"".join(groups)}</ul></section>')

    # À faire
    if a_faire:
        parts.append(f'<section aria-labelledby="faire-h"><h2 id="faire-h" class="label">À faire '
                     f'<span class="n">{len(a_faire)}</span></h2><ul class="items items--work">'
                     + "".join(question(it, with_flag=True, button=False) for it in a_faire) + "</ul></section>")

    parts.append(f'<footer>Générée le {jour(generated)} à {generated[11:16]} depuis {len(records)} fiches de '
                 f'<code>.digest/sujets/</code>. La page ne se modifie pas : une décision se prend dans le terminal, '
                 f'avec le bouton « Copier la commande ».</footer>')
    return PAGE.replace("{{PROJET}}", esc(projet)).replace("{{BODY}}", "\n".join(parts))


def load_days(path):
    """Instantanés par jour. Accepte l'ancien format à un seul état."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "jours" in data:
        return data["jours"]
    return {data["generated"][:10]: data}


def state_of(records, generated):
    return {"generated": generated,
            "open": [[r["titre"], norm(it["titre"])] for r in records for it in r["ouvert"]],
            "todo": [[r["titre"], norm(it["titre"])] for r in records for it in r["a_faire"]]}


PAGE = r"""<title>Vue d’ensemble {{PROJET}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Une colonne, lue dans une fenêtre étroite à côté du terminal : le résumé, puis le détail replié. */
:root {
  --key:#14161F; --paper:#F2F4F8; --surface:#FFFFFF; --surface-2:#E9ECF3;
  --line:#D3D9E6; --muted:#5F677D; --cyan:#0E6BBF; --magenta:#C41E63; --good:#1E7A5A;
  --shadow:0 1px 2px rgba(20,22,31,.06), 0 8px 24px -16px rgba(20,22,31,.28);
  --f-display:"Bricolage Grotesque", system-ui, sans-serif;
  --f-body:"Source Sans 3", "Helvetica Neue", Arial, sans-serif;
  --f-mono:"IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --key:#E3E7F1; --paper:#0F1118; --surface:#171A24; --surface-2:#1F2430;
    --line:#2C3242; --muted:#9098AE; --cyan:#5EAEF5; --magenta:#F2679B; --good:#4FC39A;
    --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7); color-scheme:dark;
  }
}
:root[data-theme="dark"] {
  --key:#E3E7F1; --paper:#0F1118; --surface:#171A24; --surface-2:#1F2430;
  --line:#2C3242; --muted:#9098AE; --cyan:#5EAEF5; --magenta:#F2679B; --good:#4FC39A;
  --shadow:0 1px 2px rgba(0,0,0,.4), 0 8px 24px -16px rgba(0,0,0,.7); color-scheme:dark;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--key);
  font:400 16px/1.55 var(--f-body); -webkit-font-smoothing:antialiased; }
.wrap { max-width:46rem; margin:0 auto; padding-inline:clamp(16px, 4vw, 28px); padding-block:28px 88px;
  display:flex; flex-direction:column; gap:40px; }
code { font-family:var(--f-mono); font-size:.86em; background:var(--surface-2); padding:.05em .3em; border-radius:2px; }
a { color:var(--cyan); }
.muted, .rule { color:var(--muted); }
ul { margin:0; padding:0; list-style:none; }

/* En-tête */
.mast { display:flex; flex-direction:column; gap:14px; padding-bottom:22px; border-bottom:2px solid var(--key); }
.eyebrow, .label, .tag, .flag, .status, .s-date, .since-label, footer, .rule {
  font-family:var(--f-mono); letter-spacing:.08em; }
.eyebrow { margin:0; font-size:11px; text-transform:uppercase; color:var(--muted); }
h1 { font-family:var(--f-display); font-weight:800; font-size:clamp(32px, 7vw, 46px); line-height:1;
  letter-spacing:-.025em; margin:0; text-wrap:balance; }
.tally { display:flex; flex-wrap:wrap; gap:12px 36px; }
.tally div { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }
.tally b { font-family:var(--f-display); font-weight:700; font-size:40px; line-height:1; font-variant-numeric:tabular-nums; }
.t-q b { color:var(--magenta); } .t-w b { color:var(--cyan); }
.tally span { font-family:var(--f-mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); }
.tally em { font-style:normal; font-size:14px; color:var(--muted); }

/* Depuis le … */
.since { background:var(--surface); border:1px solid var(--line); border-radius:3px; }
.since--first { display:flex; flex-wrap:wrap; align-items:center; gap:6px 14px; padding:12px 14px; font-size:15px; }
.since > summary { display:flex; flex-wrap:wrap; align-items:center; gap:8px 14px; padding:12px 14px; cursor:pointer; min-height:44px; }
.since-label { font-size:11px; text-transform:uppercase; color:var(--muted); }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip { font-size:14px; font-weight:600; padding:2px 9px; border-radius:999px; border:1px solid currentColor; }
.chip--good { color:var(--good); } .chip--new { color:var(--magenta); }
.since-body { padding:4px 16px 16px; border-top:1px solid var(--line); }
.since-body h4 { font-family:var(--f-mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); margin:16px 0 8px; font-weight:500; }
.changes-list { display:flex; flex-direction:column; gap:6px; font-size:15px; }
.changes-list .tag { margin-right:6px; }

/* Libellés de section */
.label { font-size:11px; font-weight:500; text-transform:uppercase; color:var(--muted); margin:0 0 12px;
  display:flex; align-items:center; gap:8px; }
.n { font-family:var(--f-mono); font-size:11px; color:var(--key); background:var(--surface-2);
  border-radius:999px; padding:1px 8px; letter-spacing:0; }
.tag { font-size:11px; color:var(--muted); }
.flag { font-size:10px; text-transform:uppercase; color:var(--magenta); border:1px solid currentColor;
  border-radius:2px; padding:1px 6px; }
.item-meta { display:flex; flex-wrap:wrap; align-items:center; gap:8px; margin:0; }

/* Prochaine décision */
.next-card { background:var(--surface); border:2px solid var(--key); border-radius:4px; padding:22px 22px 18px;
  box-shadow:var(--shadow); display:flex; flex-direction:column; gap:12px; }
.next-card h3 { font-family:var(--f-display); font-weight:700; font-size:clamp(21px, 4.5vw, 26px); line-height:1.2;
  letter-spacing:-.015em; margin:0; text-wrap:balance; }
.next-detail > summary { cursor:pointer; color:var(--cyan); font-weight:600; min-height:44px; display:flex; align-items:center; }
.next-detail p, .item-body p { margin:0 0 10px; max-width:65ch; }
.next-detail ul, .item-body ul { list-style:disc; padding-left:1.2em; margin:0 0 10px; }
.rule { font-size:11px; margin:0; }
.hint { margin:0; font-size:15px; color:var(--muted); }
.empty { color:var(--muted); font-style:italic; border:1px dashed var(--line); border-radius:3px; padding:16px 18px; margin:0; }

/* Bouton Reprendre : 44 px de haut, annoncé aux lecteurs d'écran */
.resume { align-self:flex-start; min-height:44px; padding:0 18px; font:600 15px/1 var(--f-body); cursor:pointer;
  color:var(--key); background:var(--surface-2); border:1px solid var(--line); border-radius:3px; }
.resume:hover { border-color:var(--key); }
.resume--primary { background:var(--key); color:var(--surface); border-color:var(--key); }
.resume--primary:hover { opacity:.9; }
.resume.ok { background:var(--good); border-color:var(--good); color:#fff; }
:focus-visible { outline:2px solid var(--cyan); outline-offset:2px; }
.fallback { font-family:var(--f-mono); font-size:13px; background:var(--surface-2); padding:8px 10px; border-radius:3px;
  overflow-x:auto; white-space:pre; user-select:all; }

/* Éléments dépliables */
summary { list-style:none; }
summary::-webkit-details-marker { display:none; }
.items { display:flex; flex-direction:column; gap:8px; }
.item { background:var(--surface); border:1px solid var(--line); border-radius:3px; }
.item--bloc { border-left:4px solid var(--magenta); }
.item > summary { display:flex; flex-direction:column; gap:4px; padding:12px 14px 12px 36px; cursor:pointer;
  position:relative; min-height:44px; }
.item > summary::before, .subject > summary::before, .group > summary::before {
  content:""; position:absolute; left:14px; top:19px; width:7px; height:7px;
  border-right:2px solid var(--muted); border-bottom:2px solid var(--muted); transform:rotate(-45deg);
  transition:transform .15s ease; }
details[open] > summary::before { transform:rotate(45deg); }
.item-title { font-weight:600; font-size:16px; line-height:1.35; }
.item-body { padding:0 16px 16px 36px; display:flex; flex-direction:column; font-size:15px; }
.items--work .item > summary .item-title { font-weight:400; }

/* Sujets */
.subjects { background:var(--surface); border:1px solid var(--line); border-radius:3px; }
.subjects > li + li { border-top:1px solid var(--line); }
.subject > summary { display:grid; grid-template-columns:minmax(0, 1fr) auto; gap:4px 12px; align-items:center;
  padding:12px 14px 12px 36px; cursor:pointer; position:relative; min-height:44px; }
.subject > summary::before { top:20px; }
.s-name { font-weight:600; min-width:0; }
.s-name small { font-family:var(--f-mono); font-size:10.5px; font-weight:400; letter-spacing:.06em; color:var(--muted); margin-left:8px; }
.s-counts { font-size:14px; color:var(--muted); grid-column:1; font-variant-numeric:tabular-nums; }
.s-date { font-size:11px; color:var(--muted); grid-column:2; grid-row:2; justify-self:end; }
.status { font-size:10px; text-transform:uppercase; padding:3px 7px; border-radius:2px; border:1px solid currentColor;
  white-space:nowrap; justify-self:end; }
.status--trancher { color:var(--magenta); } .status--faire { color:var(--cyan); } .status--fait { color:var(--good); }
.subject-body { padding:0 16px 14px 36px; font-size:15px; }
.subject-body p { margin:0 0 8px; max-width:65ch; }
.subject-body { display:flex; flex-direction:column; gap:8px; }
.subject-body > p { margin:0; }
.settled > summary { display:flex; align-items:center; gap:8px; padding:8px 12px 8px 32px; cursor:pointer;
  position:relative; min-height:44px; font-family:var(--f-mono); font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); border:1px solid var(--line); border-radius:3px; }
.settled > summary::before { content:""; position:absolute; left:13px; top:18px; width:6px; height:6px;
  border-right:2px solid var(--muted); border-bottom:2px solid var(--muted); transform:rotate(-45deg);
  transition:transform .15s ease; }
.settled[open] > .items { padding:8px 0 4px; }
.settled .item-title { font-weight:400; font-size:15px; }

/* Groupes par sujet */
.groups { display:flex; flex-direction:column; gap:8px; }
.group > summary { display:flex; align-items:center; gap:8px; padding:12px 14px 12px 36px; cursor:pointer;
  position:relative; min-height:44px; font-weight:600; background:var(--surface-2); border-radius:3px; }
.group > summary::before { top:19px; }
.group[open] > .items { padding:8px 0 4px 12px; }
.group--done { margin-top:8px; }
.group--done[open] > .subjects { margin-top:8px; }

footer { font-size:11px; line-height:1.7; color:var(--muted); border-top:1px solid var(--line); padding-top:18px; letter-spacing:.04em; }
footer code { background:none; padding:0; }

@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style>
<div class="wrap">
{{BODY}}
</div>
<p class="sr-only" id="live" aria-live="polite" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></p>
<script>
  const live = document.getElementById('live');
  document.querySelectorAll('.resume').forEach((button) => {
    button.addEventListener('click', async () => {
      const cmd = button.dataset.cmd;
      try {
        await navigator.clipboard.writeText(cmd);
        button.textContent = 'Commande copiée';
        button.classList.add('ok');
        live.textContent = 'Commande copiée. Colle-la dans le terminal.';
        setTimeout(() => { button.textContent = 'Copier la commande'; button.classList.remove('ok'); }, 1600);
      } catch (e) {
        // Presse-papiers refusé : afficher la commande sélectionnée, prête pour ⌘C.
        let box = button.nextElementSibling;
        if (!box || !box.classList.contains('fallback')) {
          box = document.createElement('code');
          box.className = 'fallback';
          box.textContent = cmd;
          button.after(box);
        }
        const range = document.createRange();
        range.selectNodeContents(box);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        live.textContent = 'Commande sélectionnée. Copie-la avec Cmd C.';
      }
    });
  });
</script>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("digest")
    ap.add_argument("--projet", required=True)
    a = ap.parse_args()
    root = Path(a.digest)
    generated = datetime.now().strftime("%Y-%m-%dT%H:%M")
    today = generated[:10]
    records = [read_record(p) for p in sorted((root / "sujets").glob("*.md"))]
    days = load_days(root / "etat.json")
    earlier = sorted(d for d in days if d < today)
    before = days[earlier[-1]] if earlier else None
    (root / "tableau.html").write_text(build(records, a.projet, before, generated), encoding="utf-8")
    days[today] = state_of(records, generated)
    # Trente jours suffisent : on ne compare qu'avec le dernier jour de travail.
    days = {d: days[d] for d in sorted(days)[-30:]}
    (root / "etat.json").write_text(json.dumps({"jours": days}, ensure_ascii=False, indent=0), encoding="utf-8")
