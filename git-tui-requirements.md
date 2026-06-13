# git-claude-tui — requirements & rationale

This document records *what* the tools must do and *why*, so a fresh session
(human or AI) can understand the design intent without re-deriving it. It is the
spec; the code in `bin/` is the implementation.

## Origin & purpose

The suite grew out of a crash-recovery problem: a developer with many local
git repositories (across **multiple git accounts** — two GitHub, one Bitbucket,
separated into personal vs work folders) wanted to know, at a glance:

- which repos have work that exists **only on the laptop** (uncommitted or unpushed) and would be lost in a crash;
- which repos are **manual copies** of each other, so redundant copies can be deleted safely;
- a visual **overview** of all repos and their state;
- for any one repo, **where unpushed work sits in history and time**, to judge whether it is still worth keeping.

Hard constraint throughout: the tools are **read-only** — they must never modify
the repositories they inspect.

## Global design decisions

1. **Zero runtime dependencies.** Bash + Python 3 stdlib only (notably
   `curses`). Rationale: must run on a freshly-installed machine (incl. NixOS)
   with nothing pip-installed.
2. **One shared scanner.** `git_repo_scan.py` holds all git logic; the Python
   tools import it from their own directory. Rationale: a single source of truth
   for status rules. Keep the file beside `git-map`/`git-tui`.
3. **Account detection by remote URL.** `gh` (personal github), `gh:first8`
   (work github via SSH host alias), `bitbucket`, `other`, `none`. Rationale:
   the user drives multiple accounts through SSH host aliases; the colour-coding
   must reflect *which* account a repo belongs to.
4. **Status taxonomy (per repo):** `clean` / `dirty` (uncommitted) /
   `unpushed` (committed but ahead of, or lacking, an upstream) / `no-remote`.
   These are independent of "dirty ≠ unpushed", which the user explicitly needed
   distinguished.

## Tool requirements

### `git-overview` (CLI table)
- R1. Scan all repos under one or more roots (default `~/git`); skip heavy dirs
  (`node_modules`, `.cache`, `.direnv`, …).
- R2. Per repo show: relative path, branch, dirty count (`±N`), ahead/behind,
  remote account, and attention flags.
- R3. **Fold away nested/submodule repos** by default (a repo inside another
  repo's tree); they are noise. Reveal with `--all`.
- R4. Summary counts of dirty / unpushed / no-remote at the end.

### `git-overview --copies` (duplicate analysis)
- R5. Group repos that are **copies of each other** by shared `origin` URL, or by
  root-commit when there is no remote.
- R6. For each copy compute a **working-tree state signature** (HEAD + tracked
  diff + untracked file names & sizes) so byte-identical copies are detected.
- R7. Verdict per copy: `SAFE TO DELETE` only when it has **no unique unpushed
  commits AND no uncommitted changes**, or when it is **identical to** another
  listed copy. Otherwise `KEEP` with the reason. Rationale: the user keeps manual
  copies as snapshots and needs to know which are truly redundant.

### `git-map` (SVG "subway map")
- R8. Render every repo as an SVG: folder hierarchy = grey spines, repos =
  stations, **account = ring colour**, **status = fill**, copies = double-ring
  interchanges, with a legend. Rationale: a printable big-picture view.
- R9. Self-contained SVG (opens in a browser); no rasteriser dependency.

### `git-tui` (interactive)
- R10. Browse the repo tree; expand/collapse folders; colour/shape per the
  status encoding; badges `±N` / `↑N` / `⇄N`.
- R11. Filters: dirty-only, unpushed-only, copies-only, all; jump to next copy.
- R12. `o` prints the selected repo path and exits, for `cd "$(git-tui)"`.
- R13. An always-on **legend** (top-right, toggle `?`) documenting every symbol —
  the encoding must be self-explanatory.
- R14. `--list` plain-text mode for non-tty / piping; degrade gracefully where
  curses can't run.

### `git-tui` drill-down (per-repo history)
- R15. `→`/Enter on a repo opens a detail view showing the repo's history.
- R16. **Show topology, not just time.** The view must render the actual commit
  **DAG** — forks, merges, dead-end branches — because branches share history and
  a pure time-projection collapses them into identical-looking lines. Implemented
  by styling `git log --graph` output (git computes the layout) as a coloured map:
  lanes coloured per column, `●` pushed / `◆` unpushed nodes, `[refs]` for branch
  /tag tips (incl. `origin/*` to show where the remote is).
- R17. **Unpushed-in-time judgement.** The user must be able to tell that an
  unpushed commit is e.g. years old while recent work exists elsewhere (→ safe to
  drop) vs recent (→ keep). Commit rows carry relative dates; unpushed nodes are
  visually distinct.
- R18. **Working-tree clarity.** Uncommitted changes live in the working tree on
  the current branch, *on top of HEAD*, and are not in any commit. The view must:
  - draw a **`✎` working-tree stub branching off HEAD** listing the changed files;
  - state **which branch** and **which HEAD commit** the changes sit on;
  - **distinguish staged (git-added) vs modified-unstaged vs untracked** files, so
    an empty `git diff` (everything staged) is not confusing;
  - offer **`d` to view the diff**, showing `git diff --cached` (staged) and
    `git diff` (unstaged) as clearly-labelled, separately-coloured sections.

## Status / symbol encoding (canonical)

| Symbol | Meaning |
|--------|---------|
| ring/glyph colour | account: personal gh / work gh / bitbucket / other |
| `○` `●` `◆` `◌` | clean / dirty / unpushed / no-remote (overview & map) |
| `●` `◆` (graph) | pushed / unpushed commit |
| `✎` | working-tree (uncommitted) stub |
| `+ ~ ?` | staged / modified-unstaged / untracked file |
| `±N` `↑N` `⇄N` | files changed / commits unpushed / copy-group N |
| `\| / \\` | commit-graph lanes / fork / merge |

## Known constraints / non-goals

- The commit graph is **vertical** (topology, newest→oldest top-to-bottom), not a
  horizontal time-axis. Combining true DAG topology *and* horizontal date
  positioning is a much harder custom layout problem and is deliberately not done.
- `git()` calls have a 30s timeout; very large repos cap commit/graph fetches.

## Related but out of scope (planned, not in this repo)

A separate effort covers backing up and restoring Claude Code conversations and
project notes via a private "vault" repo and snapshot tooling. These tools only
*surface* repo state; they do not back anything up.
