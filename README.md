# claude-digest

A [Claude Code](https://claude.com/claude-code) skill that keeps a project's decisions from one session to the next: what was settled, what is still open, and what was dropped. Nothing gets debated twice.

> **The skill is written in French on purpose.** Its onboarding message and record format were tuned word by word in French. Claude reads it without trouble, but the onboarding and the records it writes will be in French. Translate `SKILL.md` if you need another language.

## What it does

- Keeps one Markdown record per subject in `.digest/sujets/`, at the root of your project. Claude writes to it as soon as you settle something, and tells you in one line what it wrote.
- Records a decision only if you said it yourself. Your silence never counts as agreement.
- Generates an overview page: what is left to decide, what is decided but not built, and the state of each subject. It is published as a claude.ai artifact, always at the same URL, so you can keep it open next to your terminal.
- Can summarize your past Claude Code sessions on the project, the way a colleague who was there would.

## Install

```sh
git clone https://github.com/yannskee/claude-digest ~/.claude/skills/digest
```

If you use `CLAUDE_CONFIG_DIR`, clone into `$CLAUDE_CONFIG_DIR/skills/digest` instead. Requires Python 3 and git. The overview page needs the claude.ai artifact tool; without it, the records still work.

## Use

| Command | What it does |
|---|---|
| `/digest` | Starts the onboarding on a new project, or shows the open questions |
| `/digest <subject>` | Resumes one subject |
| `/digest clean` | Proposes closing finished tasks and settling or dropping stale questions |
| `/digest disable` | Turns off automatic loading, or deletes the digest after archiving it |

During onboarding, you choose two settings:

- **Versioning**: commit the digest with your project, or keep it in its own git repository, invisible to your teammates.
- **Activation**: load the digest automatically at every session through a `SessionStart` hook in `.claude/settings.local.json`, or only when you type `/digest`.

## Files

| File | Role |
|---|---|
| `SKILL.md` | The instructions Claude follows |
| `build.py` | Generates the overview page from the records |
| `import.py` | Lists past sessions and extracts their conversation |
| `check_clean.py` | Decides when to suggest `/digest clean`, counting in working days |
| `check_recap.py` | Detects a previous session that was never summarized |
| `session-start.sh` | The hook that runs at the start of each session |

## License

MIT
