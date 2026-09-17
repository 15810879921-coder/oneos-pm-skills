#!/usr/bin/env python3
"""Check the 10.2.3 installation UI without changing the user's clipboard."""
import argparse
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18761/#lifecycle-10-2-3")
    parser.add_argument("--screenshot")
    args = parser.parse_args()
    names = ("YunxiaoPM", "yunxiao-development-delivery", "development-brain", "YunxiaoQA", "yunxiao-release-operations")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 960})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.add_init_script("Object.defineProperty(navigator, 'clipboard', {value: {writeText: async text => { window.__testCopiedText = text; }}})")
        page.goto(args.url)
        page.wait_for_load_state("networkidle")
        section = page.locator("#lifecycle-10-2-3")
        assert section.is_visible()
        section.get_by_role("button", name="复制给 Codex 更新").click()
        copied = page.evaluate("window.__testCopiedText")
        assert "10.2.3" in copied and "-a cursor" not in copied
        commands = [line for line in copied.splitlines() if line.startswith("npx skills add ")]
        assert len(commands) == 5
        for name, command in zip(names, commands):
            assert f"--skill {name} -a codex -g -y" in command
        for name in names:
            card = page.locator(f'[data-copy="update-{name}"]')
            if card.count():
                card.click()
                command = page.evaluate("window.__testCopiedText")
                assert f"--skill {name} -a codex -g -y" in command
                assert "-a cursor" not in command
        assert not errors, errors
        page.locator("#lifecycle-10-2-3").scroll_into_view_if_needed()
        if args.screenshot:
            page.screenshot(path=args.screenshot, full_page=False)
        browser.close()
    print("Install page: 5 exact Codex-only update commands, copy callback and JS checks passed")


if __name__ == "__main__":
    main()
