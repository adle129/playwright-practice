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
    # Ensure the reports directory exists (pytest-html 4.x creates parent dirs itself; this hook is kept as an example)
    os.makedirs("reports", exist_ok=True)

def pytest_collection_modifyitems(config,items):
    for item in items:
        if not item.get_closest_marker("flaky"):
            item.add_marker(pytest.mark.flaky(reruns=1,reruns_delay=3))


