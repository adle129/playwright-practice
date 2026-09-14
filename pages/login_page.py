from playwright.sync_api import Page, expect
from pages.base_page import BasePage

class LoginPage(BasePage):
    URL = "https://www.saucedemo.com/"

    def __init__(self, page: Page):
        super().__init__(page)
        self.username_input = page.locator("input[id='user-name']")
        self.password_input = page.locator("input[id='password']")
        self.login_button = page.locator("[data-test='login-button']")


    def load(self):
        self.navigate_to(self.URL)

    def login(self,username:str,password:str):
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.login_button.click()

    def verify_login_page(self):
        expect(self.page).to_have_title("Swag Labs")
