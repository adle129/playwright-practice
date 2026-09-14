from playwright.sync_api import Page, expect
from pages.base_page import BasePage
class CheckoutStepOnePage(BasePage):
    URL = "https://www.saucedemo.com/checkout-step-one.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.first_name_input = page.locator("[data-test='firstName']")
        self.last_name_input = page.locator("[data-test='lastName']")
        self.postal_code_input = page.locator("[data-test='postalCode']")
        self.continue_button = page.locator("[data-test='continue']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_checkout_step_one_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.page.locator(".title")).to_have_text("Checkout: Your Information")

    def fill_checkout_information(self, first_name: str, last_name: str, postal_code: str):
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.postal_code_input.fill(postal_code)

    def click_continue_button(self):
        self.continue_button.click()