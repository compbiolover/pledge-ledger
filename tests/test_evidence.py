import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import evidence as e  # noqa: E402

OFFICIALS = {"S-MS": {"official_id": "S-MS", "name": "Scott Colom", "state": "MS", "state_name": "Mississippi",
                      "office": "Senator", "term_start": "2027-01-03"},
             "TN": {"official_id": "TN", "name": "Marsha Blackburn", "state": "TN", "state_name": "Tennessee",
                    "office": "Governor", "term_start": ""}}


def pledge(pid, text, off="S-MS"):
    return {"pledge_id": pid, "official_id": off, "pledge_text": text}


PLEDGES = [pledge("S-MS-001", "Vote to take back Congress’s power over tariffs"),
           pledge("S-MS-006", "Work to end the federal income tax for Mississippians making under $75,000"),
           pledge("S-MS-040", "Reduce VA wait times"),
           pledge("TN-001", "Eliminate the state grocery tax", off="TN"),
           pledge("TN-002", "Cut the income tax", off="TN")]


class Terms(unittest.TestCase):
    def setUp(self):
        self.terms = e.search_terms(PLEDGES, OFFICIALS)

    def test_drops_filler_names_and_demonyms(self):
        self.assertEqual(set(self.terms["S-MS-001"]), {"tariff", "power"})
        self.assertNotIn("mississippian", self.terms["S-MS-006"])
        self.assertNotIn("work", self.terms["S-MS-006"])

    def test_keeps_two_letter_acronyms(self):
        self.assertIn("va", self.terms["S-MS-040"])

    def test_rarest_words_first(self):
        # "income" and "tax" appear in more promises than "grocery", so grocery leads
        self.assertEqual(self.terms["TN-001"][0], "grocery")

    def test_same_rule_whatever_the_official(self):
        a = e.search_terms([pledge("X-1", "Ban stock trading", off="S-MS")], OFFICIALS)["X-1"]
        b = e.search_terms([pledge("X-1", "Ban stock trading", off="TN")], OFFICIALS)["X-1"]
        self.assertEqual(a, b)

    def test_matching_needs_two_terms_or_the_only_one(self):
        self.assertEqual(e.matched("Reclaiming Congressional Tariff Power Act", ["tariff", "power"]), ["tariff", "power"])
        self.assertEqual(e.matched("Electric Power Reliability Act", ["tariff", "power"]), [])
        self.assertEqual(e.matched("VA Wait Time Accountability Act", ["va"]), ["va"])
        self.assertEqual(e.matched("Anything", []), [])

    def test_stems_match_word_forms(self):
        self.assertEqual(e.stem("tariffs"), e.stem("tariff"))
        self.assertEqual(e.stem("trading"), e.stem("trade"))
        self.assertEqual(e.stem("Congress’s"), e.stem("congress"))


class Helpers(unittest.TestCase):
    def test_congress_number_and_urls(self):
        self.assertEqual(e.congress_of(2027), 120)
        self.assertEqual(e.congress_of(2026), 119)
        self.assertEqual(e.bill_url(120, "S", "12"), "https://www.congress.gov/bill/120th-congress/senate-bill/12")
        self.assertEqual(e.bill_url(121, "HJRES", "3"), "https://www.congress.gov/bill/121st-congress/house-joint-resolution/3")
        self.assertEqual(e.bill_url(119, "SAMDT", "3"), "")

    def test_window(self):
        self.assertTrue(e.in_window("2027-04-13", "2027-01-03", "2027-04-13"))
        self.assertFalse(e.in_window("2027-04-14", "2027-01-03", "2027-04-13"))
        self.assertFalse(e.in_window("", "2027-01-03", "2027-04-13"))


MENU = b"""<?xml version="1.0"?><vote_summary><congress>120</congress><session>1</session><congress_year>2027</congress_year>
<votes><vote><vote_number>00012</vote_number><vote_date>04-Mar</vote_date><issue>S.J.Res. 4</issue>
<question>On the Joint Resolution
</question><result>Passed</result><title>A joint resolution terminating tariff power emergencies</title></vote>
<vote><vote_number>00013</vote_number><vote_date>20-Apr</vote_date><issue>S. 9</issue><question>On Passage</question>
<result>Passed</result><title>Tariff power act, after the review date</title></vote></votes></vote_summary>"""
VOTE = b"""<?xml version="1.0"?><roll_call_vote><members>
<member><member_full>Colom (D-MS)</member_full><last_name>Colom</last_name><state>MS</state><vote_cast>Yea</vote_cast></member>
<member><member_full>Wicker (R-MS)</member_full><last_name>Wicker</last_name><state>MS</state><vote_cast>Nay</vote_cast></member>
</members></roll_call_vote>"""


class Sources(unittest.TestCase):
    def setUp(self):
        self.terms = e.search_terms(PLEDGES, OFFICIALS)

    def test_senate_votes(self):
        def fake(url, **kw):
            if "vote_menu_120_1" in url:
                return MENU
            if "vote_120_1_00012" in url:
                return VOTE
            raise e.urllib.error.HTTPError(url, 404, "nf", None, None)
        with mock.patch.object(e, "get", side_effect=fake):
            rows = e.vote_items([OFFICIALS["S-MS"]], {"S-MS": PLEDGES[:3]}, self.terms,
                                {"S-MS": ("2027-01-03", "2027-04-13")}, "2027-04-13")
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["pledge_id"], rows[0]["date"]), ("S-MS-001", "2027-03-04"))
        self.assertIn("voted Yea", rows[0]["detail"])

    def test_legiscan(self):
        sessions = {"status": "OK", "sessions": [
            {"session_id": 2100, "year_start": 2027, "year_end": 2028, "session_name": "115th General Assembly"},
            {"session_id": 2000, "year_start": 2025, "year_end": 2026, "session_name": "114th General Assembly"}]}
        master = {"status": "OK", "masterlist": {
            "session": {"session_id": 2100},
            "0": {"number": "SB1", "title": "Grocery Tax Repeal", "description": "Repeals the state sales tax on groceries.",
                  "status": "4", "last_action_date": "2027-03-01", "last_action": "Signed by Governor",
                  "url": "https://legiscan.com/TN/bill/SB1/2027"},
            "1": {"number": "HB2", "title": "Roads", "description": "Highway funding.", "status": "1",
                  "last_action_date": "2027-02-01", "last_action": "Filed", "url": "https://legiscan.com/TN/bill/HB2/2027"}}}
        calls = []

        def fake(url, **kw):
            calls.append(url)
            return json.dumps(sessions if "getSessionList" in url else master).encode()
        with mock.patch.object(e, "get", side_effect=fake):
            rows = e.legiscan_items(OFFICIALS["TN"], PLEDGES[3:], self.terms, "2027-01-01", "2027-04-13", "k")
        self.assertEqual([r["pledge_id"] for r in rows], ["TN-001"])
        self.assertIn("Passed", rows[0]["detail"])
        self.assertEqual(sum("getMasterList" in u for u in calls), 1)  # the 2025-26 session is skipped

    def test_gdelt(self):
        body = json.dumps({"articles": [{"url": "https://example.com/a", "title": "Colom backs tariff vote",
                                         "seendate": "20270301T120000Z", "domain": "example.com"}]}).encode()
        seen = []

        def fake(url, **kw):
            seen.append(url)
            return body
        ws = e.gdelt_words(PLEDGES, self.terms)
        self.assertEqual(set(ws["S-MS-001"]), {"tariffs", "power"})
        with mock.patch.object(e, "get", side_effect=fake):
            rows = e.gdelt_items(OFFICIALS["S-MS"], PLEDGES[:1], self.terms, "2027-01-03", "2027-04-13", ws)
        self.assertEqual(rows[0]["date"], "2027-03-01")
        self.assertIn("%22Scott+Colom%22", seen[0])
        self.assertIn("startdatetime=20270114000000", seen[0])  # cut to GDELT's 3-month reach


if __name__ == "__main__":
    unittest.main()
