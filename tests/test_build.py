import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import build  # noqa: E402


def ev(pid, coder, task="status", period="2027-04-30", rated_at="2027-05-01", **kw):
    r = {k: "" for k in build.RATING_COLUMNS}
    r.update(pledge_id=pid, coder=coder, task=task, period_end=period if task == "status" else "",
             rated_at=rated_at, codebook_version="1.0", _file=f"{coder}.csv", _line=2)
    r.update(kw)
    return r


class Stats(unittest.TestCase):
    def test_kappa_textbook(self):
        # 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> kappa 0.4
        pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
        self.assertAlmostEqual(build.cohen_kappa(pairs), 0.4, places=6)

    def test_kappa_perfect_and_undefined(self):
        self.assertEqual(build.cohen_kappa([("a", "a"), ("b", "b")]), 1.0)
        self.assertIsNone(build.cohen_kappa([]))
        self.assertIsNone(build.cohen_kappa([("a", "a")] * 3))  # single category

    def test_weighted_kappa_penalizes_far_more(self):
        cats = build.EFFORTS
        near = [("2", "3")] * 5 + [("0", "0")] * 5 + [("4", "4")] * 5
        far = [("0", "4")] * 5 + [("0", "0")] * 5 + [("4", "4")] * 5
        self.assertGreater(build.cohen_kappa(near, cats, "quadratic"),
                           build.cohen_kappa(far, cats, "quadratic"))

    def test_weighted_kappa_known_value(self):
        # 3-point scale; by hand: po=0.9375, pe=0.6875 -> 0.8
        cats = ["0", "1", "2"]
        pairs = [("0", "0"), ("1", "1"), ("2", "2"), ("0", "1")]
        self.assertAlmostEqual(build.cohen_kappa(pairs, cats, "quadratic"), 0.8, places=6)

    def test_wilson(self):
        lo, hi = build.wilson(5, 10)
        self.assertAlmostEqual(lo, 0.2366, places=3)
        self.assertAlmostEqual(hi, 0.7634, places=3)
        self.assertIsNone(build.wilson(0, 0))


class Consensus(unittest.TestCase):
    def test_single_coder_is_pending(self):
        res, _, _ = build.consensus([ev("X-1", "ann", outcome="kept", effort="2")], [])
        f = res[("X-1", "status", "2027-04-30")]["fields"]
        self.assertEqual(f["outcome"]["state"], "pending")
        self.assertIsNone(f["outcome"]["value"])

    def test_agreement_and_dispute(self):
        rs = [ev("X-1", "ann", outcome="kept", effort="2"),
              ev("X-1", "bob", outcome="kept", effort="3")]
        f = build.consensus(rs, [])[0][("X-1", "status", "2027-04-30")]["fields"]
        self.assertEqual((f["outcome"]["state"], f["outcome"]["value"]), ("agreed", "kept"))
        self.assertEqual(f["effort"]["state"], "disputed")
        self.assertEqual(f["blocker"]["value"], "")  # blocker ignored when kept

    def test_latest_rating_per_coder_wins(self):
        rs = [ev("X-1", "ann", outcome="broken", effort="1", blocker="courts", rated_at="2027-05-01"),
              ev("X-1", "ann", outcome="kept", effort="2", rated_at="2027-05-03"),
              ev("X-1", "bob", outcome="kept", effort="2")]
        f = build.consensus(rs, [])[0][("X-1", "status", "2027-04-30")]["fields"]
        self.assertEqual(f["outcome"]["value"], "kept")

    def test_adjudication_overrides(self):
        rs = [ev("X-1", "ann", outcome="partial", effort="2", blocker="budget"),
              ev("X-1", "bob", outcome="broken", effort="2", blocker="budget")]
        adj = [{"pledge_id": "X-1", "task": "status", "period_end": "2027-04-30", "field": "outcome",
                "final_value": "partial", "adjudicator": "cat", "decided_at": "2027-05-04",
                "reason": "Amount enacted was half the pledge"}]
        f = build.consensus(rs, adj)[0][("X-1", "status", "2027-04-30")]["fields"]
        self.assertEqual((f["outcome"]["state"], f["outcome"]["value"]), ("adjudicated", "partial"))

    def test_merge_decision_value(self):
        rs = [ev("X-2", "ann", task="extraction", decision="merge", merge_into="X-1", testable="Y", verbatim_ok="Y"),
              ev("X-2", "bob", task="extraction", decision="merge", merge_into="X-1", testable="Y", verbatim_ok="Y")]
        f = build.consensus(rs, [])[0][("X-2", "extraction", "")]["fields"]
        self.assertEqual(f["decision"]["value"], "merge:X-1")

    def test_periods_are_separate(self):
        rs = [ev("X-1", "ann", outcome="in_progress", effort="2", blocker="too_early", period="2027-04-30"),
              ev("X-1", "bob", outcome="in_progress", effort="2", blocker="too_early", period="2027-04-30"),
              ev("X-1", "ann", outcome="kept", effort="3", period="2027-12-31", rated_at="2028-01-02")]
        res = build.consensus(rs, [])[0]
        self.assertEqual(res[("X-1", "status", "2027-04-30")]["fields"]["outcome"]["state"], "agreed")
        self.assertEqual(res[("X-1", "status", "2027-12-31")]["fields"]["outcome"]["state"], "pending")


class Safety(unittest.TestCase):
    def test_adjudication_cannot_override_single_coder(self):
        rs = [ev("X-1", "ann", outcome="in_progress", effort="2", blocker="too_early")]
        adj = [{"pledge_id": "X-1", "task": "status", "period_end": "2027-04-30", "field": "outcome",
                "final_value": "kept", "adjudicator": "cat", "decided_at": "2027-05-04", "reason": "x"}]
        res, _, errs = build.consensus(rs, adj)
        self.assertEqual(res[("X-1", "status", "2027-04-30")]["fields"]["outcome"]["state"], "pending")
        self.assertTrue(errs)

    def test_blocker_pairs_skip_kept(self):
        rs = [ev("X-1", "ann", outcome="kept", effort="2"), ev("X-1", "bob", outcome="kept", effort="2"),
              ev("X-2", "ann", outcome="broken", effort="1", blocker="courts"),
              ev("X-2", "bob", outcome="broken", effort="1", blocker="budget")]
        _, pairs, _ = build.consensus(rs, [])
        self.assertEqual(len(pairs[("status", "blocker", "ann", "bob")]), 1)

    def test_evidence_counts_citers(self):
        rs = [ev("X-1", "ann", outcome="kept", effort="2", evidence_urls="https://a|https://b"),
              ev("X-1", "bob", outcome="kept", effort="2", evidence_urls="https://a")]
        res, _, _ = build.consensus(rs, [])
        cited = {e["url"]: e["cited_by"] for e in res[("X-1", "status", "2027-04-30")]["evidence"]}
        self.assertEqual(cited, {"https://a": 2, "https://b": 1})


class Validation(unittest.TestCase):
    def setUp(self):
        self.off = [{"official_id": "X", "party": "D", "office": "Governor"}]
        self.pl = [{"pledge_id": "X-1", "official_id": "X", "pledge_text": "Do a thing", "archive_url": "https://web.archive.org/x"}]

    def test_blocker_required_when_not_kept(self):
        errs, _ = build.validate(self.off, self.pl, [ev("X-1", "ann", outcome="broken", effort="1")], [], [])
        self.assertTrue(any("blocker" in e for e in errs))

    def test_unknown_pledge(self):
        errs, _ = build.validate(self.off, self.pl, [ev("Z-9", "ann", outcome="not_rated", effort="0",
                                                        blocker="too_early")], [], [])
        self.assertTrue(any("unknown pledge_id" in e for e in errs))

    def test_rejects_javascript_urls(self):
        errs, _ = build.validate(self.off, self.pl, [ev("X-1", "ann", outcome="kept", effort="2",
                                                        evidence_urls="javascript:alert(1)")], [], [])
        self.assertTrue(any("http" in e for e in errs))

    def test_rejects_bad_adjudication_value(self):
        adj = [{"pledge_id": "X-1", "task": "status", "period_end": "2027-04-30", "field": "outcome",
                "final_value": "x\"><img>", "adjudicator": "c", "decided_at": "2027-05-04", "reason": "r"}]
        errs, _ = build.validate(self.off, self.pl, [], adj, [])
        self.assertTrue(any("invalid final_value" in e for e in errs))

    def test_rejects_self_merge(self):
        errs, _ = build.validate(self.off, self.pl, [ev("X-1", "ann", task="extraction", decision="merge",
                                                        merge_into="X-1", testable="Y", verbatim_ok="Y")], [], [])
        self.assertTrue(any("merge_into" in e for e in errs))

    def test_rejects_unknown_office(self):
        errs, _ = build.validate([{"official_id": "X", "party": "D", "office": "Mayor"}], self.pl, [], [], [])
        self.assertTrue(any("office" in e for e in errs))

    def test_congress_blockers_allowed(self):
        errs, _ = build.validate(self.off, self.pl, [ev("X-1", "ann", outcome="broken", effort="2", blocker="filibuster",
                                                        evidence_urls="https://x")], [], [])
        self.assertEqual(errs, [])

    def test_valid_passes(self):
        errs, _ = build.validate(self.off, self.pl, [ev("X-1", "ann", outcome="kept", effort="2",
                                                        evidence_urls="https://x")], [], [])
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main()


class PreregAndCorrections(unittest.TestCase):
    def setUp(self):
        self.p = {"pledge_id": "X-1", "official_id": "X", "pledge_text": "Do a thing", "source_url": "https://a"}
        self.manifest = {"pledges": {"X-1": build.pledge_hash(self.p)}}

    def test_no_manifest_means_no_status(self):
        st, errs = build.check_prereg([self.p], None, [])
        self.assertEqual((st, errs), ({"X-1": None}, []))

    def test_unchanged_is_frozen_and_new_is_added(self):
        new = dict(self.p, pledge_id="X-2")
        st, errs = build.check_prereg([self.p, new], self.manifest, [])
        self.assertEqual(st, {"X-1": "frozen", "X-2": "added"})
        self.assertEqual(errs, [])

    def test_change_without_correction_fails(self):
        edited = dict(self.p, pledge_text="Do a different thing")
        st, errs = build.check_prereg([edited], self.manifest, [])
        self.assertEqual(st["X-1"], "changed")
        self.assertTrue(errs)

    def test_change_with_correction_passes(self):
        edited = dict(self.p, source_url="https://b")
        corr = [{"pledge_id": "X-1", "kind": "source"}]
        self.assertEqual(build.check_prereg([edited], self.manifest, corr)[1], [])

    def test_rating_correction_does_not_excuse_quote_change(self):
        edited = dict(self.p, pledge_text="Other")
        self.assertTrue(build.check_prereg([edited], self.manifest, [{"pledge_id": "X-1", "kind": "rating"}])[1])

    def test_whitespace_only_change_is_not_a_change(self):
        st, _ = build.check_prereg([dict(self.p, pledge_text="Do a thing  ")], self.manifest, [])
        self.assertEqual(st["X-1"], "frozen")

    def test_corrections_validation(self):
        good = {"date": "2027-02-01", "pledge_id": "X-1", "kind": "quote", "what_changed": "Fixed typo", "issue_url": ""}
        self.assertEqual(build.validate_corrections([good], {"X-1"}), [])
        bad = {"date": "Feb 1", "pledge_id": "Z", "kind": "oops", "what_changed": "", "issue_url": "javascript:x"}
        self.assertEqual(len(build.validate_corrections([bad], {"X-1"})), 5)
