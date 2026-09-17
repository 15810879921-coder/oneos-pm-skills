#!/usr/bin/env python3
"""Default read-only official ListTestPlan transport; Content-Type is fixed to JSON."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import yunxiao_cli_runtime as core

PAGE_SIZE = 100
MAX_PAGES = 100


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward the PAT to a redirect target.
        return None


def endpoint() -> str:
    # Only the central public API has been verified. Never guess a Region endpoint
    # or send an existing credential to an arbitrary configured host.
    configured = os.environ.get("ALIBABA_CLOUD_YUNXIAO_API_BASE_URL", "").strip()
    if configured and configured.rstrip("/") != "https://openapi-rdc.aliyuncs.com":
        raise core.AdapterError("JSON计划读取尚未验证当前Region/API_BASE_URL，禁止改用其他组织端点。")
    organization = os.environ.get("ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID", "").strip()
    if not organization:
        raise core.AdapterError("JSON计划读取缺少organizationId。")
    return ("https://openapi-rdc.aliyuncs.com/oapi/v1/projex/organizations/"
            + urllib.parse.quote(organization, safe="") + "/testPlan/list")


def list_plans_json(project_id: str) -> list[dict[str, Any]]:
    token = os.environ.get("ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN", "")
    if not token:
        raise core.AdapterError("JSON计划读取缺少访问令牌。")
    if not project_id or not project_id.strip():
        raise core.AdapterError("JSON计划读取缺少projectIdentifier。")
    url = endpoint()
    opener = urllib.request.build_opener(NoRedirect())
    plans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for page in range(1, MAX_PAGES + 1):
        query = urllib.parse.urlencode({"projectIdentifier": project_id,
                                      "page": page, "perPage": PAGE_SIZE})
        request = urllib.request.Request(
            url + "?" + query, data=b"{}", method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json",
                     "x-yunxiao-token": token},
        )
        try:
            with opener.open(request, timeout=60) as response:
                if response.status != 200:
                    raise core.AdapterError(f"JSON计划读取 StatusCode: {response.status}")
                payload = response.read()
        except urllib.error.HTTPError as error:
            detail = core.scrub(error.read(4096).decode("utf-8", errors="replace"))
            raise core.AdapterError(f"JSON计划读取 StatusCode: {error.code} {detail}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise core.AdapterError("JSON计划读取 connection error: " + core.scrub(str(error))) from None
        try:
            batch = json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            raise core.AdapterError("JSON计划读取响应不是有效JSON，不能推断无计划。") from None
        if not isinstance(batch, list):
            raise core.AdapterError("JSON计划读取响应必须是计划数组，不能推断无计划。")
        for item in batch:
            if not isinstance(item, dict) or not isinstance(item.get("testPlanIdentifier"), str) \
                    or not item["testPlanIdentifier"].strip():
                raise core.AdapterError("JSON计划读取返回无效计划标识。")
            if item.get("spaceIdentifier") != project_id:
                raise core.AdapterError("JSON计划读取返回项目不一致或缺少项目标识。")
            identifier = item["testPlanIdentifier"]
            if identifier in seen:
                raise core.AdapterError("JSON计划读取分页重复，不能证明已完整读取。")
            seen.add(identifier)
            plans.append(item)
        if len(batch) < PAGE_SIZE:
            return plans
    raise core.AdapterError("JSON计划读取超过分页上限，不能证明已完整读取。")
