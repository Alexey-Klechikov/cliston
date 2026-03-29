from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


class BrowserSession:
    def __init__(self):
        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def get_page(self) -> Page:
        if self.page is None:
            self.pw = await async_playwright().start()
            # headless=False is helpful for debugging/watching Garm work
            self.browser = await self.pw.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
        return self.page

    async def close(self):
        if self.browser and self.pw:
            await self.browser.close()
            await self.pw.stop()
            self.page = None
