from playwright.sync_api import Page, expect
from pages.inventory_page import InventoryPage
from pages.cart_page import CartPage
from pages.checkout_step_one_page import CheckoutStepOnePage
import pytest

PRODUCT = "Sauce Labs Backpack"
PRICE = "$29.99"


@pytest.fixture
def cart_page(inventory_page:InventoryPage):
    inventory_page.click_shopping_cart_link()
    page = CartPage(inventory_page.page)
    page.verify_cart_page()
    return page

@pytest.fixture
def cart_page_with_product(inventory_page:InventoryPage):
    inventory_page.add_product_to_cart(PRODUCT)
    inventory_page.click_shopping_cart_link()
    page = CartPage(inventory_page.page)
    page.verify_cart_page()
    return page

@pytest.mark.regression
def test_continue_shopping(cart_page:CartPage,inventory_page:InventoryPage):
    cart_page.click_continue_shopping_button()
    inventory_page.verify_inventory_page()


@pytest.mark.regression
def test_checkout(cart_page:CartPage):
    cart_page.click_checkout_button()
    checkout_page = CheckoutStepOnePage(cart_page.page)
    checkout_page.verify_checkout_step_one_page()

@pytest.mark.regression
def test_remove_product_from_cart(cart_page_with_product:CartPage):
    cart_page_with_product.remove_product_from_cart(PRODUCT)
    count = cart_page_with_product.get_items_count()
    assert count == 0, f"There should no item shown if remove all the prod"

@pytest.mark.regression
def test_product_name_shown(cart_page_with_product:CartPage):
    names = cart_page_with_product.get_item_names()
    expect_name = ['Sauce Labs Backpack']
    assert names == expect_name, f"The product name shown in cart page is not correct, EXPECTED:{expect_name} RECEIVED: {names}"

@pytest.mark.regression
def test_product_description_shown(cart_page_with_product:CartPage):
    descs = cart_page_with_product.get_item_descs()
    expect_desc = ['carry.allTheThings() with the sleek, streamlined Sly Pack that melds uncompromising style with unequaled laptop and tablet protection.']
    assert descs == expect_desc, f"The product description shown in cart page is not correct, EXPECTED:{expect_desc} RECEIVED: {descs}"
