from playwright.sync_api import Page, expect
from pages.inventory_page import InventoryPage
from pages.inventory_item_page import InventoryItemPage
import pytest

PRODUCT = "Sauce Labs Backpack"
PRICE = "$29.99"

@pytest.mark.parametrize("product,price", [
    ("Sauce Labs Backpack", "$29.99"),
    ("Sauce Labs Bike Light", "$9.99"),
    ("Sauce Labs Bolt T-Shirt", "$15.99")
])

@pytest.mark.smoke
def test_product_price_shown_on_inventory_page(inventory_page: InventoryPage, product: str, price: str):
    product_price = inventory_page.get_product_price(product)
    assert product_price == price, f"Product price is not correct, EXPECTED:{price},RECEIVED:{product_price}"


@pytest.mark.regression
def test_add_product_to_cart(inventory_page: InventoryPage):
    inventory_page.add_product_to_cart(PRODUCT)
    count = inventory_page.get_product_count_in_cart()
    assert count == 1, f"The item count in cart is not correct，EXPECTED:1,RECEIVED:{count}"

@pytest.mark.regression
def test_product_detail_page_link(inventory_page: InventoryPage):
    inventory_page.click_product_link(PRODUCT)
    inventory_item = InventoryItemPage(inventory_page.page, product_id="4")
    inventory_item.verify_inventory_item_page(PRODUCT)

@pytest.mark.regression
def test_total_production_items_count(inventory_page:InventoryPage):
    count = inventory_page.get_product_count()
    assert count == 6, f"The total count of products shown in page is not correct, EXPECTED:6, RECEIVED:{count}"