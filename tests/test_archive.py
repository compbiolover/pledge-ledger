import gzip
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import archive_sources  # noqa: E402

SITEGROUND = b"<html><head><title>One moment, please...</title></head><body>Please wait while your request is being verified...</body></html>"
PERIMETERX = b'<html><head><title>Access to this page has been denied</title></head><body><div id="px-captcha"></div></body></html>'
CLOUDFLARE = b"<html><head><title>Just a moment...</title></head><body></body></html>"
REAL = "<html><head><title>Where Scott Stands</title></head><body><p>In the Senate, Scott will:</p><form><div class='g-recaptcha'></div></form></body></html>".encode()


class BotCheck(unittest.TestCase):
    def test_flags_bot_check_pages(self):
        for page in (SITEGROUND, PERIMETERX, CLOUDFLARE):
            self.assertIsNotNone(archive_sources.bot_check(page))

    def test_flags_gzipped_bot_check_page(self):
        self.assertIsNotNone(archive_sources.bot_check(gzip.compress(SITEGROUND)))

    def test_passes_real_page_even_with_a_signup_captcha(self):
        self.assertIsNone(archive_sources.bot_check(REAL))
        self.assertIsNone(archive_sources.bot_check(gzip.compress(REAL)))


if __name__ == "__main__":
    unittest.main()
