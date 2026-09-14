from playwright.sync_api import Page, expect
from pages.base_page import BasePage
class CheckoutCompletePage(BasePage):
    URL = "https://www.saucedemo.com/checkout-complete.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.backhome_button = page.locator("[data-test='back-to-products']")
        self.generate_pdf_button = page.locator("[data-test='generate-pdf-order']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_checkout_complete_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.page.locator(".complete-header")).to_have_text("Thank you for your order!")

    def click_backhome_button(self):
        self.backhome_button.click()    

    def click_generate_pdf_button(self):
        self.generate_pdf_button.click()    