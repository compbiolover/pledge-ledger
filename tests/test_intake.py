import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import intake_ratings  # noqa: E402

URL = "https://github.com/user-attachments/files/123456/awillems.csv"


def body(coder="awillems", file=f"[awillems.csv]({URL})"):
    return f"### Reviewer ID\n\n{coder}\n\n### Ratings file\n\n{file}\n"


class Intake(unittest.TestCase):
    def test_parses_issue_form(self):
        self.assertEqual(intake_ratings.parse(body(coder="AWillems ")), ("awillems", URL))

    def test_rejects_bad_id(self):
        for bad in ["", "../main", "a", "x; rm -rf /"]:
            with self.assertRaises(SystemExit):
                intake_ratings.parse(body(coder=bad))

    def test_rejects_missing_extra_or_foreign_files(self):
        for f in ["pid,coder\nNC-001,awillems", f"{URL}\n{URL.replace('123456', '7')}",
                  "https://evil.example/files/1/awillems.csv",
                  "https://github.com/user-attachments/files/1/awillems.exe"]:
            with self.assertRaises(SystemExit):
                intake_ratings.parse(body(file=f))


if __name__ == "__main__":
    unittest.main()
