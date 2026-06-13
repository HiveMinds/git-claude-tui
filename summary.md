# Conversation summary

A summary of how `git-claude-tui` came to be, for context in future sessions.
(No private/identifying data is included here.)

## Starting point

The work began as a broader question: setting up a new machine and wanting a
clean, reproducible way to survive a crash — including restoring tooling state,
keeping project notes private, managing several git accounts, and getting an
overview of which repositories had unsaved or unpushed work. The repo-overview
need was carved off first and became this tool suite. (The backup/restore
"vault" side of that discussion is separate and not part of this repo.)

## What was built, in order

1. **`git-overview`** — a read-only Bash survey of every repo under given roots:
   branch, dirty count, ahead/behind, which account the remote belongs to, and
   flags for repos needing attention. Nested/submodule repos are folded away by
   default to cut noise.

2. **`git-overview --copies`** — groups repos that are copies of one another
   (same origin or root commit) and judges which copies are safe to delete. A
   per-copy working-tree signature detects byte-identical duplicates; a copy is
   only "safe to delete" if it has no unique unpushed commits and no uncommitted
   changes (or is identical to another copy). This supports a workflow of keeping
   manual snapshot copies and later pruning the redundant ones.

3. **`git-map`** — renders all repos as a self-contained SVG "subway map":
   folders as spines, repos as stations coloured by account, status as fill,
   copies as interchange rings, with a legend. No rasteriser dependency.

4. **`git-tui`** — an interactive `curses` browser of the repo tree (filters,
   legend, jump-to-copy, `cd`-on-exit, and a `--list` fallback), plus a
   per-repo drill-down.

## Drill-down evolution (the interesting part)

The per-repo view went through three iterations driven by feedback:

- v1: a single merged timeline of all commits by date.
- v2: per-branch parallel "swim-lanes" — rejected, because branches share
  history so the lanes looked identical; it showed *time*, not *topology*.
- v3 (current): the real commit **DAG**, by styling `git log --graph` output
  into a coloured map — forks, merges, dead-end branches, `●` pushed / `◆`
  unpushed nodes, and branch/tag labels (including remote tips). This finally
  shows where unpushed work diverges and lets the user judge, with relative
  dates, whether old unpushed work is safe to discard.

Then a **working-tree** view was added: uncommitted changes are drawn as a `✎`
stub branching off HEAD, naming the branch and base commit and splitting files
into staged / modified-unstaged / untracked, with a `d` diff viewer showing
staged vs unstaged diffs separately — clarifying the common confusion where
"uncommitted changes" exist but `git diff` is empty because everything is staged.

## Notable bugs found and fixed along the way

- A NUL byte used as a field delimiter truncated the git command's argument
  (NUL terminates C strings); switched to a unit-separator character.
- `git for-each-ref %(HEAD)` renders inconsistently (`*` / space / empty) for
  non-current branches, which silently dropped branches from parsing; fixed by
  detecting the current branch separately.
- Standard `curses` bottom-right-cell write error; fixed with a clamped,
  exception-guarded draw helper.

## Engineering notes

- All four tools are read-only and dependency-free (Bash + Python stdlib).
- Shared git logic lives in `git_repo_scan.py`; the Python tools import it from
  their own directory, so it must stay colocated.
- Behaviour was validated by driving the curses UI through a pseudo-terminal and
  by deterministic data-level checks against purpose-built synthetic repos.

See `git-tui-requirements.md` for the detailed, rationale-tagged requirements.
