"""Test if the /console route resolves correctly in the Vue app."""

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    console_errors = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )

    # Navigate to the app and try the /console route directly
    page.goto("http://localhost:5174/console")
    page.wait_for_load_state("networkidle")

    print(f"Page title: {page.title()}")
    print(f"Current URL: {page.url}")

    # Check if we got redirected (404 catch-all)
    if "404" in page.url or "404" in page.content():
        print("RESULT: Route /console leads to 404 page")
    else:
        print("RESULT: Route /console loaded successfully")

    if console_errors:
        print(f"\nConsole errors ({len(console_errors)}):")
        for err in console_errors:
            print(f"  {err}")

    page.screenshot(path="/tmp/console_route.png", full_page=True)
    browser.close()
