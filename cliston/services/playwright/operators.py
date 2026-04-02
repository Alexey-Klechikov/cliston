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

    structured_snapshot = await page.evaluate(
        """
        () => {
            const viewport = { width: window.innerWidth, height: window.innerHeight };

            const compactText = (value) => (value || '').replace(/\\s+/g, ' ').trim();

            const isVisible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
                    return false;
                }

                const rect = el.getBoundingClientRect();
                return (
                    rect.width > 0 &&
                    rect.height > 0 &&
                    rect.bottom >= 0 &&
                    rect.right >= 0 &&
                    rect.top <= viewport.height &&
                    rect.left <= viewport.width
                );
            };

            const unique = (items) => Array.from(new Set(items));

            const noiseTerms = new Set([
                'logga in', 'bli kund', 'kundservice', 'nyheter', 'spara & investera', 'pension',
                'bolan', 'borsen idag', 'visa som tabell', 'end of interactive chart',
                'created with highcharts', 'investeringar innebar en risk', 'courtage & rakneexempel',
                'oversikt', 'analys', 'nyheter & forum', 'jamfor', 'installningar',
            ]);

            const normalizeAscii = (value) =>
                compactText(value)
                    .toLowerCase()
                    .replace(/å/g, 'a')
                    .replace(/ä/g, 'a')
                    .replace(/ö/g, 'o');

            const isNoiseText = (text) => {
                const normalized = normalizeAscii(text);
                return !normalized || noiseTerms.has(normalized);
            };

            const numberPattern = /[+\\-−]?\\d{1,3}(?:[ \\u00A0]?\\d{3})*(?:,\\d{1,4})?/g;
            const hasNumericSignal = (text) => numberPattern.test(text);
            const hasFinanceSignal = (text) =>
                /(sek|usd|eur|nok|dkk|pe-tal|p\\/e|direktavkastning|borsvarde|vinst\\/aktie|volatilitet|rapport|isin|beta|omsattning)/i.test(text);
            const hasSignal = (text) => hasNumericSignal(text) || hasFinanceSignal(text);

            const suggestedSelector = (el) => {
                const classValue = typeof el.className === 'string' ? el.className : '';
                const firstClass = classValue.split(' ').filter(Boolean)[0] || '';
                return (
                    el.id ? `#${el.id}` :
                    (el.getAttribute('name') ? `[name="${el.getAttribute('name')}"]` :
                    (el.getAttribute('aria-label') ? `[aria-label="${el.getAttribute('aria-label')}"]` :
                    (el.getAttribute('placeholder') ? `[placeholder="${el.getAttribute('placeholder')}"]` :
                    (firstClass ? `${el.tagName.toLowerCase()}.${firstClass}` : el.tagName.toLowerCase()))))
                );
            };

            const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4'))
                .filter(isVisible)
                .map((el) => compactText(el.textContent))
                .filter((text) => text.length >= 2 && text.length <= 120)
                .filter((text) => !isNoiseText(text))
                .slice(0, 40);

            const leafTexts = Array.from(
                document.querySelectorAll('h1, h2, h3, h4, p, li, td, th, span, strong, label, button, a'),
            )
                .filter(isVisible)
                .filter((el) => el.children.length === 0)
                .map((el) => compactText(el.textContent))
                .filter((text) => text.length >= 2 && text.length <= 140)
                .filter((text) => !isNoiseText(text))
                .filter((text, i, arr) => arr.indexOf(text) === i)
                .slice(0, 500);

            const signalText = leafTexts
                .filter((text) => hasSignal(text))
                .slice(0, 180);

            const contextText = leafTexts
                .filter((text) => !hasSignal(text))
                .filter((text) => text.length >= 8 && text.length <= 90)
                .slice(0, 90);

            const links = Array.from(document.querySelectorAll('a[href]'))
                .filter(isVisible)
                .map((el) => ({
                    text: compactText(el.textContent),
                    href: el.getAttribute('href') || '',
                    selector: suggestedSelector(el),
                }))
                .filter((link) => link.text && !isNoiseText(link.text))
                .slice(0, 40);

            const buttons = Array.from(
                document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]'),
            )
                .filter(isVisible)
                .map((el) => ({
                    text: compactText(el.innerText || el.getAttribute('value') || el.getAttribute('aria-label')),
                    selector: suggestedSelector(el),
                    disabled: !!el.disabled,
                }))
                .filter((button) => button.text && !isNoiseText(button.text))
                .slice(0, 50);

            const formFields = Array.from(document.querySelectorAll('input, textarea, select'))
                .filter(isVisible)
                .map((el) => ({
                    tag: el.tagName.toLowerCase(),
                    type: (el.getAttribute('type') || '').toLowerCase(),
                    name: el.getAttribute('name') || '',
                    id: el.id || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    aria_label: el.getAttribute('aria-label') || '',
                    value: compactText(el.value || ''),
                    selector: suggestedSelector(el),
                }))
                .filter((field) => field.placeholder || field.name || field.id || field.value)
                .slice(0, 70);

            const tables = Array.from(document.querySelectorAll('table'))
                .filter(isVisible)
                .slice(0, 6)
                .map((table) => {
                    const headers = Array.from(table.querySelectorAll('th'))
                        .map((el) => compactText(el.textContent))
                        .filter(Boolean)
                        .slice(0, 10);

                    const rows = Array.from(table.querySelectorAll('tr'))
                        .slice(0, 8)
                        .map((row) =>
                            Array.from(row.querySelectorAll('td, th'))
                                .map((cell) => compactText(cell.textContent))
                                .filter((text) => text.length > 0 && text.length <= 100)
                                .slice(0, 10),
                        )
                        .filter((row) => row.length > 0);

                    return { headers, rows };
                })
                .filter((table) => table.headers.length > 0 || table.rows.length > 0);

            const lists = Array.from(document.querySelectorAll('ul, ol'))
                .filter(isVisible)
                .slice(0, 8)
                .map((list) =>
                    Array.from(list.querySelectorAll(':scope > li'))
                        .map((li) => compactText(li.textContent))
                        .filter((text) => text.length > 0 && text.length <= 80)
                        .slice(0, 8),
                )
                .filter((items) => items.length > 0);

            const dtPairs = Array.from(document.querySelectorAll('dt'))
                .filter(isVisible)
                .map((dt) => {
                    const dd = dt.nextElementSibling && dt.nextElementSibling.tagName.toLowerCase() === 'dd'
                        ? dt.nextElementSibling
                        : null;
                    return {
                        label: compactText(dt.textContent),
                        value: compactText(dd ? dd.textContent : ''),
                    };
                })
                .filter((pair) => pair.label && pair.value && hasSignal(pair.value))
                .slice(0, 60);

            const inlinePairs = Array.from(
                document.querySelectorAll('tr, .row, [class*="row"], [class*="item"], [class*="stat"]'),
            )
                .filter(isVisible)
                .slice(0, 140)
                .map((el) => {
                    const chunks = unique(
                        Array.from(el.querySelectorAll('td, th, span, strong, label, div'))
                            .filter(isVisible)
                            .map((n) => compactText(n.textContent))
                            .filter((text) => text.length > 0 && text.length <= 80),
                    );

                    if (chunks.length < 2) return null;
                    return { label: chunks[0], value: chunks[1] };
                })
                .filter(Boolean)
                .filter((pair) => pair.label && pair.value && hasSignal(pair.value))
                .slice(0, 80);

            const keyValueCandidates = [...dtPairs, ...inlinePairs]
                .filter((pair) => pair.label && pair.value)
                .slice(0, 120);

            const numericCandidates = unique(
                [...signalText, ...keyValueCandidates.map((pair) => pair.value)]
                    .flatMap((text) => text.match(numberPattern) || [])
                    .map((value) => value.replace(/\\s+/g, ''))
                    .filter((value) => value.length >= 2),
            ).slice(0, 80);

            const interactiveElements = Array.from(
                document.querySelectorAll('button, input, a, select, [role="button"]'),
            )
                .filter(isVisible)
                .map((el) => ({
                    tag: el.tagName,
                    text: compactText(el.innerText || el.placeholder || el.ariaLabel),
                    id: el.id,
                    class: typeof el.className === 'string' ? el.className : '',
                    type: el.type,
                    suggested_selector: suggestedSelector(el),
                }))
                .filter((el) => (el.text && !isNoiseText(el.text)) || el.tag === 'INPUT' || el.tag === 'SELECT')
                .slice(0, 80);

            const payload = {
                url: location.href,
                title: document.title,
                headings,
                signal_text: signalText,
                context_text: contextText,
                numeric_candidates: numericCandidates,
                key_value_candidates: keyValueCandidates,
                links,
                buttons,
                form_fields: formFields,
                tables,
                lists,
                interactive_elements: interactiveElements,
            };

            const maxChars = 18000;
            let serialized = JSON.stringify(payload);

            if (serialized.length > maxChars) {
                payload.context_text = payload.context_text.slice(0, 40);
                payload.links = payload.links.slice(0, 20);
                payload.buttons = payload.buttons.slice(0, 24);
                payload.lists = payload.lists.slice(0, 4);
                serialized = JSON.stringify(payload);
            }

            if (serialized.length > maxChars) {
                payload.tables = payload.tables.slice(0, 2);
                payload.signal_text = payload.signal_text.slice(0, 80);
                payload.key_value_candidates = payload.key_value_candidates.slice(0, 60);
                payload.interactive_elements = payload.interactive_elements.slice(0, 50);
                serialized = JSON.stringify(payload);
            }

            return serialized;
        }
        """,
    )

    return (
        screenshot_bytes,
        f"Visible Frontend Snapshot: {structured_snapshot}",
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
