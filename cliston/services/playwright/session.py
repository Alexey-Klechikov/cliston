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
            self.browser = await self.pw.firefox.launch(headless=False)

            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720},
            )
            self.page = await self.context.new_page()
        return self.page

    async def close(self):
        if self.browser and self.pw:
            await self.browser.close()
            await self.pw.stop()
            self.page = None
