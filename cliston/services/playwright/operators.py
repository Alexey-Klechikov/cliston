import logging

from services.playwright.session import BrowserSession

_browser_session = BrowserSession()


def _selector_candidates(selector: str) -> list[str]:
    raw = selector.strip()
    candidates = [raw]

    # If selector looks like a plain token (e.g. search-input), try common DOM mappings.
    if not any(char in raw for char in ["#", ".", "[", "]", " ", ":", "=", '"', "'"]):
        candidates.extend(
            [
                f"#{raw}",
                f"[name='{raw}']",
                f"[data-testid='{raw}']",
                f"[aria-label='{raw}']",
                f"[placeholder='{raw}']",
                f"text={raw}",
            ],
        )

    # Deduplicate while preserving order.
    return list(dict.fromkeys(candidates))


async def _find_first_visible_selector(page, selector: str, timeout_per_selector_ms: int = 1000) -> str | None:
    for candidate in _selector_candidates(selector):
        try:
            await page.wait_for_selector(candidate, state="visible", timeout=timeout_per_selector_ms)
            return candidate
        except Exception:
            continue

    return None


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
                        const classValue = typeof el.className === 'string' ? el.className : '';
                        const firstClass = classValue.split(' ').filter(Boolean)[0] || '';
                        const suggestedSelector =
                            el.id ? `#${el.id}` :
                            (el.getAttribute('name') ? `[name="${el.getAttribute('name')}"]` :
                            (el.getAttribute('aria-label') ? `[aria-label="${el.getAttribute('aria-label')}"]` :
                            (el.getAttribute('placeholder') ? `[placeholder="${el.getAttribute('placeholder')}"]` :
                            (firstClass ? `${el.tagName.toLowerCase()}.${firstClass}` : el.tagName.toLowerCase()))));

                        return {
                            tag: el.tagName,
                            text: el.innerText || el.placeholder || el.ariaLabel,
                            id: el.id,
                            class: el.className,
                            type: el.type,
                            suggested_selector: suggestedSelector
                        };
                    }
                }).filter(Boolean);

            // Keep payload compact so the model can reason over it reliably.
            return JSON.stringify(elements.slice(0, 120));
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
        f"Infiltration Successful. Currently at: {current_url}. Title: {page_title}. "
        "Next action: call browser_inspect, then interact using a selector from inspect output."
    )


async def browser_interact(action: str | None, selector: str | None, value: str | None = None) -> str:
    logging.info(f"Performing action '{action}' on selector '{selector}' with value '{value}'")

    if not selector:
        return "Error: Selector is required for interaction."

    page = await _browser_session.get_page()
    try:
        resolved_selector = await _find_first_visible_selector(page, selector, timeout_per_selector_ms=1200)
        if not resolved_selector:
            tried = ", ".join(_selector_candidates(selector))
            return (
                f"Tactical Failure: Selector '{selector}' is not visible or not in the DOM. "
                f"Tried: {tried}. "
                "It may be hidden behind a button (like a search icon) or a menu. "
                "Use 'browser_inspect' to find the trigger element and click it first."
            )

        if action == "click":
            await page.click(resolved_selector, timeout=3000)
        elif action == "type":
            if not value:
                return "Error: 'type' action requires a 'value'."
            # Explicitly clear before typing to avoid appending to old text
            await page.click(resolved_selector, click_count=3, timeout=3000)
            await page.keyboard.press("Backspace")
            await page.fill(resolved_selector, value, timeout=3000)
        elif action == "keypress":
            if not value:
                return "Error: 'keypress' action requires a 'value' (e.g., 'Enter')."
            await page.focus(resolved_selector, timeout=3000)
            await page.keyboard.press(value)
        else:
            return f"Error: Unrecognized action '{action}'. Supported actions are 'click', 'type', and 'keypress'."

        try:
            await page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            await page.wait_for_load_state("domcontentloaded", timeout=2000)

        return f"Success: {action} on {resolved_selector}. Current URL: {page.url}"

    except Exception as e:
        return f"Infrastructure Error during {action}: {str(e)}"
