"""trace 体验场景:故意埋了一个坑,用 trace 找出"实际发生了什么"。

剧情:测试想验证"购物车里是 Onesie",但代码里没有定位 Onesie,
而是用 .first 点了页面上第一个 Add to cart 按钮(实际是 Backpack)。
失败信息只会告诉你"车里的不是 Onesie";trace 才能让你看到"点的是谁"。
"""
from pages.cart_page import CartPage


def test_onesie_should_be_in_cart(inventory_page):
    # 🕳️ 坑在这里:本应写 inventory_page.add_product_to_cart("Sauce Labs Onesie")
    inventory_page.page.get_by_role("button", name="Add to cart").first.click()

    inventory_page.page.locator("[data-test='shopping-cart-link']").click()
    cart = CartPage(inventory_page.page)
    cart.verify_cart_page()

    names = cart.get_item_names()
    assert names == ["Sauce Labs Onesie"], f"购物车里应该是 Onesie,实际是 {names}"
