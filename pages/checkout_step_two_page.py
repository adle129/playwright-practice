from playwright.sync_api import Page, expect
from pages.base_page import BasePage
class CheckoutStepTwoPage(BasePage):
    URL = "https://www.saucedemo.com/checkout-step-two.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.cart_items = page.locator("[data-test='inventory-item']")
        self.payment_info = page.locator("[data-test='payment-info-value']")
        self.shipping_info = page.locator("[data-test='shipping-info-value']")
        self.price_total = page.locator("[data-test='total-label']")
        self.price_tax = page.locator("[data-test='tax-label']")
        self.price_item_total = page.locator("[data-test='subtotal-label']")
        self.finish_button = page.locator("[data-test='finish']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_checkout_step_two_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.page.locator(".title")).to_have_text("Checkout: Overview")

    def get_cart_items_count(self):
        return self.cart_items.count()

    def get_payment_info(self):
        return self.payment_info.inner_text()

    def get_shipping_info(self):
        return self.shipping_info.inner_text()

    def get_price_total(self):
        return self.price_total.inner_text()

    def get_price_tax(self):
        return self.price_tax.inner_text()

    def get_price_item_total(self):
        return self.price_item_total.inner_text()

    def click_finish_button(self):
        self.finish_button.click()