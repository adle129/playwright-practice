"""Trace hands-on scenario: a deliberately planted bug — use the trace viewer to find out what really happened.

Story: the test wants "Sauce Labs Onesie" in the cart, but the code never locates Onesie —
it clicks the first "Add to cart" button on the page (.first), which is actually Backpack.
The failure message only says "the cart doesn't contain Onesie"; the trace shows you "who got clicked".
"""
from pages.cart_page import CartPage


def test_onesie_should_be_in_cart(inventory_page):
    # 🕳️ The planted bug: this should be inventory_page.add_product_to_cart("Sauce Labs Onesie")
    inventory_page.page.get_by_role("button", name="Add to cart").first.click()

    inventory_page.page.locator("[data-test='shopping-cart-link']").click()
    cart = CartPage(inventory_page.page)
    cart.verify_cart_page()

    names = cart.get_item_names()
    assert names == ["Sauce Labs Onesie"], f"expected ['Sauce Labs Onesie'] in the cart, got {names}"
