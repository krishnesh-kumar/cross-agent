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

    def state(self, now=None):
        recs, errs = mem.load()
        st, warns = mem.fold(recs, now=now)
        return st, errs, warns

    def test_patch_latest_wins_across_files(self):
        self.write("cl", ["260901.1000|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["260901.1100|gpt|Tcl1|claim|on it"])
        st, errs, _ = self.state(now="260901.1100")
        self.assertEqual(errs, [])
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertEqual(st["Tcl1"]["title"], "Do thing")

    def test_self_approval_ignored(self):
        self.write("cl", [
            "260901.1000|cl|Tcl1|open|Do thing",
            "260901.1100|cl|Tcl1|done|finished",
            "260901.1200|cl|Tcl1|ok|looks good to me",
        ])
        st, _, warns = self.state(now="260901.1200")
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))

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
        self.write("cl", ["260930.1000|cl|Tcl1|done|t"])
        self.write("clb", ["260930.1100|clb|Tcl1|peer|lgtm"])
        st, _, warns = self.state(now="260930.1100")
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))

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
        self.write("cl", ["260901.1000|cl|Fcl1|live|" + "uses Node.js " + "x" * 80])
        self.write("gpt", ["260901.1100|gpt|Fgpt1|live|" + "long " + "x" * 80 + " see mem/notes/x.md"])
        _, _, warns = self.state(now="260901.1100")
        self.assertTrue(any("Fcl1 fact >80" in w for w in warns))
        self.assertFalse(any("Fgpt1 fact" in w for w in warns))

    def test_snap_uses_latest_log_not_wall_clock(self):
        self.write("cl", ["260901.1000|cl|Tcl1|claim|ttl=30m"])
        recs, errs = mem.load()
        st, warns = mem.fold(recs)
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertFalse(any("expired" in w for w in warns))
        snap, _ = mem.snapshot(recs, errs, st, warns)
        self.assertIn("spec=1", snap.splitlines()[0])

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


if __name__ == "__main__":
    unittest.main()
