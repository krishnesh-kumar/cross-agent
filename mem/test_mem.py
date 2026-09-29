"""Unit tests for mem.py. Run: python3 -m unittest mem/test_mem.py"""
import os
import shutil
import tempfile
import unittest

import importlib.util

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

    def write(self, who, lines):
        with open(os.path.join(mem.LOG, who + ".2026-09.l"), "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

    def state(self):
        recs, errs = mem.load()
        st, warns = mem.fold(recs)
        return st, errs, warns

    def test_patch_latest_wins_across_files(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|claim|on it"])
        st, errs, warns = self.state()
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
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))
        self.write("gpt", ["260901.1300|gpt|Tcl1|ok|verified"])
        st, _, _ = self.state()
        self.assertEqual(st["Tcl1"]["status"], "ok")

    def test_creator_may_approve_other_agents_work(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|done|did it"])
        self.write("cl", ["260901.1200|cl|Tcl1|ok|reviewed"])
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "ok")
        self.assertEqual(warns, [])

    def test_supersede_marks_old(self):
        self.write("cl", ["260901.1000|cl|Fcl1|live|timeout is 10s"])
        self.write("gpt", ["260902.1000|gpt|Fgpt1|live|timeout is 30s !Fcl1"])
        st, _, warns = self.state()
        self.assertEqual(st["Fcl1"]["status"], "old")
        self.assertEqual(st["Fgpt1"]["status"], "live")
        self.assertEqual(warns, [])
        snap, _ = mem.snapshot(*mem.load(), *mem.fold(mem.load()[0]))
        self.assertIn("Fgpt1|live", snap)
        self.assertNotIn("Fcl1|old", snap)

    def test_forward_reference_ok_but_never_created_warns(self):
        self.write("cl", ["260901.1000|cl|Tcl1|drop|replaced by ^Tcl2", "260901.1001|cl|Tcl2|open|new one",
                          "260901.1002|cl|Fcl1|live|see ^Tcl99"])
        _, _, warns = self.state()
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
        _, errs, _ = self.state()
        self.assertEqual(len(errs), 6, errs)

    def test_snapshot_caps_and_order(self):
        lines = ["260901.%04d|cl|Tcl%d|open|task %d" % (i, i, i) for i in range(1, 31)]
        lines += ["260902.0001|cl|Tcl30|done|finished", "260902.0002|cl|Tcl29|block|waiting on ^Tcl1"]
        self.write("cl", lines)
        recs, errs = mem.load()
        now, rest = mem.snapshot(recs, errs, *mem.fold(recs))
        rows = [l for l in now.splitlines() if l.startswith("2609")]
        self.assertEqual(len(rows), 25)
        self.assertIn("|Tcl30|done|", rows[0])
        self.assertIn("|Tcl29|block|", rows[1])
        self.assertIn("#tasks 25 +5 in rest.l", now)
        self.assertEqual(len([l for l in rest.splitlines() if l.startswith("2609")]), 5)
        self.assertIn("rest=5", now.splitlines()[0])
        self.assertTrue(now.splitlines()[1].startswith("#k ts|who|id|status|title|note"))

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

    def review(self, *args):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            mem.cmd_review(*args)

    def test_review_records_human_decision_marked_via_agent(self):
        self.write("cl", ["260901.1000|cl|Tcl1|done|did it", "260901.1001|cl|Tcl2|done|did more"])
        self.review("cl", "Tcl1", "ok", "looks good | ship")
        self.review("gpt", "Tcl2", "redo", "tests missing")
        st, errs, warns = self.state()
        self.assertEqual((st["Tcl1"]["status"], st["Tcl2"]["status"]), ("ok", "redo"))
        self.assertEqual((errs, warns), ([], []))
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
        st, _, _ = self.state()
        self.assertEqual((st["Thu1"]["status"], st["Tcl1"]["status"], st["Tcl2"]["status"]), ("done", "open", "done"))


if __name__ == "__main__":
    unittest.main()
