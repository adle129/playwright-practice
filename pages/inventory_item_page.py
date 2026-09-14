from playwright.sync_api import Page, expect
from pages.base_page import BasePage

class InventoryItemPage(BasePage):
    URL = "https://www.saucedemo.com/inventory-item.html?id="

    def __init__(self, page: Page, product_id: str):
        super().__init__(page)
        self.URL += product_id
        self.product_name = page.locator("[data-test='inventory-item-name']")
        self.product_desc = page.locator("[data-test='inventory-item-desc']")
        self.product_price = page.locator("[data-test='inventory-item-price']")
        self.shopping_cart_button = page.locator("[data-test='shopping-cart-link']")
        self.remove_button = page.locator("[data-test='remove']")
        self.back_to_products_button = page.locator("[data-test='back-to-products']")
        self.shopping_cart_badge = page.locator("[data-test='shopping-cart-badge']")

    def load(self):
        self.navigate_to(self.URL)

    def verify_inventory_item_page(self,product_name:str):
        expect(self.page).to_have_url(self.URL)
        expect(self.product_name).to_have_text(product_name)

    def remove_product_from_cart(self):
        self.remove_button.click()

    def add_product_to_cart(self):
        self.page.get_by_role("button",name="Add to cart").click()

    def click_cart_button(self):
        self.shopping_cart_button.click()

    def get_product_count_in_cart(self):
        cart_badge_count = self.shopping_cart_badge.inner_text()
        return int(cart_badge_count)

    def get_product_price(self):
        price_text = self.product_price.inner_text()
        return price_text

    def click_back_to_products_button(self):
        self.back_to_products_button.click()

    def get_product_description(self):
        return self.product_desc.inner_text()

    def verify_cart_badge_not_visible(self):
        expect(self.shopping_cart_badge).to_be_hidden()