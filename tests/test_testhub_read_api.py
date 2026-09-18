from __future__ import annotations
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).parents[1] / "skills/yunxiao-development-delivery/scripts"))
import yunxiao_testhub_read_api as api


class Response(io.BytesIO):
    status = 200


class TestHubJsonReadTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN": "private-test-token",
            "ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID": "ORG",
            "ALIBABA_CLOUD_YUNXIAO_API_BASE_URL": "",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_read(self, *pages):
        opener = Mock()
        opener.open.side_effect = [Response(json.dumps(page).encode()) for page in pages]
        with patch.object(api.urllib.request, "build_opener", return_value=opener):
            result = api.list_plans_json("PROJECT")
        return result, opener

    def test_request_uses_json_official_endpoint_and_exact_project(self):
        result, opener = self.run_read([{"testPlanIdentifier": "P1", "spaceIdentifier": "PROJECT"}])
        request = opener.open.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.data, b"{}")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("X-yunxiao-token"), "private-test-token")
        self.assertEqual(request.full_url, "https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/ORG/testPlan/list?projectIdentifier=PROJECT&page=1&perPage=100")
        self.assertEqual(len(result), 1)

    def test_pagination_does_not_trust_misleading_next_page_header(self):
        with patch.object(api, "PAGE_SIZE", 1):
            result, opener = self.run_read(
                [{"testPlanIdentifier": "P1", "spaceIdentifier": "PROJECT"}],
                [{"testPlanIdentifier": "P2", "spaceIdentifier": "PROJECT"}], [])
        self.assertEqual(len(result), 2)
        self.assertEqual(opener.open.call_count, 3)

    def test_invalid_payload_or_foreign_project_is_not_empty_plan(self):
        for payload in ({}, {"errorMessage": "error"}, [None], [{}],
                        [{"testPlanIdentifier": "P1", "spaceIdentifier": "OTHER"}]):
            with self.subTest(payload=payload), self.assertRaises(api.core.AdapterError):
                self.run_read(payload)

    def test_repeated_page_and_truncated_inventory_fail(self):
        page = [{"testPlanIdentifier": "P1", "spaceIdentifier": "PROJECT"}]
        with patch.object(api, "PAGE_SIZE", 1):
            with self.assertRaisesRegex(api.core.AdapterError, "重复"):
                self.run_read(page, page)
            with patch.object(api, "MAX_PAGES", 1):
                with self.assertRaisesRegex(api.core.AdapterError, "上限"):
                    self.run_read(page)

    def test_arbitrary_endpoint_blocked_before_any_network(self):
        with patch.dict(os.environ, {"ALIBABA_CLOUD_YUNXIAO_API_BASE_URL": "https://other.invalid"}):
            with patch.object(api.urllib.request, "build_opener") as opener:
                with self.assertRaises(api.core.AdapterError):
                    api.list_plans_json("PROJECT")
                opener.assert_not_called()

    def test_redirects_are_not_followed(self):
        self.assertIsNone(api.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid"))

    def test_http_errors_keep_code_and_scrub_secret(self):
        error = urllib.error.HTTPError("https://openapi-rdc.aliyuncs.com", 403, "Forbidden", {}, io.BytesIO(b"private-test-token"))
        opener = Mock()
        opener.open.side_effect = error
        with patch.object(api.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(api.core.AdapterError) as raised:
                api.list_plans_json("PROJECT")
        self.assertIn("403", str(raised.exception))
        self.assertNotIn("private-test-token", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
