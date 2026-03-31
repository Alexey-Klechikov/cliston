import logging

from services.playwright_browser.session import BrowserSession

_browser_session = BrowserSession()


async def close_browser():
    await _browser_session.close()


async def browser_inspect() -> tuple[bytes, str]:
    """
    Captures tactical telemetry: A compressed screenshot for vision
    and a filtered list of interactive elements for precise data extraction.
    """
    logging.info("Garm: Executing visual and textual reconnaissance.")

    page = await _browser_session.get_page()

    # Capture Vision (Screenshot)
    screenshot_bytes = await page.screenshot(type="jpeg", quality=50, full_page=False)

    # Capture Interactive Elements (Filtered DOM)
    interactive_elements = await page.evaluate(
        """
        () => {
            const elements = Array.from(document.querySelectorAll('button, input, a, select, [role="button"]'))
                .map(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        return {
                            tag: el.tagName,
                            text: el.innerText || el.placeholder || el.ariaLabel,
                            id: el.id,
                            class: el.className,
                            type: el.type
                        };
                    }
                }).filter(Boolean);
            return JSON.stringify(elements);
        }
        """,
    )

    return (
        screenshot_bytes,
        f"Interactive DOM Elements: {interactive_elements}",
    )


async def browser_navigate(url: str | None) -> str:
    logging.info(f"Navigating to {url}")

    if not url:
        return "Error: URL is required for infiltration."

    page = await _browser_session.get_page()

    try:
        await page.goto(url, wait_until="networkidle", timeout=10000)
    except Exception as e1:
        logging.warning(f"Networkidle failed for {url}, attempting soft load...")
        try:
            await page.wait_for_load_state("load", timeout=5000)
        except Exception as e2:
            return f"Infiltration Failure: {url} is unresponsive or protected. {str(e1)} | {str(e2)}"

    obstructions = [
        "button:has-text('Accepter')",
        "button:has-text('Godkänn')",
        "button:has-text('Accept')",
        "#cookie-accept",
        ".modal-close",
        "button:has-text('Accept All')",
        "#popup-close",
        ".newsletter-modal .close",
    ]
    for selector in obstructions:
        try:
            if await page.is_visible(selector, timeout=1000):
                await page.click(selector)
                logging.info(f"Neutralized obstruction: {selector}")
        except Exception:
            continue

    current_url = page.url
    page_title = await page.title()

    return (
        f"Infiltration Successful. Currently at: {current_url}. " f"Title: {page_title}. UI is clear for interaction."
    )


async def browser_interact(action: str | None, selector: str | None, value: str | None = None) -> str:
    logging.info(f"Performing action '{action}' on selector '{selector}' with value '{value}'")

    if not selector:
        return "Error: Selector is required for interaction."

    page = await _browser_session.get_page()
    try:
        # TACTICAL WAIT: Ensure the element is present and visible
        # We catch the timeout specifically to give Garm better 'Eyes'
        try:
            await page.wait_for_selector(selector, state="visible", timeout=5000)
        except Exception:
            return (
                f"Tactical Failure: Selector '{selector}' is not visible or not in the DOM. "
                "It may be hidden behind a button (like a search icon) or a menu. "
                "Use 'browser_inspect' to find the trigger element and click it first."
            )

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

        # 2. POST-ACTION STABILIZATION
        try:
            await page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=2000)

        return f"Success: {action} on {selector}. Current URL: {page.url}"

    except Exception as e:
        logging.error(f"Error during {action} on {selector}: {str(e)}")
        return f"Infrastructure Error during {action}: {str(e)}"
