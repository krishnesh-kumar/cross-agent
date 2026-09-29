#!/usr/bin/env python3
"""cross-agent memory tool. Python 3.8+, stdlib only. Format: see AGENTS.md.

  mem.py snap                          rebuild mem/now.l from mem/log/*.l
  mem.py check                         lint logs; exit 1 on errors
  mem.py add WHO KIND|ID STATUS TEXT   append one record (mints id if KIND), then snap
  mem.py new                           print log lines at or after now.l upto= (may repeat a few)
"""
import glob
import os
import re
import sys
import time
from collections import namedtuple

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "log")
NOW = os.path.join(ROOT, "now.l")

TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$")
WHO = re.compile(r"^[a-z]{2,5}$")
ID = re.compile(r"^([ATFDM])([a-z]{2,5})(\d*)$")
REF = re.compile(r"(?<![A-Za-z0-9])([\^!])([ATFDM][a-z]{2,5}\d*)\b")
KINDS = "ATFDM"
STATUS = {
    "A": ("on", "off"),
    "T": ("open", "claim", "done", "ok", "redo", "block", "drop"),
    "F": ("live", "old", "wrong"),
    "D": ("live", "old", "wrong"),
    "M": ("new", "seen"),
}
DEFAULT = {"A": "on", "T": "open", "F": "live", "D": "live", "M": "new"}
CLOSED = {"off", "ok", "drop", "old", "wrong", "seen"}
TASK_ORDER = {"done": 0, "redo": 1, "block": 2, "claim": 3, "open": 4}
SECRETS = [
    re.compile(p)
    for p in (
        r"sk-[A-Za-z0-9_-]{20,}",
        r"gh[pousr]_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"xox[abprs]-[A-Za-z0-9-]{10,}",
        r"AIza[0-9A-Za-z_-]{30,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY",
        r"[Bb]earer [A-Za-z0-9._-]{20,}",
        r"eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}",
        r"(?i)(api[_-]?key|secret|token|passw(or)?d|cookie)\s*[:=]\s*\S{8,}",
    )
]

Rec = namedtuple("Rec", "ts who id status text file line")


def utcnow():
    return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())


def fmt(r):
    return "|".join((r.ts, r.who, r.id, r.status, r.text))


def load():
    """Parse every log file. Returns (records sorted by ts, errors)."""
    recs, errs = [], []
    for path in sorted(glob.glob(os.path.join(LOG, "*.l"))):
        fname = os.path.basename(path)
        fwho = fname.split(".")[0]
        with open(path, encoding="utf-8") as fh:
            for n, raw in enumerate(fh, 1):
                line = raw.rstrip("\r\n")
                loc = "%s:%d" % (fname, n)
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 4)
                if len(parts) != 5:
                    errs.append("%s need 5 fields ts|who|id|status|text" % loc)
                    continue
                ts, who, rid, status, text = parts
                m = ID.match(rid)
                if not TS.match(ts):
                    errs.append("%s bad ts %r (want YYYY-MM-DDTHH:MMZ)" % (loc, ts))
                elif not WHO.match(who):
                    errs.append("%s bad who %r (2-5 lowercase letters)" % (loc, who))
                elif who != fwho:
                    errs.append("%s who=%s but file belongs to %s" % (loc, who, fwho))
                elif not m or (m.group(1) == "A") != (m.group(3) == ""):
                    errs.append("%s bad id %r (KIND+handle+n; A has no n)" % (loc, rid))
                elif status != "-" and status not in STATUS[rid[0]]:
                    errs.append("%s bad status %r for %s (%s)" % (loc, status, rid[0], " ".join(STATUS[rid[0]])))
                else:
                    recs.append(Rec(ts, who, rid, status, text, fname, n))
                for pat in SECRETS:
                    if pat.search(text):
                        errs.append("%s looks like a secret (%s)" % (loc, pat.pattern[:24]))
                        break
    recs.sort(key=lambda r: (r.ts, r.file, r.line))
    return recs, errs


def fold(recs):
    """Replay records into current state: {id: entry}. Returns (state, warnings)."""
    st, warns = {}, []
    for r in recs:
        kind = r.id[0]
        e = st.get(r.id)
        if e is None:
            e = st[r.id] = dict(
                id=r.id, kind=kind, by=r.who, ts0=r.ts, title=r.text, note="",
                who=r.who, ts=r.ts, owner=r.who,
                status=r.status if r.status != "-" else DEFAULT[kind],
            )
        else:
            s = r.status
            if kind == "T" and s in ("claim", "done"):
                e["owner"] = r.who
            if kind == "T" and s == "ok" and r.who == e["owner"]:
                warns.append("%s self-approval by %s ignored (%s:%d)" % (r.id, r.who, r.file, r.line))
                s = "-"
            if s != "-":
                e["status"] = s
            if r.text:
                e["note"] = r.text
            e["who"], e["ts"] = r.who, r.ts
        for sigil, tgt in REF.findall(r.text):
            t = st.get(tgt)
            if t is None:
                warns.append("%s refers to unknown %s (%s:%d)" % (r.id, tgt, r.file, r.line))
            elif sigil == "!" and tgt != r.id and t["status"] not in CLOSED:
                t.update(status="old", who=r.who, ts=r.ts, note="superseded by " + r.id)
    return st, warns


def snapshot(recs, errs, st, warns):
    upto = max((r.ts for r in recs), default=utcnow())
    out = ["#now %s upto=%s recs=%d ids=%d" % (utcnow(), upto, len(recs), len(st))]
    out += ["#err " + e for e in errs]
    out += ["#warn " + w for w in warns]
    out.append("#fmt ts|who|id|status|title|note  (ts/who = last update; T done = awaiting review by another handle)")
    sections = (
        ("agents", "A", lambda e: e["status"] == "on"),
        ("tasks", "T", lambda e: e["status"] not in ("ok", "drop")),
        ("facts", "F", lambda e: e["status"] == "live"),
        ("decisions", "D", lambda e: e["status"] == "live"),
        ("msgs", "M", lambda e: e["status"] == "new"),
    )
    for name, kind, keep in sections:
        rows = [e for e in st.values() if e["kind"] == kind and keep(e)]
        if kind == "T":
            rows.sort(key=lambda e: (TASK_ORDER.get(e["status"], 9), e["ts"]))
        else:
            rows.sort(key=lambda e: e["ts"], reverse=True)
        out.append("#%s %d" % (name, len(rows)))
        out += ["|".join((e["ts"], e["who"], e["id"], e["status"], e["title"], e["note"])) for e in rows]
    tail = recs[-10:]
    out.append("#recent %d" % len(tail))
    out += [fmt(r) for r in tail]
    return "\n".join(out) + "\n"


def cmd_snap():
    recs, errs = load()
    st, warns = fold(recs)
    text = snapshot(recs, errs, st, warns)
    with open(NOW, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s: %d recs, %d ids, %d err, %d warn" % (os.path.relpath(NOW), len(recs), len(st), len(errs), len(warns)))
    return 0


def cmd_check():
    recs, errs = load()
    _, warns = fold(recs)
    for e in errs:
        print("ERR  " + e)
    for w in warns:
        print("WARN " + w)
    print("%d records, %d errors, %d warnings" % (len(recs), len(errs), len(warns)))
    return 1 if errs else 0


def cmd_new():
    upto = ""
    if os.path.exists(NOW):
        with open(NOW, encoding="utf-8") as fh:
            m = re.search(r"upto=(\S+)", fh.readline())
            upto = m.group(1) if m else ""
    recs, _ = load()
    for r in recs:
        if r.ts >= upto:
            print(fmt(r))
    return 0


def cmd_add(who, kid, status, text):
    if not WHO.match(who):
        sys.exit("bad handle %r: 2-5 lowercase letters" % who)
    if "|" in text or "\n" in text:
        sys.exit("text may not contain | or newline")
    recs, _ = load()
    if kid in KINDS:
        if kid == "A":
            rid = "A" + who
        else:
            ns = [int(m.group(3)) for r in recs for m in [ID.match(r.id)]
                  if m and m.group(1) == kid and m.group(2) == who and m.group(3)]
            rid = "%s%s%d" % (kid, who, max(ns, default=0) + 1)
    else:
        m = ID.match(kid)
        if not m or (m.group(1) == "A") != (m.group(3) == ""):
            sys.exit("bad id %r" % kid)
        rid = kid
    kind = rid[0]
    if status != "-" and status not in STATUS[kind]:
        sys.exit("bad status %r for %s: %s or -" % (status, kind, " ".join(STATUS[kind])))
    ts = utcnow()
    for pat in SECRETS:
        if pat.search(text):
            sys.exit("refusing: text looks like a secret (%s)" % pat.pattern[:24])
    os.makedirs(LOG, exist_ok=True)
    path = os.path.join(LOG, "%s.%s.l" % (who, ts[:7]))
    line = fmt(Rec(ts, who, rid, status, text, "", 0))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line)
    return cmd_snap()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "help"
    if cmd == "snap":
        return cmd_snap()
    if cmd == "check":
        return cmd_check()
    if cmd == "new":
        return cmd_new()
    if cmd == "add" and len(argv) == 6:
        return cmd_add(*argv[2:6])
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
