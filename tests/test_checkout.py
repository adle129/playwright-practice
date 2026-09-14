from playwright.sync_api import Page, expect
from pages.inventory_page import InventoryPage
from pages.inventory_item_page import InventoryItemPage
from pages.cart_page import CartPage
from pages.checkout_step_one_page import CheckoutStepOnePage
from pages.checkout_step_two_page import CheckoutStepTwoPage
from pages.checkout_complete_page import CheckoutCompletePage
import pytest

PRODUCT = "Sauce Labs Backpack"
PRICE = "$29.99"

@pytest.mark.smoke
@pytest.mark.parametrize("first_name,last_name,postal_code", [
    ("John", "Doe", "12345")
])
def test_checkout_button_redirects_to_checkout_page(inventory_page: InventoryPage,first_name: str, last_name: str, postal_code: str ):
    inventory_page.add_product_to_cart(PRODUCT)
    inventory_page.click_shopping_cart_link()
    cart = CartPage(inventory_page.page)
    cart.verify_cart_page()
    cart.click_checkout_button()
    checkout_step_one_page = CheckoutStepOnePage(inventory_page.page)
    checkout_step_one_page.verify_checkout_step_one_page()
    checkout_step_one_page.fill_checkout_information(first_name, last_name, postal_code)
    checkout_step_one_page.click_continue_button()
    checkout_step_two_page = CheckoutStepTwoPage(inventory_page.page)
    checkout_step_two_page.verify_checkout_step_two_page()
    shipping_info = checkout_step_two_page.get_shipping_info()
    payment_info = checkout_step_two_page.get_payment_info() 
    price_total = checkout_step_two_page.get_price_total()
    price_tax = checkout_step_two_page.get_price_tax()
    price_item_total = checkout_step_two_page.get_price_item_total()
    assert shipping_info == "Free Pony Express Delivery!", f"Shipping information is incorrect, expected 'FREE PONY EXPRESS DELIVERY!', got '{shipping_info}'"
    assert payment_info == "SauceCard #31337", f"Payment information is incorrect, expected 'SauceCard #31337', got '{payment_info}'"
    assert price_total == "Total: $32.39", f"Total price is incorrect, expected 'Total: $32.39', got '{price_total}'"
    assert price_tax == "Tax: $2.40", f"Tax is incorrect, expected 'Tax: $2.40', got '{price_tax}'"
    assert price_item_total == "Item total: $29.99", f"Item total is incorrect, expected 'Item total: $29.99', got '{price_item_total}'"
    checkout_step_two_page.click_finish_button()
    checkout_complete_page = CheckoutCompletePage(inventory_page.page)
    checkout_complete_page.verify_checkout_complete_page()

    #Verify that the checkout complete page has the correct title and message
    with checkout_complete_page.page.expect_download() as download_info:
        checkout_complete_page.click_generate_pdf_button()
    download = download_info.value
    assert download.suggested_filename.startswith("swag-labs-order-"), f"Expected receipt filename to start with 'swag-labs-order-', got '{download.suggested_filename}'"
    assert download.suggested_filename.endswith(".pdf"), f"Expected receipt filename to end with '.pdf', got '{download.suggested_filename}'"
    checkout_complete_page.click_backhome_button() 
    inventory_page.verify_inventory_page()
