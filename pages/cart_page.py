from playwright.sync_api import Page, expect
from pages.base_page import BasePage

class CartPage(BasePage):
    URL = "https://www.saucedemo.com/cart.html"

    def __init__(self, page: Page):
        super().__init__(page)
        self.cart_items = page.locator("[data-test='inventory-item']")
        self.cart_item_names = page.locator("[data-test='inventory-item-name']")
        self.cart_item_descs = page.locator("[data-test='inventory-item-desc']")
        self.cart_item_prices = page.locator("[data-test='inventory-item-price']")
        self.cart_item_quantity = page.locator("[data-test='item-quantity']")
        self.checkout_button = page.locator("[data-test='checkout']")
        self.continue_shopping_button = page.locator("[data-test='continue-shopping']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_cart_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.page.locator(".title")).to_have_text("Your Cart")

    def remove_product_from_cart(self, product_name: str):
        cart_item = self.cart_items.filter(has_text=product_name)
        cart_item.get_by_role("button", name="Remove").click()

    def get_items_count(self):
        count = self.cart_items.count()
        return count

    def get_item_names(self) -> list[str]:
        return self.cart_item_names.all_inner_texts()

    def click_checkout_button(self):
        self.checkout_button.click()

    def click_continue_shopping_button(self):
        self.continue_shopping_button.click()

    def get_item_descs(self):
        return self.cart_item_descs.all_inner_texts()

