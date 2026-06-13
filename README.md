# git-claude-tui

A small suite of **read-only** tools for getting an overview of many git
repositories at once — which are dirty, which are unpushed, which are duplicate
copies of each other — and for drilling into a single repo's branch/commit
history. Zero runtime dependencies (Bash + Python stdlib `curses`).

Built to answer questions like *"my laptop might die — what have I got that
isn't safely pushed, and which of my dozen manual copies can I delete?"*

## Tools

All live in `bin/` and share one scanner module (`git_repo_scan.py`), so keep
them in the same directory.

| Tool | What it does |
|------|--------------|
| `git-overview` | Survey every repo under given roots: branch, dirty count, ahead/behind, remote account, flags repos needing attention. |
| `git-overview --copies` | Group repos that are copies of each other (same origin / root commit) and judge which copies are **safe to delete** vs hold unique work. |
| `git-map` | Render all repos as an SVG "subway map" — folders as spines, repos as stations coloured by account, status as fill, copies as interchanges. |
| `git-tui` | Interactive terminal browser of the repo tree; drill into any repo (`→`) for a colour-coded **commit DAG** (git topology drawn as a subway-style map) showing forks, merges, dead-end branches, and which commits are unpushed. |

## Install

```sh
git clone git@github.com:HiveMinds/git-claude-tui.git
export PATH="$PWD/git-claude-tui/bin:$PATH"   # add to ~/.bashrc to persist
```

Requires `git` and Python 3.

## Usage

```sh
git-overview                 # scan ~/git
git-overview ~/git ~/work    # scan specific roots
git-overview --all           # include clean + nested/submodule repos
git-overview --copies        # duplicate-copy analysis

git-map                      # write ~/Pictures/git-map.svg
git-map ~/git/work           # map a subtree
git-map --out /tmp/m.svg ~/git

git-tui                      # interactive; ? for legend, q to quit
git-tui --list               # plain-text dump (no tty needed)
```

### `git-tui` keys

Tree: `j/k` move · `l/h` expand/collapse · `z` collapse-all · `d`/`u`/`x`/`a`
filter dirty/unpushed/copies/all · `c` next copy · `?` legend · `r` rescan ·
`o` print selected path & quit · `q` quit.

Drill-down (`→`/Enter on a repo): the commit DAG (git topology) rendered as a
coloured map — lanes coloured per column, `●` pushed / `◆` unpushed nodes,
`[refs]` for branch/tag tips. `j/k` scroll · `PgUp/PgDn`/`g/G` page · `?` legend
· `h/←/q` back.

## Status encoding

- **Account / line colour:** personal github, work github, bitbucket, other.
- **Station shape:** `○` clean · `●` dirty (uncommitted) · `◆` unpushed · `◌` no remote.
- **Badges:** `±N` files changed · `↑N` commits unpushed · `⇄N` copy group N.

Read-only by design: these tools never write to the repositories they inspect.
