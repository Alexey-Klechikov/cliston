import logging

from services.playwright_browser.session import BrowserSession

_browser_session = BrowserSession()


async def close_browser():
    await _browser_session.close()


async def browser_inspect() -> str:
    logging.info("Inspecting the current page content")

    page = await _browser_session.get_page()
    # We extract text, but also 'aria-labels' so Garm knows what buttons do
    content = await page.evaluate(
        """() => {
        return document.body.innerText.substring(0, 5000);
    }""",
    )
    return f"Current Page Content: {content}"


async def browser_navigate(url: str | None) -> str:
    logging.info(f"Navigating to {url}")

    if not url:
        return "Error: URL is required."

    page = await _browser_session.get_page()
    await page.goto(url, wait_until="networkidle")

    # We return the new URL and title so Garm knows he moved
    return f"Successfully reached {page.url}. Page Title: {await page.title()}"


async def browser_interact(action: str | None, selector: str | None, value: str | None = None) -> str:
    logging.info(f"Performing action '{action}' on selector '{selector}' with value '{value}'")

    if not selector:
        return "Error: Selector is required for interaction."

    page = await _browser_session.get_page()
    try:
        if action == "click":
            await page.click(selector)
        elif action == "type":
            if not value:
                return "Error: 'type' action requires a 'value'."
            # Explicitly clear before typing to avoid appending to old text
            await page.click(selector, click_count=3)
            await page.keyboard.press("Backspace")
            await page.fill(selector, value)
        elif action == "keypress":
            if not value:
                return "Error: 'keypress' action requires a 'value' (e.g., 'Enter')."
            await page.focus(selector)
            await page.keyboard.press(value)
        else:
            return f"Error: Unrecognized action '{action}'. Supported actions are 'click', 'type', and 'keypress'."

        # Wait for potential redirects or AJAX
        try:
            await page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            await page.wait_for_load_state("load", timeout=2000)

        return f"Success: {action} on {selector}. Current URL: {page.url}"
    except Exception as e:
        return f"Error during {action}: {str(e)}"
