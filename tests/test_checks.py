import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import check_pledges as c  # noqa: E402

PAGE = ("<html><head><style>p{}</style><script>var x='Ban stock trading';</script></head><body>"
        "<li>Vote to take back Congress’s power over tariffs</li>"
        "<p>that&#8217;s something that I absolutely would support abolishing or at least\n"
        "significantly reforming the filibuster, she said.</p>"
        "<p>Fight for a seat on the Agriculture Committee – not Washington</p></body></html>").encode()


def row(pid, text, off="S-XX", group=""):
    return {"pledge_id": pid, "official_id": off, "pledge_text": text, "compound_group": group}


class Quotes(unittest.TestCase):
    def setUp(self):
        self.text = c.page_text(PAGE)

    def test_finds_quote_despite_curly_apostrophe_entity_and_line_break(self):
        q = "that's something that I absolutely would support abolishing or at least significantly reforming the filibuster,"
        self.assertEqual(c.quote_status(q, self.text), "ok")

    def test_finds_quote_with_straight_apostrophe_and_dash(self):
        self.assertEqual(c.quote_status("Vote to take back Congress's power over tariffs", self.text), "ok")
        self.assertEqual(c.quote_status("Fight for a seat on the Agriculture Committee - not Washington", self.text), "ok")

    def test_flags_changed_words_and_case(self):
        self.assertEqual(c.quote_status("Vote to take back Congress's power over all tariffs", self.text), "missing")
        self.assertEqual(c.quote_status("vote to take back congress's power over tariffs", self.text), "case_only")

    def test_ignores_script_text(self):
        self.assertEqual(c.quote_status("Ban stock trading", self.text), "missing")

    def test_handles_gzip(self):
        import gzip
        self.assertEqual(c.page_text(gzip.compress(PAGE)), self.text)


class Rows(unittest.TestCase):
    def test_text_checks(self):
        self.assertEqual([k for k, _ in c.text_checks(row("A", "Cut taxes ... for everyone"))], ["ellipsis"])
        self.assertEqual([k for k, _ in c.text_checks(row("A", " ".join(["word"] * 41)))], ["over_40_words"])
        self.assertEqual(c.text_checks(row("A", "Cut the grocery tax.")), [])

    def test_duplicates_skip_compound_groups_and_other_officials(self):
        rows = [row("A-1", "Eliminate the state grocery tax."),
                row("A-2", "Eliminate the state grocery tax"),
                row("B-1", "Eliminate the state grocery tax.", off="S-YY"),
                row("A-3", "Raise the minimum wage and index it.", group="G"),
                row("A-4", "Raise the minimum wage and index it.", group="G"),
                row("A-5", "Build a new bridge over the river.")]
        self.assertEqual([(a["pledge_id"], b["pledge_id"]) for a, b, _ in c.duplicates(rows)], [("A-1", "A-2")])

    def test_raw_url(self):
        self.assertEqual(c.raw_url("https://web.archive.org/web/20261029092610/https://x.com/a/"),
                         "https://web.archive.org/web/20261029092610id_/https://x.com/a/")


if __name__ == "__main__":
    unittest.main()
