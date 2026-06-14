"""Shared git-repo scanning for git-map / git-tui. Read-only."""
import os, subprocess

PRUNE = {"node_modules", ".cache", ".direnv", ".venv", "venv"}

def git(repo, *args):
    # core.fileMode=false: ignore the executable bit everywhere, so chmod-only
    # changes don't show up as "old mode/new mode" noise in diffs or as phantom
    # modified files in status.
    try:
        r = subprocess.run(["git", "-C", repo, "-c", "core.fileMode=false", *args],
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip()
    except Exception:
        return ""

def account_of(url):
    if not url:                                            return "none"
    if "github-first8:" in url or "github-first8/" in url: return "gh:first8"
    if "bitbucket.org" in url:                             return "bitbucket"
    if "github.com" in url:                                return "gh"
    return "other"

def find_repos(root):
    found = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in PRUNE]
        if ".git" in dns or ".git" in fns:
            found.append(os.path.realpath(dp))
            if ".git" in dns:
                dns.remove(".git")
    return found

def inspect(repo):
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    if branch == "HEAD":
        branch = "(detached)"
    url = git(repo, "remote", "get-url", "origin")
    remotes = git(repo, "remote")
    acct = account_of(url)
    dirty = len([x for x in git(repo, "status", "--porcelain").splitlines() if x])
    ahead, has_up = 0, False
    up = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if up:
        has_up = True
        c = git(repo, "rev-list", "--count", "--left-right", "@{upstream}...HEAD")
        if c and len(c.split()) == 2:
            ahead = int(c.split()[1])
    if url:
        gkey = url
    else:
        roots = git(repo, "rev-list", "--max-parents=0", "HEAD")
        gkey = "root:" + ",".join(sorted(roots.split())) if roots else "none"
    if not remotes:
        status = "no-remote"
    elif dirty:
        status = "dirty"
    elif ahead > 0 or not has_up:
        status = "unpushed"
    else:
        status = "clean"
    return dict(branch=branch, account=acct, dirty=dirty, ahead=ahead,
                has_up=has_up, gkey=gkey, status=status)

class Node:
    __slots__ = ("name", "children", "repo", "x", "y", "key")
    def __init__(self, name):
        self.name = name; self.children = {}; self.repo = None
        self.x = 0; self.y = 0; self.key = ""

def scan(roots):
    """Return (roots, repos, info, gid, ngroups). repos = non-nested repo paths."""
    roots = [os.path.realpath(os.path.expanduser(r)) for r in roots]
    all_repos = []
    for r in roots:
        if os.path.isdir(r):
            all_repos += find_repos(r)
    all_repos = sorted(set(all_repos))
    rs = set(all_repos)
    nested = lambda p: any(p.startswith(q + os.sep) for q in rs if q != p)
    repos = [p for p in all_repos if not nested(p)]
    info = {p: inspect(p) for p in repos}
    groups = {}
    for p in repos:
        groups.setdefault(info[p]["gkey"], []).append(p)
    gid, n = {}, 0
    for k, members in groups.items():
        if len(members) >= 2:
            n += 1
            for m in members:
                gid[m] = n
    return roots, repos, info, gid, n

def build_tree(roots, repos):
    """Build a Node tree from repo paths; leaves carry .repo (path)."""
    root = Node("repos")
    for p in repos:
        owner = max((r for r in roots if p == r or p.startswith(r + os.sep)),
                    key=len, default=None)
        if owner is None:
            continue
        rel = os.path.relpath(p, owner)
        parts = [os.path.basename(owner)] + ([] if rel == "." else rel.split(os.sep))
        cur, key = root, ""
        for part in parts:
            key = key + "/" + part
            if part not in cur.children:
                ch = Node(part); ch.key = key; cur.children[part] = ch
            cur = cur.children[part]
        cur.repo = p
    return root

def _parse_commits(raw, pushed):
    out = []
    for line in raw.splitlines():
        p = line.split("\t", 4)
        if len(p) < 5:
            continue
        sha, ct, cr, refs, subj = p
        out.append(dict(sha=sha[:8], full=sha, ct=int(ct) if ct.isdigit() else 0,
                        rel=cr, refs=refs, subj=subj, pushed=sha in pushed))
    return out

def repo_graph(repo, limit=600):
    """Parse `git log --graph` into styled lines for the commit-DAG view.

    Returns a list of dicts:
      {kind:'c', art, sha, ct, rel, refs, subj, pushed}   commit rows
      {kind:'l', art}                                      link/rail rows
    The `art` is git's own topology art (* | / \\ _) — column 2*L == lane L.
    """
    pushed = set(git(repo, "rev-list", "--remotes").split())
    US = "\x1f"   # unit separator: legal in argv (unlike NUL), absent from commit text
    raw = git(repo, "log", "--branches", "--remotes", "--date-order", "--graph",
              f"--format={US}%H{US}%ct{US}%cr{US}%D{US}%s", "-n", str(limit))
    out = []
    for ln in raw.split("\n"):
        if US in ln:
            art, rest = ln.split(US, 1)
            f = (rest.split(US) + [""] * 5)[:5]
            h, ct, cr, refs, subj = f
            out.append(dict(kind="c", art=art, sha=h[:8], full=h,
                            ct=int(ct) if ct.isdigit() else 0, rel=cr,
                            refs=refs, subj=subj, pushed=(h in pushed)))
        elif ln.strip():
            out.append(dict(kind="l", art=ln))
    return out

def repo_worktree(repo):
    """Uncommitted state: staged / unstaged / untracked files, and the HEAD it sits on."""
    cur = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    head = git(repo, "rev-parse", "HEAD")
    subj = git(repo, "log", "-1", "--format=%s")
    raw = git(repo, "status", "--porcelain=v1")
    staged, unstaged, untracked, nfiles = [], [], [], 0
    for ln in raw.split("\n"):
        if len(ln) < 4:
            continue
        nfiles += 1                        # one porcelain line == one changed file
        x, y, path = ln[0], ln[1], ln[3:]
        if x == "?" and y == "?":
            untracked.append(path); continue
        if x not in " ?":
            staged.append((x, path))       # in the index -> will be committed
        if y not in " ?":
            unstaged.append((y, path))     # modified in tree, not staged
    return dict(branch=cur, head=head, head_short=head[:8], subj=subj,
                staged=staged, unstaged=unstaged, untracked=untracked, n=nfiles)

def repo_detail(repo, per_branch=400, max_branches=24, with_commits=True):
    """Branches (optionally each with its commit list) for the drill-down."""
    # NB: don't use %(HEAD) as a parse field — git renders it inconsistently
    # ("*" / " " / "" for non-current refs), which corrupts tab-splitting.
    cur = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    raw = git(repo, "for-each-ref",
              "--format=%(refname:short)\t%(upstream:short)"
              "\t%(committerdate:unix)\t%(committerdate:relative)", "refs/heads")
    branches = []
    for line in raw.splitlines():
        p = line.split("\t")
        if len(p) < 4:
            continue
        name, up, cu, cr = p[0], p[1], p[2], p[3]
        head = "*" if name == cur else " "
        ahead = behind = unpushed = None
        if up:
            c = git(repo, "rev-list", "--count", "--left-right", f"{up}...{name}")
            if c and len(c.split()) == 2:
                behind, ahead = int(c.split()[0]), int(c.split()[1])
        else:
            u = git(repo, "rev-list", "--count", name, "--not", "--remotes")
            unpushed = int(u) if u.isdigit() else 0
        branches.append(dict(current=(head == "*"), name=name, upstream=up,
                             ahead=ahead, behind=behind, unpushed=unpushed,
                             ct=int(cu) if cu.isdigit() else 0, rel=cr))
    branches.sort(key=lambda b: (not b["current"], -b["ct"]))   # current first, then recency
    branches = branches[:max_branches]

    pushed = set(git(repo, "rev-list", "--remotes").split())
    if with_commits:
        for b in branches:
            raw = git(repo, "log", b["name"], "--date-order",
                      "--format=%H\t%ct\t%cr\t%D\t%s", "-n", str(per_branch))
            b["commits"] = _parse_commits(raw, pushed)

    u = git(repo, "rev-list", "--count", "--branches", "--not", "--remotes")
    n_unpushed = int(u) if u.isdigit() else 0
    return dict(branches=branches, n_unpushed=n_unpushed)


def sorted_children(node):
    """Repos first, then folders; each alphabetical."""
    return [node.children[k] for k in
            sorted(node.children, key=lambda k: (node.children[k].repo is None, k.lower()))]
