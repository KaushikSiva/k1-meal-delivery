"""Software tests only; synthetic responses are not robot evidence."""

import io
import json
import unittest
from unittest.mock import patch

from tools.you_search import NoRedirect, search


class SearchClientTests(unittest.TestCase):
    def test_secret_only_in_auth_header_and_echo_redacted(self):
        fake_key = "test-credential-not-a-real-key"
        class Opener:
            def open(inner, request, timeout):
                self.assertEqual(request.full_url, "https://ydc-index.io/v1/search")
                self.assertEqual(request.method, "POST")
                self.assertEqual(request.get_header("X-api-key"), fake_key)
                self.assertNotIn(fake_key, request.data.decode())
                body = json.loads(request.data)
                self.assertEqual(body["include_domains"], ["docs.booster.tech"])
                self.assertEqual(timeout, 45)
                return io.BytesIO(json.dumps({"results": {"web": [
                    {"title": fake_key, "url": "https://example.invalid", "snippets": []}
                ]}}).encode())
        with patch("tools.you_search.read_key", return_value=fake_key), patch(
            "tools.you_search.build_opener", return_value=Opener()
        ):
            result = search("K1", 3, ["docs.booster.tech"])
        self.assertNotIn(fake_key, json.dumps(result))
        self.assertEqual(result["results"][0]["title"], "[REDACTED]")
        self.assertEqual(result["evidence_kind"], "web_search_leads_not_physical_measurements")

    def test_redirect_is_not_followed_with_credential(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid"))

    def test_bad_results_are_rejected(self):
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b'{"results":{"web":"invalid"}}')
        with patch("tools.you_search.read_key", return_value="dummy"), patch(
            "tools.you_search.build_opener", return_value=Opener()
        ):
            with self.assertRaises(ValueError):
                search("K1")


if __name__ == "__main__":
    unittest.main()
