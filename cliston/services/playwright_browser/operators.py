import logging

from services.playwright_browser.session import BrowserSession

_browser_session = BrowserSession()


async def close_browser():
    await _browser_session.close()


async def browser_inspect() -> str:
    logging.info("Inspecting the current page content")

    page = await _browser_session.get_page()
    # Extract both innerText and innerHTML for better debugging
    content_text = await page.evaluate(
        """() => {
        return document.body.innerText.substring(0, 5000);
    }""",
    )
    content_html = await page.evaluate(
        """() => {
        return document.body.innerHTML.substring(0, 5000);
    }""",
    )

    # # Optionally capture a screenshot for visual debugging
    # screenshot_path = "page_screenshot.png"
    # await page.screenshot(path=screenshot_path)

    return f"Current Page Content (Text): {content_text}\nCurrent Page Content (HTML): {content_html}"


async def browser_navigate(url: str | None) -> str:
    logging.info(f"Navigating to {url}")

    if not url:
        return "Error: URL is required."

    page = await _browser_session.get_page()
    try:
        # Set a shorter timeout for navigation
        await page.goto(url, wait_until="domcontentloaded", timeout=8000)
    except Exception as e:
        return f"Error: Navigation to {url} failed due to timeout or other issue: {str(e)}"

    # We return the new URL and title so Garm knows he moved
    return f"Successfully reached {page.url}. Page Title: {await page.title()}"


async def browser_interact(action: str | None, selector: str | None, value: str | None = None) -> str:
    logging.info(f"Performing action '{action}' on selector '{selector}' with value '{value}'")

    if not selector:
        return "Error: Selector is required for interaction."

    page = await _browser_session.get_page()
    try:
        # Wait for the selector to be visible before interacting
        await page.wait_for_selector(selector, timeout=5000)

        if action == "click":
            await page.click(selector, timeout=3000)
        elif action == "type":
            if not value:
                return "Error: 'type' action requires a 'value'."
            # Explicitly clear before typing to avoid appending to old text
            await page.click(selector, click_count=3, timeout=3000)
            await page.keyboard.press("Backspace")
            await page.fill(selector, value, timeout=3000)
        elif action == "keypress":
            if not value:
                return "Error: 'keypress' action requires a 'value' (e.g., 'Enter')."
            await page.focus(selector, timeout=3000)
            await page.keyboard.press(value)
        else:
            return f"Error: Unrecognized action '{action}'. Supported actions are 'click', 'type', and 'keypress'."

        # Wait for potential redirects or AJAX
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass

        return f"Success: {action} on {selector}. Current URL: {page.url}"
    except Exception as e:
        return f"Error during {action}: {str(e)}"
