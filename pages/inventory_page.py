from playwright.sync_api import Page, expect
from pages.base_page import BasePage

class InventoryPage(BasePage):
    URL = "https://www.saucedemo.com/inventory.html"

    def __init__(self, page: Page):
        super().__init__(page)

        self.product_items = page.locator("[data-test='inventory-item']")
        self.product_names = page.locator("[data-test='inventory-item-name']")
        self.product_descs = page.locator("[data-test='inventory-item-desc']")
        self.product_prices = page.locator("[data-test='inventory-item-price']")
        self.shopping_cart_badge = page.locator("[data-test='shopping-cart-badge']")
        self.shopping_cart_link = page.locator("[data-test='shopping-cart-link']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_inventory_page(self):
        expect(self.page).to_have_url(self.URL)
        expect(self.page.locator(".title")).to_have_text("Products")

    def add_product_to_cart(self, product_name: str):
        self.product_items.filter(has_text=product_name) \
            .get_by_role("button",name="Add to cart").click()

    def get_product_count_in_cart(self):
        cart_badge_count = self.shopping_cart_badge.inner_text()
        return int(cart_badge_count)

    def get_product_price(self, product_name: str):
        product_item = self.product_items.filter(has_text=product_name)
        price_text = product_item.locator("[data-test='inventory-item-price']").inner_text()
        return price_text

    def click_product_link(self, product_name: str):
        product_name = self.product_names.filter(has_text=product_name)
        product_name.click()

    def click_shopping_cart_link(self):
        self.shopping_cart_link.click()

    def get_product_count(self):
        return self.product_items.count()
