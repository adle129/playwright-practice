import pytest
import os
from playwright.sync_api import Page
from pages.login_page import LoginPage
from pages.inventory_page import InventoryPage

USERNAME = "standard_user"
PASSWORD = "secret_sauce"
AUTH_FILE = "auth.json"

@pytest.fixture(scope="session")
def storage_state(browser):

    context = browser.new_context()
    page = context.new_page()
    login_page = LoginPage(page)
    login_page.load()
    login_page.login(USERNAME, PASSWORD)
    context.storage_state(path=AUTH_FILE)
    context.close() 
    return AUTH_FILE 


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args,storage_state):
    return {**browser_context_args, "storage_state": storage_state}

@pytest.fixture
def inventory_page(page: Page) -> InventoryPage:
    inv = InventoryPage(page)
    inv.load()
    inv.verify_inventory_page()
    return inv

def pytest_sessionstart(session):
    # 确保报告目录存在(pytest-html 4.x 其实会自动创建父目录,此 hook 可留作示例)
    os.makedirs("reports", exist_ok=True)


