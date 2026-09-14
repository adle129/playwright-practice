from playwright.sync_api import Page, expect
from pages.inventory_item_page import InventoryItemPage
from pages.inventory_page import InventoryPage
from pages.cart_page import CartPage
import pytest

PRODUCT = "Sauce Labs Backpack"
PRICE = "$29.99"

@pytest.fixture
def product_detail_page(inventory_page: InventoryPage)-> InventoryItemPage:
    inventory_page.click_product_link(PRODUCT)
    detail = InventoryItemPage(inventory_page.page, product_id="4")
    detail.verify_inventory_item_page(PRODUCT)
    return detail


@pytest.mark.regression
def test_product_detail_page_shows_price(product_detail_page: InventoryItemPage):
    price = product_detail_page.get_product_price()
    assert price == PRICE, f"Price of the product is not correct，EXPECTED:{PRICE},RECEIVED:{price}"

@pytest.mark.regression
def test_add_product_to_cart_from_detail_page(product_detail_page: InventoryItemPage):
    product_detail_page.add_product_to_cart()
    count = product_detail_page.get_product_count_in_cart()
    assert count == 1, f"Number in Cart is not correct,EXPECTED:1, RECEIVED:{count}"

@pytest.mark.regression
def test_remove_product_from_cart_from_detail_page(product_detail_page: InventoryItemPage):
    product_detail_page.add_product_to_cart()
    product_detail_page.remove_product_from_cart()
    expect(product_detail_page.shopping_cart_badge).to_be_hidden()

@pytest.mark.regression
def test_click_cart_button_redirects_to_cart_page(product_detail_page: InventoryItemPage):
    product_detail_page.click_cart_button()
    cart = CartPage(product_detail_page.page)
    cart.verify_cart_page()


@pytest.mark.regression
def test_click_back_to_products_button_redirects_to_inventory_page(product_detail_page: InventoryItemPage):
    product_detail_page.click_back_to_products_button()
    inventory_page = InventoryPage(product_detail_page.page)
    inventory_page.verify_inventory_page()

@pytest.mark.regression
def test_get_product_description(product_detail_page:InventoryItemPage):
    descr_content = product_detail_page.get_product_description()
    exepct_content = "carry.allTheThings() with the sleek, streamlined Sly Pack that melds uncompromising style with unequaled laptop and tablet protection."
    assert descr_content == exepct_content, f"Product detail description is not correct，EXPECTED:{exepct_content},RECEIVED:{descr_content}"


@pytest.mark.regression
def test_remove_product_from_detail_when_cart_has_two_items(inventory_page):
    # Add two productions into cart
    inventory_page.add_product_to_cart(PRODUCT)
    inventory_page.add_product_to_cart("Sauce Labs Bike Light")

    #Go to the detail product page
    inventory_page.click_product_link(PRODUCT)
    detail = InventoryItemPage(inventory_page,product_id="4")
    detail.verify_inventory_item_page(PRODUCT)

    #Verify the cart number
    orgCount = detail.get_product_count_in_cart();
    assert orgCount == 2, f"The number of products in cart is not correct, EXPECTED:2 RECEIVED:{orgCount}"

    #Remove the production
    detail.remove_product_from_cart()

    #verify the cart number is changed as expected
    curCount = detail.get_product_count_in_cart()
    assert curCount == orgCount -1, \
        f"The number of product count in cart is not correct after remove the product, EXPECTED:{orgCount-1} RECEIVED:{curCount}"                                
                                       