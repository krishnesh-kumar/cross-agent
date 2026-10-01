#!/usr/bin/env python3
"""cross-agent memory tool. Python 3.8+, stdlib only. Format: see AGENTS.md.

  mem.py snap                          rebuild mem/now.l (+ mem/rest.l overflow) from mem/log/*.l
  mem.py check                         lint logs; exit 1 on format errors only
  mem.py add WHO KIND|ID STATUS TEXT   append one record (mints id if KIND), then snap
  mem.py new                           print log lines at or after now.l upto= (may repeat a few)
  mem.py review VIA ID ok|redo [NOTE]  record the human's chat decision as hu, text starts via:VIA
"""
import glob
import os
import re
import sys
import time
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "log")
NOW = os.path.join(ROOT, "now.l")
REST = os.path.join(ROOT, "rest.l")
HUMAN = "hu"
SPEC = 1
DEFAULT_TTL_MIN = 90
OUTLIER_MIN = 26 * 60  # a lone ts this far ahead of the rest is a typo, not the clock

TS = re.compile(r"^\d{6}\.\d{4}$")  # YYMMDD.HHMM UTC
WHO = re.compile(r"^[a-z]{2,5}$")
ID = re.compile(r"^([ATFDM])([a-z]{2,5})(\d*)$")
REF = re.compile(r"(?<![A-Za-z0-9])([\^!])([ATFDM][a-z]{2,5}\d*)\b")
TAG = re.compile(r"(?<![A-Za-z0-9])#([a-z0-9_-]+)\b")
TTL = re.compile(r"\bttl=(\d+)m\b")
UNTIL = re.compile(r"\buntil=(\d{6}\.\d{4})\b")
# A slash path counts even without "see". "see file.md" counts. Node.js does not.
PATHISH = re.compile(
    r"(?:[\w.-]+/)+[\w.-]+|see\s+[\w.-]+\.(?:md|py|txt|l)\b",
    re.I,
)
KINDS = "ATFDM"
STATUS = {
    "A": ("on", "off"),
    "T": ("open", "claim", "done", "peer", "ok", "redo", "block", "drop"),
    "F": ("live", "law", "old", "wrong"),
    "D": ("live", "law", "old", "wrong"),
    "M": ("new", "seen"),
}
DEFAULT = {"A": "on", "T": "open", "F": "live", "D": "live", "M": "new"}
CLOSED = {"off", "ok", "drop", "old", "wrong", "seen"}
TASK_ORDER = {"done": 0, "peer": 1, "redo": 2, "block": 3, "claim": 4, "open": 5}
CAP = {"A": 50, "T": 25, "F": 40, "D": 15, "M": 10}
MAXLEN = {"F": 120}
MAXTEXT = 200
FACT_PATH_HINT = 80
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
    return time.strftime("%y%m%d.%H%M", time.gmtime())


def month_of(ts):
    return "20%s-%s" % (ts[:2], ts[2:4])


def fmt(r):
    return "|".join((r.ts, r.who, r.id, r.status, r.text))


def valid_ts(ts):
    """Digit shape is not enough: 31 February matches the pattern and must not crash."""
    if not TS.match(ts or ""):
        return False
    try:
        datetime.strptime("20" + ts, "%Y%m%d.%H%M")
        return True
    except ValueError:
        return False


def ts_add_minutes(ts, minutes):
    dt = datetime.strptime("20" + ts, "%Y%m%d.%H%M") + timedelta(minutes=int(minutes))
    return dt.strftime("%y%m%d.%H%M")


def claim_until(ts, text):
    """Lease end, or None if the timestamp cannot be parsed. Never raises."""
    if not valid_ts(ts):
        return None
    m = UNTIL.search(text or "")
    if m and valid_ts(m.group(1)):
        return m.group(1)
    m = TTL.search(text or "")
    minutes = int(m.group(1)) if m else DEFAULT_TTL_MIN
    try:
        return ts_add_minutes(ts, minutes)
    except ValueError:
        return None


def same_writer(a, b, registered=None):
    """cl and an unregistered clb are the same running identity. Not cryptographic.

    A one-letter suffix counts only when the longer handle has no A line of its own.
    gp and gpt are different agents once both are registered.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) < len(b) else (b, a)
    if len(long) != len(short) + 1 or not long.startswith(short):
        return False
    if registered and short in registered and long in registered:
        return False
    return True


def pick_now(recs):
    """Latest real log ts. A lone timestamp more than a day ahead of the rest is a typo."""
    ts = sorted({r.ts for r in recs if valid_ts(r.ts)})
    if not ts:
        return utcnow(), None
    if len(ts) >= 2:
        try:
            if ts_add_minutes(ts[-2], OUTLIER_MIN) < ts[-1]:
                return ts[-2], ts[-1]
        except ValueError:
            return ts[-2], ts[-1]
    return ts[-1], None


def load():
    """Parse every log file. Returns (records sorted by ts, errors).

    Format errors are excluded from the fold. Policy misses are not errors.
    """
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
                if not TS.match(ts) or not valid_ts(ts):
                    errs.append("%s bad ts %r (want a real YYMMDD.HHMM)" % (loc, ts))
                elif not WHO.match(who):
                    errs.append("%s bad who %r (2-5 lowercase letters)" % (loc, who))
                elif who != fwho:
                    errs.append("%s who=%s but file belongs to %s" % (loc, who, fwho))
                elif not m or (m.group(1) == "A") != (m.group(3) == ""):
                    errs.append("%s bad id %r (KIND+handle+n; A has no n)" % (loc, rid))
                elif status != "-" and status not in STATUS[rid[0]]:
                    errs.append("%s bad status %r for %s (%s)" % (loc, status, rid[0], " ".join(STATUS[rid[0]])))
                elif len(text) > MAXLEN.get(rid[0], MAXTEXT):
                    errs.append("%s text %d chars, max %d for %s" % (loc, len(text), MAXLEN.get(rid[0], MAXTEXT), rid[0]))
                else:
                    recs.append(Rec(ts, who, rid, status, text, fname, n))
                for pat in SECRETS:
                    if pat.search(text):
                        errs.append("%s looks like a secret (%s)" % (loc, pat.pattern[:24]))
                        break
    recs.sort(key=lambda r: (r.ts, r.file, r.line))
    return recs, errs


def fold(recs, now=None):
    """Replay records. now defaults to the latest log ts, ignoring a lone future typo.

    Policy misses (law, self-ok, peer-before-done) are warnings. The fold ignores them.
    They are not errors: an append-only log cannot delete the bad line, and check must
    not stay red forever. Format errors never reach here.
    """
    outlier = None
    if now is None:
        now, outlier = pick_now(recs)
    st, warns = {}, []
    if outlier:
        warns.append("ignored future ts %s; clock stays %s" % (outlier, now))
    registered = {r.who for r in recs if r.id == "A" + r.who}
    known = {r.id for r in recs}
    for r in recs:
        kind = r.id[0]
        if valid_ts(r.ts) and month_of(r.ts) not in r.file:
            warns.append("%s ts %s is not in file %s" % (r.id, r.ts, r.file))
        e = st.get(r.id)
        if e is None:
            status = r.status if r.status != "-" else DEFAULT[kind]
            if status == "law" and r.who != HUMAN:
                warns.append("%s law set by %s ignored (%s:%d)" % (r.id, r.who, r.file, r.line))
                status = DEFAULT[kind]
            if kind == "T" and status in ("ok", "peer"):
                warns.append("%s %s ignored, task was not done (%s:%d)" % (r.id, status, r.file, r.line))
                status = "open"
            e = st[r.id] = dict(
                id=r.id, kind=kind, by=r.who, ts0=r.ts, title=r.text, note="",
                who=r.who, ts=r.ts, owner=r.who, status=status,
                until=claim_until(r.ts, r.text) if kind == "T" and status == "claim" else None,
                peer=r.who if status == "peer" else "",
            )
        else:
            s = r.status
            note = r.text
            if e.get("status") == "law" and r.who != HUMAN:
                warns.append("%s law note/status by %s ignored (%s:%d)" % (r.id, r.who, r.file, r.line))
                s, note = "-", ""
            if kind == "T" and s == "claim" and e.get("status") == "claim" and e.get("owner") and e["owner"] != r.who:
                until = e.get("until")
                if until and until <= r.ts:
                    pass
                else:
                    warns.append("%s double claim by %s and %s (%s:%d)" % (r.id, e["owner"], r.who, r.file, r.line))
            if kind == "T" and s in ("claim", "done"):
                e["owner"] = r.who
            if kind == "T" and s in ("ok", "peer"):
                if e.get("status") != "done":
                    warns.append("%s %s ignored, task is %s not done (%s:%d)" % (r.id, s, e.get("status"), r.file, r.line))
                    s = "-"
                elif same_writer(r.who, e.get("owner") or "", registered):
                    warns.append("%s self-approval by %s ignored (%s:%d)" % (r.id, r.who, r.file, r.line))
                    s = "-"
            if s == "law" and r.who != HUMAN:
                warns.append("%s law set by %s ignored (%s:%d)" % (r.id, r.who, r.file, r.line))
                s = "-"
            if kind == "T" and s == "claim":
                e["until"] = claim_until(r.ts, r.text)
            if kind == "T" and s == "-" and e.get("status") == "claim" and r.who == e.get("owner"):
                e["until"] = claim_until(r.ts, r.text) or e.get("until")
            if kind == "T" and s == "peer":
                e["peer"] = r.who
            if s != "-":
                e["status"] = s
            if note:
                e["note"] = note
            if s != "-" or note:
                e["who"], e["ts"] = r.who, r.ts
        for sigil, tgt in REF.findall(r.text):
            t = st.get(tgt)
            if t is None:
                if tgt not in known:
                    warns.append("%s refers to unknown %s (%s:%d)" % (r.id, tgt, r.file, r.line))
            elif sigil == "!" and tgt != r.id:
                if t.get("status") == "law" and r.who != HUMAN:
                    warns.append("%s cannot supersede law %s (%s:%d)" % (r.id, tgt, r.file, r.line))
                    cur = st.get(r.id)
                    if cur and cur["kind"] in "FD" and cur.get("status") not in CLOSED:
                        cur["status"] = "wrong"
                        cur["note"] = "refused supersede of law " + tgt
                elif t["status"] not in CLOSED:
                    t.update(status="old", who=r.who, ts=r.ts, note="superseded by " + r.id)
    for e in st.values():
        if e["kind"] == "T" and e["status"] == "claim" and e.get("until") and e["until"] <= now:
            warns.append("%s claim expired at %s, back to open" % (e["id"], e["until"]))
            e["status"] = "open"
            e["note"] = ((e.get("note") or "") + " claim expired").strip()
        if e["kind"] == "F" and e["status"] in ("live", "law"):
            blob = (e.get("title") or "") + " " + (e.get("note") or "")
            if len(e.get("title") or "") > FACT_PATH_HINT and not PATHISH.search(blob):
                warns.append("%s fact >%d chars with no repo path" % (e["id"], FACT_PATH_HINT))
    by_tag = defaultdict(list)
    for e in st.values():
        if e["kind"] == "D" and e["status"] in ("live", "law"):
            for tag in set(TAG.findall((e.get("title") or "") + " " + (e.get("note") or ""))):
                by_tag[tag].append(e["id"])
    for tag, ids in sorted(by_tag.items()):
        uniq = sorted(set(ids))
        if len(uniq) > 1:
            warns.append("conflict #%s: %s" % (tag, " ".join(uniq)))
    return st, warns


def snapshot(recs, errs, st, warns):
    """Render the capped live view. Law rows stay ahead of live rows so they are last to overflow."""
    upto = max((r.ts for r in recs if valid_ts(r.ts)), default=utcnow())
    sections = (
        ("agents", "A", lambda e: e["status"] == "on"),
        ("tasks", "T", lambda e: e["status"] not in ("ok", "drop")),
        ("facts", "F", lambda e: e["status"] in ("live", "law")),
        ("decisions", "D", lambda e: e["status"] in ("live", "law")),
        ("msgs", "M", lambda e: e["status"] == "new"),
    )
    now, rest, nrest = [], [], 0
    for name, kind, keep in sections:
        rows = [e for e in st.values() if e["kind"] == kind and keep(e)]
        if kind == "T":
            rows.sort(key=lambda e: (TASK_ORDER.get(e["status"], 9), e["ts"]))
        elif kind in "FD":
            rows.sort(key=lambda e: e["ts"], reverse=True)
            rows.sort(key=lambda e: 0 if e["status"] == "law" else 1)
        else:
            rows.sort(key=lambda e: e["ts"], reverse=True)
        head, tail = rows[:CAP[kind]], rows[CAP[kind]:]
        nrest += len(tail)
        for out, part, note in ((now, head, " +%d in rest.l" % len(tail) if tail else ""), (rest, tail, "")):
            out.append("#%s %d%s" % (name, len(part), note))
            out += ["|".join((e["ts"], e["who"], e["id"], e["status"], e["title"], e["note"])) for e in part]
    head = ["#now spec=%d upto=%s recs=%d ids=%d rest=%d" % (SPEC, upto, len(recs), len(st), nrest)]
    head += ["#err " + e for e in errs]
    head += ["#warn " + w for w in warns]
    head.append("#k ts|who|id|status|title|note  ts=YYMMDD.HHMM utc, who=last actor, id=KIND+handle+n, "
                "K: A agent T task F fact D decision M message, "
                "T done=awaiting a different handle or hu, law=hu file only, rules AGENTS.md spec=%d" % SPEC)
    return "\n".join(head + now) + "\n", "\n".join(["#rest overflow of now.l, same format"] + rest) + "\n"


def cmd_snap():
    recs, errs = load()
    st, warns = fold(recs)
    text, rest = snapshot(recs, errs, st, warns)
    with open(NOW, "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(REST, "w", encoding="utf-8") as fh:
        fh.write(rest)
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


def _append(who, kid, status, text):
    """Validate, mint an id if needed, append one line. Exits with a message on bad input."""
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
    if status == "law" and who != HUMAN:
        sys.exit("only a line in hu's file may set law; that is not proof the human wrote it")
    ts = utcnow()
    for pat in SECRETS:
        if pat.search(text):
            sys.exit("refusing: text looks like a secret (%s)" % pat.pattern[:24])
    os.makedirs(LOG, exist_ok=True)
    if len(text) > MAXLEN.get(kind, MAXTEXT):
        sys.exit("text is %d chars, max %d for %s" % (len(text), MAXLEN.get(kind, MAXTEXT), kind))
    path = os.path.join(LOG, "%s.%s.l" % (who, month_of(ts)))
    line = fmt(Rec(ts, who, rid, status, text, "", 0))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return line


def cmd_add(who, kid, status, text):
    print(_append(who, kid, status, text))
    return cmd_snap()


def cmd_review(via, rid, verdict, note=""):
    """Write the human's chat decision as an hu line marked via:<agent>. Refuses bad requests."""
    if verdict not in ("ok", "redo"):
        sys.exit("verdict must be ok or redo")
    if not WHO.match(via) or via == HUMAN:
        sys.exit("via must be the handle of the agent relaying the human's decision")
    recs, _ = load()
    e = fold(recs)[0].get(rid)
    if e is None or e["kind"] != "T":
        sys.exit("no such task: %s" % rid)
    if e["status"] not in ("done", "peer"):
        sys.exit("%s is %s, only a done or peer task can be reviewed" % (rid, e["status"]))
    if e["owner"] == HUMAN:
        sys.exit("%s was done by the human, a different handle must review it" % rid)
    text = " ".join(("via:" + via + " " + note).replace("|", "/").split())
    print(_append(HUMAN, rid, verdict, text))
    return cmd_snap()


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "help"
    if cmd == "snap":
        return cmd_snap()
    if cmd == "check":
        return cmd_check()
    if cmd == "new":
        return cmd_new()
    if cmd == "review" and len(argv) >= 5:
        return cmd_review(*argv[2:6])
    if cmd == "add" and len(argv) == 6:
        return cmd_add(*argv[2:6])
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
