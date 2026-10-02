"""Unit tests for mem.py. Run: python3 -m unittest mem/test_mem.py"""
import contextlib
import io
import os
import shutil
import tempfile
import unittest
import importlib.util
from datetime import datetime, timedelta

_spec = importlib.util.spec_from_file_location(
    "memtool", os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem.py"))
mem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mem)


class MemTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        mem.LOG = os.path.join(self.tmp, "log")
        mem.NOW = os.path.join(self.tmp, "now.l")
        mem.REST = os.path.join(self.tmp, "rest.l")
        os.makedirs(mem.LOG)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, who, lines, month="2026-09"):
        with open(os.path.join(mem.LOG, "%s.%s.l" % (who, month)), "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def state(self, now=None):
        recs, errs = mem.load()
        st, warns = mem.fold(recs, now=now)
        return st, errs, warns

    def review(self, *args):
        with contextlib.redirect_stdout(io.StringIO()):
            mem.cmd_review(*args)

    def test_patch_latest_wins_across_files(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|claim|on it"])
        st, errs, _ = self.state(now="260901.1100")
        self.assertEqual(errs, [])
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertEqual(st["Tcl1"]["title"], "Do thing")
        self.assertEqual(st["Tcl1"]["note"], "on it")
        self.assertEqual(st["Tcl1"]["who"], "gpt")

    def test_self_approval_ignored(self):
        self.write("cl", [
            "260901.1000|cl|Tcl1|open|Do thing",
            "260901.1100|cl|Tcl1|done|finished",
            "260901.1200|cl|Tcl1|ok|looks good to me",
        ])
        st, _, warns = self.state(now="260901.1200")
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))
        self.write("gpt", ["260901.1300|gpt|Tcl1|ok|verified"])
        st, _, _ = self.state(now="260901.1300")
        self.assertEqual(st["Tcl1"]["status"], "ok")

    def test_creator_may_approve_other_agents_work(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|done|did it"])
        self.write("cl", ["260901.1200|cl|Tcl1|ok|reviewed"])
        st, _, warns = self.state(now="260901.1200")
        self.assertEqual(st["Tcl1"]["status"], "ok")
        self.assertEqual(warns, [])

    def test_other_agent_ok_closes(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|done|did it"])
        self.write("cl", ["260901.1200|cl|Tcl1|ok|reviewed"])
        st, _, warns = self.state(now="260901.1200")
        self.assertEqual(st["Tcl1"]["status"], "ok")
        self.assertFalse(any("self-approval" in w for w in warns))

    def test_ok_before_done_ignored(self):
        self.write("cl", ["260930.1000|cl|Tcl1|claim|ttl=600m working"])
        self.write("gk", ["260930.1010|gk|Tcl1|ok|looks fine"])
        self.write("hu", ["260930.1020|hu|Tcl1|ok|via:gk approve"])
        st, _, warns = self.state(now="260930.1020")
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertTrue(any("not done" in w for w in warns))

    def test_peer_before_done_ignored(self):
        self.write("cl", ["260930.1000|cl|Tcl1|claim|ttl=600m working"])
        self.write("gk", ["260930.1010|gk|Tcl1|peer|lgtm"])
        st, _, warns = self.state(now="260930.1010")
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertTrue(any("not done" in w for w in warns))

    def test_suffixed_handle_cannot_self_peer(self):
        self.write("cl", ["260930.0900|cl|Acl|on|x", "260930.1000|cl|Tcl1|done|t"])
        self.write("clb", ["260930.1050|clb|Aclb|on|2nd instance", "260930.1100|clb|Tcl1|peer|lgtm"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))

    def test_one_letter_extension_is_the_same_writer(self):
        self.write("gp", ["260930.1000|gp|Agp|on|verbs", "260930.1000|gp|Tgp1|done|t"])
        self.write("gpt", ["260930.1001|gpt|Agpt|on|verbs", "260930.1100|gpt|Tgp1|ok|reviewed"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tgp1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))

    def test_hu_peer_is_not_self_approval(self):
        self.write("cl", ["260930.1000|cl|Tcl1|done|t"])
        self.write("hu", ["260930.1100|hu|Tcl1|peer|noted"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tcl1"]["status"], "peer")
        self.assertFalse(any("self-approval" in w for w in warns))

    def test_supersede_marks_old(self):
        self.write("cl", ["260901.1000|cl|Fcl1|live|timeout is 10s"])
        self.write("gpt", ["260902.1000|gpt|Fgpt1|live|timeout is 30s !Fcl1"])
        st, _, warns = self.state(now="260902.1000")
        self.assertEqual(st["Fcl1"]["status"], "old")
        self.assertEqual(st["Fgpt1"]["status"], "live")
        self.assertEqual(warns, [])

    def test_law_note_and_supersede(self):
        self.write("hu", ["260930.1000|hu|Fhu1|law|API timeout is 30s"])
        self.write("gk", ["260930.1100|gk|Fhu1|-|actually 10s, ignore the title"])
        self.write("gk", ["260930.1200|gk|Dgk1|live|use nose !Fhu1"])
        st, _, warns = self.state(now="260930.1200")
        self.assertEqual(st["Fhu1"]["status"], "law")
        self.assertEqual(st["Fhu1"]["note"], "")
        self.assertEqual(st["Dgk1"]["status"], "wrong")
        self.assertTrue(any("law note" in w for w in warns))
        self.assertTrue(any("cannot supersede law" in w for w in warns))

    def test_mentioning_law_does_not_mark_task_wrong(self):
        self.write("hu", ["260930.1000|hu|Dhu1|law|use pytest"])
        self.write("gk", ["260930.1100|gk|Tgk1|open|discuss whether to replace !Dhu1"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tgk1"]["status"], "open")
        self.assertEqual(st["Dhu1"]["status"], "law")
        self.assertFalse(any("cannot supersede law" in w for w in warns))

    def test_expired_takeover_is_not_double_claim(self):
        self.write("cl", ["260930.1001|cl|Tcl1|claim|ttl=10m"])
        self.write("gk", ["260930.1100|gk|Tcl1|claim|mine now"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tcl1"]["owner"], "gk")
        self.assertFalse(any("double claim" in w for w in warns))

    def test_default_ttl_expires(self):
        self.write("cl", ["260901.1000|cl|Tcl1|claim|no lease written"])
        st, _, _ = self.state(now="260901.1100")
        self.assertEqual(st["Tcl1"]["status"], "claim")
        st, _, warns = self.state(now="260901.1330")
        self.assertEqual(st["Tcl1"]["status"], "open")
        self.assertTrue(any("claim expired" in w for w in warns))

    def test_progress_note_extends_lease(self):
        self.write("cl", [
            "260930.1000|cl|Tcl1|claim|working",
            "260930.1100|cl|Tcl1|-|progress: half done",
            "260930.1145|cl|Tcl1|-|progress: almost there",
        ])
        st, _, warns = self.state(now="260930.1145")
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertFalse(any("expired" in w for w in warns))

    def test_impossible_date_is_format_error_not_crash(self):
        self.write("cl", ["260231.1000|cl|Tcl1|claim|working"])
        recs, errs = mem.load()
        self.assertEqual(recs, [])
        self.assertTrue(any("bad ts" in e for e in errs))
        st, warns = mem.fold(recs)
        self.assertEqual(st, {})
        self.assertEqual(warns, [])

    def test_future_typo_does_not_expire_claims(self):
        self.write("cl", ["260930.1000|cl|Tcl1|claim|working", "260930.1010|cl|Fcl1|live|x"])
        self.write("gk", ["991231.2358|gk|Fgk9|live|typo", "991231.2359|gk|Fgk8|live|same broken clock"])
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertTrue(any("ignored future ts" in w for w in warns))

    def test_long_log_clock_does_not_freeze(self):
        lines = []
        for i in range(600):
            dt = datetime(2026, 1, 1) + timedelta(days=i)
            lines.append(dt.strftime("%y%m%d") + ".1000|cl|Fcl%d|live|day %d" % (i + 1, i))
        self.write("cl", lines)
        recs, _ = mem.load()
        clock, outlier = mem.pick_now(recs)
        self.assertEqual(clock, lines[-1].split("|")[0])
        self.assertIsNone(outlier)

    def test_pause_is_not_a_typo(self):
        self.write("cl", ["260928.0900|cl|Tcl1|claim|working", "260928.0905|cl|Fcl1|live|x"])
        self.write("gk", ["260930.1200|gk|Fgk1|live|first write after a 2-day pause"])
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "open")
        self.assertFalse(any("ignored future" in w for w in warns))

    def test_agreeing_facts_are_not_conflicts(self):
        self.write("cl", [
            "260930.1000|cl|Fcl1|live|API base url is api.example.com #api",
            "260930.1001|cl|Fcl2|live|API timeout is 30s #api",
        ])
        _, _, warns = self.state(now="260930.1001")
        self.assertFalse(any("conflict" in w for w in warns))

    def test_decisions_same_tag_conflict(self):
        self.write("cl", ["260930.1000|cl|Dcl1|live|use pytest #test"])
        self.write("gpt", ["260930.1001|gpt|Dgpt1|live|use unittest #test"])
        _, _, warns = self.state(now="260930.1001")
        self.assertTrue(any("conflict #test" in w for w in warns))

    def test_path_hint_rejects_dotted_words(self):
        self.write("cl", ["260901.1000|cl|Fcl1|live|" + "uses Node.js and/or TCP/IP " + "x" * 70])
        self.write("gpt", ["260901.1100|gpt|Fgpt1|live|" + "long " + "x" * 70 + " see mem/notes/x.md"])
        self.write("gk", ["260901.1200|gk|Fgk1|live|" + "names mem/mem.py and .github/workflows/mem.yml " + "x" * 40])
        self.write("gm", ["260901.1300|gm|Fgm1|live|" + "See mem/ci_commit.sh and mem/log/ " + "x" * 50])
        _, _, warns = self.state(now="260901.1300")
        self.assertTrue(any("Fcl1 fact >80" in w for w in warns))
        self.assertFalse(any("Fgpt1 fact" in w for w in warns))
        self.assertFalse(any("Fgk1 fact" in w for w in warns))
        self.assertFalse(any("Fgm1 fact" in w for w in warns))

    def test_law_sorts_ahead_of_live(self):
        lines = ["260930.0900|hu|Dhu1|law|use pytest"]
        lines += ["260930.%04d|gk|Dgk%d|live|decision %d" % (1000 + i, i, i) for i in range(1, 16)]
        self.write("hu", lines[:1])
        self.write("gk", lines[1:])
        recs, errs = mem.load()
        st, warns = mem.fold(recs, now="260930.1015")
        snap, rest = mem.snapshot(recs, errs, st, warns)
        self.assertIn("|Dhu1|law|", snap)
        self.assertNotIn("|Dhu1|law|", rest)

    def test_snap_uses_latest_log_not_wall_clock(self):
        self.write("cl", ["260901.1000|cl|Tcl1|claim|ttl=30m"])
        recs, errs = mem.load()
        st, warns = mem.fold(recs)
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertFalse(any("expired" in w for w in warns))
        snap, _ = mem.snapshot(recs, errs, st, warns)
        self.assertIn("spec=1", snap.splitlines()[0])

    def test_forward_reference_ok_but_never_created_warns(self):
        self.write("cl", [
            "260901.1000|cl|Tcl1|drop|replaced by ^Tcl2",
            "260901.1001|cl|Tcl2|open|new one",
            "260901.1002|cl|Fcl1|live|see ^Tcl99",
        ])
        _, _, warns = self.state(now="260901.1002")
        self.assertEqual(len(warns), 1)
        self.assertIn("unknown Tcl99", warns[0])

    def test_format_errors(self):
        self.write("cl", [
            "260901.1000|gpt|Tgpt1|open|wrong file",
            "2026-09-01|cl|Tcl1|open|bad ts",
            "260901.1000|cl|Tcl2|bogus|bad status",
            "260901.1000|cl|Acl1|on|A with n",
            "260901.1000|cl|Fcl1|live|token=sk-abcdefghijklmnopqrstuvwxyz1234",
            "260901.1000|cl|Fcl2|live|" + "x" * 121,
        ])
        _, errs, _ = self.state(now="260901.1000")
        self.assertEqual(len(errs), 6, errs)

    def test_snapshot_caps_and_order(self):
        lines = ["260901.%04d|cl|Tcl%d|open|task %d" % (i, i, i) for i in range(1, 31)]
        lines += ["260902.0001|cl|Tcl30|done|finished", "260902.0002|cl|Tcl29|block|waiting on ^Tcl1"]
        self.write("cl", lines)
        recs, errs = mem.load()
        now, rest = mem.snapshot(recs, errs, *mem.fold(recs, now="260902.0002"))
        rows = [l for l in now.splitlines() if l.startswith("2609")]
        self.assertEqual(len(rows), 25)
        self.assertIn("|Tcl30|done|", rows[0])
        self.assertIn("|Tcl29|block|", rows[1])
        self.assertIn("#tasks 25 +5 in rest.l", now)
        self.assertEqual(len([l for l in rest.splitlines() if l.startswith("2609")]), 5)
        self.assertIn("rest=5", now.splitlines()[0])
        self.assertTrue(any(l.startswith("#k ts|who|id|status|title|note") for l in now.splitlines()))

    def test_add_mints_ids(self):
        mem.cmd_add("cl", "T", "open", "first")
        mem.cmd_add("cl", "T", "open", "second")
        mem.cmd_add("cl", "A", "on", "claude verbs=shell")
        mem.cmd_add("gpt", "Tcl2", "claim", "mine now")
        st, errs, _ = self.state()
        self.assertEqual(errs, [])
        self.assertEqual(sorted(st), ["Acl", "Tcl1", "Tcl2"])
        self.assertEqual(st["Tcl2"]["status"], "claim")
        self.assertTrue(os.path.exists(mem.NOW))
        self.assertTrue(os.path.exists(mem.REST))
        month = "20" + mem.utcnow()[:2] + "-" + mem.utcnow()[2:4]
        self.assertEqual(sorted(os.listdir(mem.LOG)), ["cl.%s.l" % month, "gpt.%s.l" % month])
        with self.assertRaises(SystemExit):
            mem.cmd_add("cl", "F", "live", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234")

    def test_review_records_human_decision_marked_via_agent(self):
        self.write("cl", ["260901.1000|cl|Tcl1|done|did it", "260901.1001|cl|Tcl2|done|did more"])
        self.review("cl", "Tcl1", "ok", "looks good | ship")
        self.review("gpt", "Tcl2", "redo", "tests missing")
        st, errs, warns = self.state()
        self.assertEqual((st["Tcl1"]["status"], st["Tcl2"]["status"]), ("ok", "redo"))
        self.assertEqual(errs, [])
        self.assertFalse(any("self-approval" in w for w in warns))
        self.assertEqual(st["Tcl1"]["who"], "hu")
        self.assertEqual(st["Tcl1"]["note"], "via:cl looks good / ship")
        self.assertEqual(st["Tcl2"]["note"], "via:gpt tests missing")

    def test_review_refuses_bad_requests(self):
        self.write("hu", ["260901.1000|hu|Thu1|done|human did this"])
        self.write("cl", ["260901.1001|cl|Tcl1|open|not done yet", "260901.1002|cl|Tcl2|done|ok"])
        for args in (("cl", "Thu1", "ok"), ("cl", "Tcl1", "ok"), ("cl", "Tcl99", "ok"), ("cl", "Fcl1", "ok"),
                     ("hu", "Tcl2", "ok"), ("cl", "Tcl2", "maybe"), ("cl", "Tcl2", "ok", "token=sk-abcdefghijklmnopqrstuvwxyz1234")):
            with self.assertRaises(SystemExit, msg=str(args)):
                self.review(*args)
        st, _, _ = self.state(now="260901.1002")
        self.assertEqual((st["Thu1"]["status"], st["Tcl1"]["status"], st["Tcl2"]["status"]), ("done", "open", "done"))


if __name__ == "__main__":
    unittest.main()
