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
        self.write("cl", ["2026-09-01T10:00Z|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["2026-09-01T11:00Z|gpt|Tcl1|claim|on it"])
        st, errs, warns = self.state()
        self.assertEqual(errs, [])
        self.assertEqual(st["Tcl1"]["status"], "claim")
        self.assertEqual(st["Tcl1"]["title"], "Do thing")
        self.assertEqual(st["Tcl1"]["note"], "on it")
        self.assertEqual(st["Tcl1"]["who"], "gpt")

    def test_self_approval_ignored(self):
        self.write("cl", [
            "2026-09-01T10:00Z|cl|Tcl1|open|Do thing",
            "2026-09-01T11:00Z|cl|Tcl1|done|finished",
            "2026-09-01T12:00Z|cl|Tcl1|ok|looks good to me",
        ])
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "done")
        self.assertTrue(any("self-approval" in w for w in warns))
        self.write("gpt", ["2026-09-01T13:00Z|gpt|Tcl1|ok|verified"])
        st, _, _ = self.state()
        self.assertEqual(st["Tcl1"]["status"], "ok")

    def test_creator_may_approve_other_agents_work(self):
        self.write("cl", ["2026-09-01T10:00Z|cl|Tcl1|open|Do thing"])
        self.write("gpt", ["2026-09-01T11:00Z|gpt|Tcl1|done|did it"])
        self.write("cl", ["2026-09-01T12:00Z|cl|Tcl1|ok|reviewed"])
        st, _, warns = self.state()
        self.assertEqual(st["Tcl1"]["status"], "ok")
        self.assertEqual(warns, [])

    def test_supersede_marks_old(self):
        self.write("cl", ["2026-09-01T10:00Z|cl|Fcl1|live|timeout is 10s"])
        self.write("gpt", ["2026-09-02T10:00Z|gpt|Fgpt1|live|timeout is 30s !Fcl1"])
        st, _, warns = self.state()
        self.assertEqual(st["Fcl1"]["status"], "old")
        self.assertEqual(st["Fgpt1"]["status"], "live")
        self.assertEqual(warns, [])
        snap = mem.snapshot(*mem.load(), *mem.fold(mem.load()[0]))
        self.assertIn("Fgpt1|live", snap)
        self.assertNotIn("Fcl1|old", snap)

    def test_format_errors(self):
        self.write("cl", [
            "2026-09-01T10:00Z|gpt|Tgpt1|open|wrong file",
            "2026-09-01|cl|Tcl1|open|bad ts",
            "2026-09-01T10:00Z|cl|Tcl2|bogus|bad status",
            "2026-09-01T10:00Z|cl|Acl1|on|A with n",
            "2026-09-01T10:00Z|cl|Fcl1|live|token=sk-abcdefghijklmnopqrstuvwxyz1234",
        ])
        _, errs, _ = self.state()
        self.assertEqual(len(errs), 5, errs)

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
        with self.assertRaises(SystemExit):
            mem.cmd_add("cl", "F", "live", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234")


if __name__ == "__main__":
    unittest.main()
