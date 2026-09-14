from playwright.sync_api import Page, expect

class BasePage:
    def __init__(self, page:Page):
        self.page = page

    def navigate_to(self, url:str):
        self.page.goto(url=url)

    def verify_url(self,url_pattern:str):
        expect(self.page).to_have_url(url=url_pattern)