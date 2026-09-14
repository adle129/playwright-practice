# Playwright Learning Notes (English)

> Live notes from an AI-assisted learning journey. New knowledge is appended as it is learned.
> Chinese version: [playwright-notes.md](playwright-notes.md)

## Table of Contents

1. [pytest: Running & Configuration](#1-pytest-running--configuration)
2. [Headed / Headless Mode](#2-headed--headless-mode)
3. [Page Object Model](#3-page-object-model)
4. [Locators](#4-locators)
5. [expect Assertions](#5-expect-assertions)
6. [Tools](#6-tools)
7. [Debugging](#7-debugging)
8. [Pitfalls Log](#8-pitfalls-log)
9. [Running Tests & Reports](#9-running-tests--reports)
10. [Flaky Tests](#10-flaky-tests)
11. [Learning Roadmap](#11-learning-roadmap)
12. [Command Cheat Sheet](#12-command-cheat-sheet)

---

## 1. pytest: Running & Configuration

- **Recommended command**: `python -m pytest tests/smoke_test.py -v`
  - `python -m pytest`: runs pytest as a module and adds the **current directory to sys.path** (this is what makes the `pages` package importable)
  - `tests/smoke_test.py`: positional arg — a file, a directory (`tests/`), or a specific test (`file.py::test_name`)
  - `-v`: verbose — prints each test name with PASSED/FAILED instead of dots
- **`pytest` vs `python -m pytest`**: bare `pytest` does NOT add the project root to sys.path → `ModuleNotFoundError: No module named 'pages'`; `python -m pytest` does (or fix it via config below)
- **pytest config must live in `[tool.pytest.ini_options]`** — putting it under `[project]` is **silently ignored** (no error, no effect):

  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]                      # add project root to sys.path (pytest>=7)
  testpaths = ["tests"]                   # default scan directory
  addopts = "-v --headed --slowmo=2000"   # default args, applied however pytest is invoked
  ```

- **VSCode Testing panel**: configure `.vscode/settings.json` (`python.testing.pytestEnabled`, `pytestArgs`); **click refresh after config changes** — the panel caches
- **The ▶ Run button does not run pytest**: it executes `python file.py`; pytest config is ignored and test functions are only *defined*, never executed
- Other useful flags: `-s` (show prints), `-k "keyword"` (filter by name), `-q` (quiet), `--headed`, `--slowmo=ms`

### Fixtures & conftest.py (dependency injection)

- **fixture = preparation steps** before a test (login, data setup). pytest executes them and injects results into the test.
- **Core mechanism: dependency injection, matched by name.** pytest reads test parameter names → finds fixtures with the same name → executes them → passes return values as arguments:

  ```python
  # What you write:
  def test_backpack_price(inventory_page):   # parameter name = fixture name
      ...

  # What pytest does internally:
  result = inventory_page_fixture(page)   # ① execute the fixture
  test_backpack_price(result)             # ② inject the result, call your test
  ```

- **What a fixture is at the Python level: decorator + registry** (no magic):
  - `@pytest.fixture(scope="session")` is a plain decorator, equivalent to `func = pytest.fixture(scope="session")(func)` — two calls: the factory (takes config, returns a decorator) → the decorator (registers the function in pytest's global registry by name, returns it unchanged)
  - **You never call a fixture function directly** — pytest's main loop looks up the registry by parameter name, calls it for you, and injects the return value. You only *request* by name; you never *call*.
- ⚠️ **A fixture is not executed just because it is defined** — it runs only when *requested*: ① a test parameter names it ② another fixture depends on it (dependency chain) ③ `autouse=True` (truly unconditional). Experiment: define an unused fixture with a print — it never prints. Timing note: a session fixture runs **before the first test that needs it**, not at process startup; `delete_output_dir` (pytest-playwright) is autouse (always runs), `storage_state` is pulled in via the dependency chain.
- **`page` is also a fixture** (registered by pytest-playwright) — the parameter must be named `page` to be injected
- **Fixtures can depend on each other**: `inventory_page` declares parameter `page`; pytest resolves dependencies recursively
- **scope controls how many times it runs**: `function` (default — every test, full isolation) / `session` (once per session, shared but can be polluted)
- **Execution order — three rules**:
  1. **Order is determined by dependencies, not by definition order** — pytest resolves the dependency tree recursively; the deeper the dependency, the earlier it runs
  2. **S (session) runs once and is cached; F (function) runs per test** — 7 tests = 1 login (storage_state is S) + a fresh page per test (page is F)
  3. **Teardown runs in reverse order** (stack semantics): last set up, first torn down
  - Same-name override trick: defining `browser_context_args(browser_context_args, ...)` resolves the parameter to the **plugin's original** fixture — no infinite recursion; this is pytest's official extension mechanism
  - **Inspection tools**: `pytest --setup-plan` (show fixture plan without running) / `--setup-show` (show SETUP/TEARDOWN while running) — never guess, just look
- **`yield` splits a fixture in two**: code before yield = setup; code after = teardown
- **`conftest.py` is auto-loaded by pytest** (no import needed) — fixtures inside are visible to tests in the same directory and below. It's the conventional home for shared fixtures.
- ⚠️ **conftest auto-loads *fixture registrations*, not *names***: fixtures are injected by parameter name (you don't import `inventory_page`), but class names imported inside conftest (`InventoryPage` etc.) are visible only to conftest itself — test files still need their own `from pages.xxx import XxxPage` for type annotations/instantiation, otherwise `NameError`. Python module namespace isolation still applies; annotations are optional but "annotate + import" is the professional default.
- **Which page should a fixture return? The state where most tests start.** 90% of tests start on the logged-in inventory page → return `InventoryPage`; other pages are reached from there by calling page methods. Don't create a fixture per page; tests that specifically test the login page use the raw `page` parameter.
- Standard example:

  ```python
  # conftest.py (project root)
  @pytest.fixture
  def inventory_page(page: Page) -> InventoryPage:
      login = LoginPage(page)
      login.load()
      login.login(USERNAME, PASSWORD)
      inv = InventoryPage(page)
      inv.verify_inventory_page()
      return inv
  ```

- **return vs yield: does it need teardown?**
  - `return` is a special case of `yield` (setup only, no teardown). The injection mechanism is identical; the only question is "is there anything to do after the test?"
  - **Rule: did the fixture acquire something that must be released/deleted/closed?** Yes → `yield` + cleanup; No → `return`
  - Classic "debts": created test data that must be deleted (create user → test → delete); acquired shared resources that must be returned (begin transaction → test → rollback)
  - **Playwright case**: browser/page lifecycle is managed by the plugin's own `page` fixture (internally yield: open browser → inject page → close browser), so your own login-type fixture is pure state preparation with zero resource usage → `return` is correct, `yield` would be redundant
  - **Teardown has try/finally semantics**: code after yield runs whether the test passed or failed (cleanup even on failure); but if setup itself raises, teardown never runs

### Test Splitting & Parametrization

- **Why splitting is safe**: fixtures default to `function` scope → every test gets a fresh browser and re-login, fully isolated — split freely, run individually
- **Splitting principles**:
  - One test verifies one thing; the test name states "scenario + expectation" (e.g. `test_add_product_updates_cart_badge`)
  - Small duplication between tests is fine; **don't invent an "add-to-cart fixture" to remove 2 duplicated lines** — over-abstraction is harder to maintain than duplication
  - Data shared by multiple tests becomes module-level constants (`PRODUCT = "Sauce Labs Backpack"`)
  - To construct the "next" page object in a test, use `inventory_page.page` (the Playwright Page stored by BasePage)
- **Parametrization**: same logic, different data → `@pytest.mark.parametrize("a, b", [(v1, v2), ...])`:

  ```python
  @pytest.mark.parametrize("product, price", [
      ("Sauce Labs Backpack", "$29.99"),
      ("Sauce Labs Bike Light", "$9.99"),
  ])
  def test_product_price(inventory_page, product, price):
      actual = inventory_page.get_product_price(product)
      assert actual == price, f"expected {price}, got {actual}"
  ```

  - N data rows → N tests run automatically; a single failing row is pinpointed
- **Post-split self-check**: ① `pytest -v` shows N independent PASSED ② `-k keyword` can run one ③ intentionally break one assertion → only that test goes red (failure isolation)

### pyproject.toml & TOML

- **TOML** = Tom's Obvious, Minimal Language — designed for config files (vs JSON: no comments, noisy; vs YAML: indentation-sensitive)
- **Two syntax concepts**:
  - Key-value pairs: `key = value` (strings, ints, bools, arrays); comments with `#`
  - Tables: `[name]` opens a table — **all keys until the next `[name]` belong to it** (the root cause of the "addopts in the wrong table" pitfall)
- **pyproject.toml = the project configuration hub** (PEP 518/621) — one file replacing setup.py / setup.cfg / pytest.ini
- **Table roles**: `[project]` = package metadata (name/version/dependencies); `[tool.xxx]` = third-party tool namespaces (tool x reads `[tool.x]`, e.g. `[tool.pytest.ini_options]`, `[tool.ruff]`)
- Typical structure:

  ```toml
  [project]
  name = "playwright-practice"
  requires-python = ">=3.12"
  dependencies = []

  [tool.pytest.ini_options]
  pythonpath = ["."]
  testpaths = ["tests"]
  addopts = "-v --headed --slowmo=2000"
  ```

## 2. Headed / Headless Mode

- **Playwright runs headless by default**: the browser works in the background with no window — "I don't see a page" is normal, not an error
- `--headed`: show the browser window; `--slowmo=500`: pause 500ms between actions so humans can follow (only meaningful in headed mode)
- **Chromium ≠ Chrome**: Chromium is the open-source engine project; Chrome = Chromium + Google's closed components (auto-update, some codecs). Playwright uses its **own downloaded Chromium build**, not your installed Chrome.
- Headless = the same engine (Blink rendering + V8 JS) doing real work, just not painting pixels on screen; behavior is effectively identical
- To use the system Chrome: `p.chromium.launch(channel="chrome")`, or `--browser-channel=chrome` under pytest (Edge: `msedge`)

## 3. Page Object Model

- **Before writing a page class, ask three questions**:
  - What does the page **have**? (elements) → locators in `__init__`
  - What can the user **do**? (actions) → action methods
  - What should tests **verify**? (assertions) → `verify_xxx` methods
- **`__init__` is the only constructor that gets called automatically**:

  ```python
  # ✅ LoginPage(page) → Python creates the instance and calls __init__(self, page)
  login = LoginPage(page)

  # ❌ init_page is a plain method: page binds to self, and the required arg is missing
  login = LoginPage.init_page(page)
  # TypeError: LoginPage.init_page() missing 1 required positional argument: 'page'
  ```

- **Calling a method requires parentheses**: `login.load` only *mentions* the method object; `login.load()` actually calls it
- Action methods do things and assert nothing; assertion methods check and do nothing
- **Method parametrization**: one method covers all inputs instead of copying one method per input:

  ```python
  def add_product_to_cart(self, product_name: str):
      # when called as add_product_to_cart("Sauce Labs Backpack"),
      # product_name IS that string: expands to has_text="Sauce Labs Backpack"
      self.product_items.filter(has_text=product_name).get_by_role("button", name="Add to cart").click()
  ```

- **False green**: a weak assertion (e.g. only checking the title) lets the test pass without verifying what matters. The test: **intentionally break the behavior — the test should turn red.** Example: the login page and inventory page share the title "Swag Labs", so a title-only check cannot tell them apart.
- **Locators live only in page classes; tests never touch them** (the soul of POM encapsulation):
  - One-liner: Locators are encapsulated inside Page Objects — test files never touch them. Tests interact with pages only through public methods.
  - Three reasons: **maintainability** (the page layer is the single source of truth; UI changes are fixed in one place) / **readability** (tests read like business steps, no CSS knowledge needed) / **separation of concerns** (page layer owns the *how*, test layer owns the *what*)
  - Closing line for interviews: It's the same encapsulation idea as OOP — implementation details are hidden behind an interface, so changes stay local.
  - If asked "won't page classes get too big?": shared elements (header/footer) go into a **BasePage** and are inherited, not duplicated
  - Anti-pattern: `inventory_item.product_price.inner_text()` in a test → add `get_product_price()` to the page class and call it instead
- **Splitting a long E2E test (one main flow + targeted tests)**:
  - **Don't shred the E2E main flow**: keep one complete journey test (verifies "the whole flow works"), with multiple assertions each carrying a clear message
  - **Extract details into targeted tests**: form validation (negative cases), price calculation, per-page element checks — anything you'd want to "run and fix alone"
  - Judging rule: "If this assertion fails, do I want to run it alone?" Yes → split it out; it's just a step in the flow → keep it in the main line
  - **The right fix for "repeated login" is technology, not bigger tests**: `storage_state` stores the auth state so tests skip UI login — remove duplication with technology, not by avoiding the split
  - Benefits of splitting: fast failure localization, parallelizable, cheap re-runs, shorter chains are more stable (flaky probability multiplies per step), focused maintenance
  - The real cost of over-splitting: duplicated preconditions → solved with fixtures/storage_state, not by not splitting
- **Fixturizing preconditions (AAA structure in practice)**:
  - Every test needs **independent preconditions** (isolation is non-negotiable), but duplicated precondition code is abstracted into fixtures — not copy-pasted, and not shared via test-to-test dependency
  - Structure: Arrange (preparation) → in fixtures; Act / Assert → in tests — **a test only writes the steps unique to itself**
  - Example: detail-page tests share the "navigate from inventory into the detail page" precondition → define a `product_detail_page` fixture (depends on `inventory_page`); tests get the page in one line
  - Where to put a fixture: used by one test file → define it inside that file (most cohesive); used by multiple files → root conftest.py; shared within a subdirectory → that directory's conftest.py
  - **Complete extraction criteria**: ① precondition shared by ≥2 tests → fixture; ② used by only 1 test → write it in the test (accept small duplication over over-abstraction); ③ **the precondition must be inserted BEFORE the fixture's own action** → step down a layer, use the more basic fixture and sequence it yourself (a fixture runs before the test body — no queue-jumping). Fixture layering: base layer (common start) / common-path layer / special paths walk themselves
  - Bonus: magic values (like product_id) get locked inside the fixture; tests don't touch page internals
  - **Eliminate the duplication of *writing*, keep the repetition of *running***: a fixture is written once (code layer) but function-scope fixtures still run once per test (execution layer) — that repeated run IS the isolation; removing it starts cross-test pollution
  - **Can the running repetition also be removed? Depends on the product**: is the result a "credential" (read-only, safe to share, e.g. auth cookies) → session scope, run once; or a "scene" (mutable state, e.g. page navigation / cart contents) → function scope, run per test. `storage_state` (credential) and `product_detail_page` (scene) are the two sides of this rule in this project.
- **Test file ownership rule: group by the page that owns the *behavior under test***: ask "when this test fails, which page is broken?" — "clicking a product link navigates to the detail page" is owned by the inventory page (link/navigation behavior) → inventory test file; "the detail page shows the right price" is owned by the detail page → detail file. Ownership follows the **acting page**, not "which page's content the assertion reads". And test names must match content (a test named `shows_price` must actually assert the price).
- **Where do assertions live: pages or tests?**

  | Layer | Tool | Asserts |
  |---|---|---|
  | pages/ | `expect` (verify_xxx methods) | **Page state**: "am I on the right page? are key elements correct?" |
  | tests/ | `assert` | **Business rules**: is the data in this scenario correct? |

  - Judging rule: is the assertion "a fact that always holds for this page" → page class; "a business rule this scenario cares about" → test
  - Three kinds of page methods: **action methods never assert**, `verify_xxx` checks state with expect, `get_xxx` only returns data and judges nothing
  - Example:

    ```python
    # pages/: fetch data + page state
    def get_product_prices(self) -> list[str]:
        return self.product_prices.all_inner_texts()

    def verify_inventory_page(self):
        expect(self.page).to_have_url(".../inventory.html")
        expect(self.page.locator(".title")).to_have_text("Products")

    # tests/: reuse verify + judge business rules
    inventory.sort_products("lohi")
    prices = inventory.get_product_prices()
    assert prices == sorted(prices)
    ```

## 4. Locators

- **The three CSS selector basics**:
  - `#login-button` → id selector
  - `.title` → class selector (`<span class="title">Products</span>`)
  - `div` → tag selector
  - Combinations/attributes: `input[id='user-name']`, `[data-test='xxx']`
- **What is data-test**: `data-*` are HTML5 custom attributes, not rendered; `data-test` / `data-testid` / `data-cy` are **stable hooks developers leave specifically for test automation** — changing one deliberately breaks tests, so they stay stable
- **Locator priority**: ① `data-testid` (use when available) → ② `get_by_role` (user perspective) → ③ id / stable class → ④ text / XPath (last resort)
- **`get_by_role`'s `name` is NOT the HTML `name` attribute — it's the *accessible name*** (what users see / screen readers announce):

  ```html
  <button id="add-to-cart-sauce-labs-onesie" name="add-to-cart-sauce-labs-onesie">
      Add to cart   ← the accessible name is the button text, not the name attribute!
  </button>
  ```

  | Element | Accessible name comes from |
  |---|---|
  | button / a | inner **text** |
  | input[type=submit] | `value` attribute (that's where the login button's "Login" comes from) |
  | text input | associated label or placeholder |
  | img | `alt` attribute |
  | any element | `aria-label` (highest priority) |

  - How to check: ① visible text on the page (intuition) ② DevTools → select element → Accessibility panel's Name field (authoritative) ③ codegen's Pick locator suggestion
- **strict mode**: when a locator resolves to **multiple** elements, actions/assertions fail with "resolved to N elements" — locators must be unique; Playwright refuses to guess
- **`filter()` picks a target out of a pile of similar elements**:

  ```python
  self.product_items = page.locator(".inventory_item")            # 6 cards
  self.product_items.filter(has_text="Sauce Labs Backpack")       # → 1
  ```

  - `has_text="text"`: substring, case-insensitive; `has=locator`: must contain a matching descendant; `has_not_text=`: negation; chainable
  - ⚠️ The result must still be unique: "Sauce Labs" matches 5 cards, "T-Shirt" matches 2 → pass a full, distinctive name
- **`exact=True` exists only in the "find-by-text" APIs**: `get_by_text`, `get_by_role`'s `name=`, `get_by_label`, `get_by_placeholder`, `get_by_title`, `get_by_alt_text`; **`locator()`, `filter()` and `to_have_text()` don't have it**
- Semantics: default = "**substring + case-insensitive**"; `exact=True` = "**whole string + case-sensitive**" (both normalize whitespace; ignored when using regex):

  ```python
  page.get_by_text("T-Shirt").count()                              # 2 (two names contain T-Shirt)
  page.get_by_text("T-Shirt", exact=True).count()                  # 0 (nothing is exactly "T-Shirt")
  page.get_by_text("Sauce Labs Bolt T-Shirt", exact=True).count()  # 1 ✅
  ```

- `to_have_text` matching rules (different from get_by_text!): a string = **whole-text match** + whitespace normalization + case-insensitive by default; control case with `ignore_case=False`; substring matching uses `to_contain_text("...")`
- **Chained locators (parent-child)**: a locator can search downward from another locator:

  ```python
  container.locator(".inventory_item")                  # container → 6 cards
  items.filter(has_text=...).get_by_role("button", name="Add to cart")  # card → button inside it
  ```

- **Locator debugging duo**: `count()` (how many matched); `all_inner_texts()` (print the texts of all matches)
- **Nested DOM: selectors "skip layers"**:
  - CSS selectors match at **any depth** by default: `.inventory_item_price` finds all 6 prices directly; the wrapper layers (description/label/pricebar) don't need to be written
  - You only need "layers" for "**this specific product's** price", and only two layers: **locate the parent (product card), then chain to the child (price)**:

    ```python
    product_item = self.product_items.filter(has_text="Sauce Labs Backpack")   # parent: one product
    price = product_item.locator("[data-test='inventory-item-price']").inner_text()  # child: its price
    ```

  - Chaining `.locator()` **narrows the search scope**: the child locator only searches inside the parent
  - `inner_text()` returns visible text (clean); `text_content()` returns raw DOM text (may include whitespace/hidden text) — prefer `inner_text()` for values
  - ⚠️ Python identifiers can't contain hyphens: `self.shopping-cart-badge` is a syntax error; use `self.shopping_cart_badge`

## 5. expect Assertions

- **expect auto-waits (polls)**: retries for up to 5s by default, passes the moment the condition holds, fails only on timeout. Python's `assert` checks exactly once — pages are asynchronous; right after a click the page hasn't finished navigating, so a bare `assert` is flaky by design
- Pattern: `expect(subject).matcher(expected)`
- Common assertions:

  | Subject | Matcher | Notes |
  |---|---|---|
  | page | `to_have_title("...")` | page title |
  | page | `to_have_url("...")` | current URL (**exact match** — the login/inventory distinction relies on it) |
  | locator | `to_be_visible()` | element visible |
  | locator | `to_have_text("...")` | whole-text match (whitespace-normalized, case-insensitive by default); substring: `to_contain_text` |
  | locator | `to_have_count(n)` | resolves to n elements |

- Failures print a detailed call log (actual values, timeout, page state) — far easier to debug than assert

### expect vs assert: which one when

- **Core difference**: `expect` polls with retries (up to ~5s), for conditions that "aren't true yet but will be"; `assert` checks once, for values that are "already settled"
- **Decision rule**:
  - Subject is a **locator or page** (page state: visibility, text, URL, title, count) → `expect`
  - Subject is a **Python value you already hold** (string, list, number) → `assert`
  - Ask: could this condition "not be true right now, but become true in a moment"? Yes → expect; No → assert
- **Positive examples**:

  ```python
  # page state: URL may not have changed yet, badge may not be updated → expect (waits)
  expect(self.page).to_have_url("https://www.saucedemo.com/inventory.html")
  expect(self.cart_badge).to_have_text("1")

  # snapshot data already fetched from the page: settled the moment you hold it → assert
  prices = page.locator(".inventory_item_price").all_inner_texts()
  assert len(prices) == 6
  assert prices == sorted(prices)     # verify sort result
  ```

- **Anti-patterns**:
  - `assert page.locator(".title").inner_text() == "Products"` — if the element hasn't rendered, `inner_text()` raises immediately, no retry → flaky; use `expect(...).to_have_text()`
  - `expect(login_button.is_visible(), "Login")` — `expect()` takes only page/locator/API response, **never a bool**; if you already computed a bool, use assert, or use `expect(locator).to_be_visible()` directly
- **Typical workflow**: `expect` waits for the page to reach a state (navigated, element appeared) → extract data (`all_inner_texts()` / `inner_text()`) → `assert` validates the data. expect owns *timing*, assert owns *content*.
- **Redirect-type tests may consist entirely of verify (expect) calls — no bare assert is fine**: expect raises AssertionError on failure; it IS the assertion. The standard is "does the test contain checks that can fail", not "does it contain the assert keyword". Self-check: break a verify's expected value and see the test turn red. The real violation is a test that only acts and checks nothing (false green).
- **assert can carry a message** (write one every time):

  ```python
  assert condition, "message shown on failure"
  assert len(prices) == 6, f"expected 6 items, got {len(prices)}"
  # failure output: AssertionError: expected 6 items, got 5
  ```

  - Habit: write "expected X, got Y" f-strings, not just "wrong"; evaluated only on failure, zero performance cost
  - pytest also rewrites assert to show both sides of the expression, but the message carries the business meaning

## 6. Tools

- **codegen (code generator)**:

  ```bash
  playwright codegen https://www.saucedemo.com/
  ```

  - Opens a browser; your manual actions are **translated into Playwright code in real time** in the side panel
  - Typical uses: ① **find locators** — hover the Pick locator over the target element and see what Playwright recommends ② record a flow as a "step-by-step manual" to copy from
  - ⚠️ Generated code is a linear transcript: **no assertions, no structure, only the one path you walked** → a starting reference only; refactor into Page Objects + assertions

## 7. Debugging

- **The debugging ladder (cheap → powerful, in order)**: read the error → watch it happen → print probes → screenshots/video → trace → page.pause()
- **Step 0: read the error (solves 80%)**
  - **First check whether this error is the same one as last time**: if the error type changed (e.g. FileNotFoundError → Page.goto TimeoutError), the problem domain changed — following the old theory leads nowhere
  - `FAILED` = assertion not met (compare expected vs actual); `ERROR` = exception thrown (bad locator / undefined name / syntax error)
  - Quick lookup:

    | Error keywords | What it means |
    |---|---|
    | `strict mode violation: resolved to N elements` | locator not unique |
    | `resolved to 0 elements` / `not found` | locator finds nothing: typo / page didn't navigate / element not yet present |
    | `Timeout 5000ms exceeded` | expect waited in vain → the expected behavior didn't happen |
    | `TimeoutError ... exceeded` (on `inner_text`/`click`/`fill`) | ≈ locator matched **0 elements**: check the locator spelling first (attribute values, hyphens vs underscores), not the network |
    | `expected ... actual ...` | assertion unmet — compare the two sides |
    | `AttributeError: has no attribute` | name/method misspelled or undefined |
    | `ModuleNotFoundError` | import path problem |

  - Read the **line number**: which line failed = which action/assertion is the problem; the scope shrinks to one line
  - **The Call log is the primary crime scene for locator problems**: timeout errors print the full locator chain verbatim — compare every attribute value in the chain against the real page; a one-character typo can't hide (real example: `inventory_item` underscore vs `inventory-item` hyphen)
- **Step 1: watch it with `--headed --slowmo`**: did the page navigate? did it click the right button? which step does it stall at?
- **Step 2: print probes + `-s`**:

  ```python
  print("current URL:", page.url)                                    # which page am I on?
  print("match count:", page.locator("[data-test='xxx']").count())   # how many matched?
  print("texts:", page.locator(".xxx").all_inner_texts())            # what did it find?
  ```

- **Step 3: failure screenshots/video**: `pytest --screenshot=only-on-failure --video=retain-on-failure`, artifacts in `test-results/`
- **trace in real-world companies**: not for "running", for "investigating" — the complete evidence archive of a failure. Typical scenarios:
  1. **CI failure forensics (most common)**: CI configured with retain-on-failure; failures are archived automatically; engineers inspect artifacts without re-running locally (many CI failures can't be reproduced locally anyway)
  2. **"Green locally, red on CI"**: trace's Console/Network/Metadata reveals environment differences (slow network / viewport / rate limiting / browser version)
  3. **Locator mysteries**: DOM snapshots show what the locator actually matched at that moment (strict mode, wrong element, zero elements)
  4. **Timing races**: the timeline is millisecond-accurate — see "the click happened before the page finished loading" flaky root causes
  5. **Cross-role communication**: attach the trace zip to a bug ticket — developers don't need to read test code to see the reproduction path
  6. **Onboarding**: read a trace to understand what an old test does and where it fails, faster than reading code
  - Company workflow: CI red → open HTML report → open the failed case → view trace in the attachment → locate the step on the timeline → decide: test issue (fix locator/timing) or product bug (attach trace and screenshot to the developer)
  - Evidence division of labor: screenshot = see the looks at a glance; video = show the process to non-automation people; trace = engineers investigate the *why* (DOM/network/timing); HTML report = the aggregating front door
  - **Engineering note ①: data privacy — three lines of defense** — Line 1: use **fake data / dedicated accounts** in test environments (what never appears needs no masking — the most fundamental); Line 2: Playwright-level minimization (`tracing.start(sources=False)` to exclude source code, `page.mask(locator)` pixel masking, trace only critical segments); Line 3: pipeline post-processing (regex redaction scripts before archiving, CI artifacts internal-only + permissioned + short retention, internal links in bug tickets — never send zips outside). Real-world priority: fake data + permissions suffices for most teams; finance/healthcare add regex redaction and masking.
  - **Engineering note ②: traces are big — four moves** — ① keep failures only (retain-on-failure already cuts the bulk) ② CI archival policy: upload only on `if: failure()` + `retention-days: 7` (GitHub Actions) / `expire_in: 7 days` (GitLab) — solves 90% of the volume ③ shrink each archive: sources=False, trace only critical segments, **pick video OR trace** (video is the biggest) ④ cloudify: upload to object storage / S3 / test platforms, put links in the report, keep nothing on the CI machine
  - **Tiered evidence (sensitive scenarios: skip trace, use code-level alternatives)**: trace is not all-or-nothing; three layers each own one concern — `--tracing` owns the global default (keep only on failure), code-level `tracing.start/stop` owns granularity (which segment, sources/snapshots toggles), `page.mask()` and logging Filters own privacy:
    - Sensitive pages (login/payment/account) → no trace; screenshot + mask, or logs only
    - Selective trace by marker: check `request.node.get_closest_marker("trace")` in a fixture and start/stop only for marked tests
    - Log redaction: a Python logging `Filter` regex-replaces patterns in `record.msg` (phone/card numbers → ***) — more elegant than post-unzip redaction
- **Step 4: trace (the time machine, for the hard cases)**:

  ```bash
  pytest --tracing=retain-on-failure    # keep traces only for failed tests
  playwright show-trace test-results/<test-name>/trace.zip
  ```

  - What you see: the per-action timeline, DOM snapshots before/after each step (what the locator actually matched), screenshots, console logs, network requests
  - When: earlier steps gave no answer — especially "why didn't the locator match / matched the wrong thing"
- **Step 5: interactive debugging**: insert `page.pause()`, or `PWDEBUG=1 python -m pytest ...` — the Inspector pops up; step through, inspect elements live
- **Step 6: binary search the scope**: `-k name` runs only the failing test; comment out half the steps and bisect down to the exact step
- ⚠️ Beginner trap: skipping the first two steps and jumping straight to trace — the information volume is overwhelming. Error messages and your own eyes are always the best debugger.
- **IDE squiggles vs runtime errors (environment issues)**:
  - `Import "pytest" could not be resolved` (Pylance squiggle) **≠** runtime error — it's VSCode's static checker saying "the interpreter I'm using doesn't have this package"; terminal execution is unaffected
  - Usual cause: the interpreter selected in VSCode and the one the terminal uses are **not the same**
  - **Judging standard: if the command line runs fine, the code is fine — the squiggle is just a mismatched IDE environment**
  - Fix: `Ctrl+Shift+P` → "Python: Select Interpreter" → pick the interpreter your terminal uses; Pylance re-indexes and the squiggle disappears
  - General rule: for IDE autocomplete anomalies, squiggles, and type errors — first check "is the interpreter selected correctly?"

## 8. Pitfalls Log

| # | ❌ Wrong | ✅ Right | Why |
|---|---|---|---|
| 1 | `login.load` | `login.load()` | Missing parentheses → method never called, page never navigated |
| 2 | `def init_page(...)` / `LoginPage.init_page(page)` | `def __init__(...)` / `LoginPage(page)` | Only `__init__` is the constructor and gets called automatically |
| 3 | `get_by_role("button", name="login-button")` | `get_by_role("button", name="Login")` | `name` matches the accessible name (the value), not the id |
| 4 | Running `python tests/xx.py` directly or the ▶ button | `python -m pytest` / VSCode Testing panel | Direct execution doesn't run tests and can't find the `pages` package |
| 5 | `addopts` under the `[project]` table | under `[tool.pytest.ini_options]` | pytest only reads its own table; wrong placement = silently ignored |
| 6 | Verifying the inventory page by title only | add `expect(page).to_have_url("...inventory.html")` | Both pages share the title; weak assertion → false green |
| 7 | Bare `pytest` (without `-m`) | configure `pythonpath = ["."]` in pyproject | Bare pytest doesn't add the project root to sys.path |
| 8 | Bare `--tracing` in addopts | `--tracing=retain-on-failure` | It's a value-requiring option (on/off/retain-on-failure), not a flag; only flags like `--headed` can stand alone |
| 9 | `--html=test-results/report.html` raises FileNotFoundError (always fails when all green; passes when something fails!) | **Don't put the report inside Playwright's output dir**: use `--html=reports/report.html` | The real culprit is pytest-playwright's autouse session fixture, which deletes the whole `--output` directory (default test-results) at session start. All green → no artifacts → directory stays deleted → report can't be written. A failure → trace artifacts re-create the directory → it works by luck. A sessionstart hook can't help (deletion happens after it); pytest-html 4.x actually creates parent dirs itself |
| 10 | `Page.goto: Timeout 30000ms exceeded` (Call log shows navigating/waiting until "load") | Re-run to verify (`--lf`); if recurring, lower --slowmo or use `goto(wait_until="domcontentloaded")` | This is a **network/site-level** timeout (the site didn't respond in 30s), not a locator issue; free demo sites rate-limit → flaky |
| 11 | A test "disappeared": collected count is one less than expected | Check whether the function name starts with `test_` | pytest only collects `test_`-prefixed functions — **no error, silently skipped**; filenames also need `test_*.py` / `*_test.py` |

---

## 9. Running Tests & Reports

- **By scope**: `pytest` (all) / `pytest tests/xx.py` (one file) / `pytest tests/xx.py::test_xxx` (one test)
- **By name/marker**:
  - `-k "cart"` / `-k "cart or price"` — name substring / logical combination (case-sensitive)
  - **Marker layering**: tag tests with `@pytest.mark.smoke` / `@pytest.mark.regression`, registered in pyproject:

    ```toml
    [tool.pytest.ini_options]
    markers = [
        "smoke: fast core-flow verification",
        "regression: full verification",
    ]
    ```

  - `pytest -m smoke` runs only the smoke layer — the execution side of the test pyramid: smoke daily (fast), full suite before release
- **Failure control**: `-x` (stop at first failure) / `--maxfail=3` / `--lf` (only last-failed — debugging hero) / `--ff` (failed first)
  - Debugging workflow: `--lf` → fix → `--lf` green → full regression
- **Parallel (xdist)**:
  - Usage: `pytest -n auto` (by cores) / `-n 4` (fixed); `--dist` strategies: `load` (default, dynamic balancing) / `loadscope` (group by file, for file-level shared state) / `loadgroup` (custom groups via `@pytest.mark.xdist_group`)
  - Principle: master collects → spawns N independent worker processes → distributes → aggregates; **workers share no memory**
  - **When you can**: ① tests fully independent ② no data conflicts ③ note session fixtures run once per worker (4 workers = 4 logins; function scope is naturally safe) ④ headless only
  - **When you can't**: headed debugging, flaky investigation, order-dependent tests, unique shared resources (ports/files/accounts), free third-party sites (multiplied request volume → rate limiting), too few tests (worker startup overhead makes it slower)
  - **Temporarily override addopts for headless parallel**: `pytest -n 2 -o "addopts=--tracing=retain-on-failure --html=reports/report.html --self-contained-html"`; `[gw0]`/`[gw1]` prefixes in output = different workers
  - **Engineering habit: parallel flags don't go into addopts** — they're per-scenario toggles (on in CI, off locally); put them in CI config or scripts

### Screenshots & Video

- **CLI switches (pytest-playwright, zero code)**:
  - `--screenshot on / only-on-failure / off`; `--video on / retain-on-failure / off`
  - ⚠️ Naming trap: screenshots use **only-on-failure**, videos use **retain-on-failure** — same meaning, different names
  - Artifacts land in `test-results/<test-name>/`; only-on-failure/retain-on-failure are the CI and daily defaults (zero cost on success, evidence on failure)
- **Code-level capture (for specific moments)**:

  ```python
  page.screenshot(path="screenshots/step1.png", full_page=True)   # full_page = long-page capture
  page.locator("#cart").screenshot(path="screenshots/cart.png")   # screenshot one element

  context = browser.new_context(record_video_dir="videos/")        # video is enabled at context level
  # ...test actions...
  context.close()   # video written on close; webm format (plays directly in Chrome)
  ```

  - Typical use: business evidence (e.g. "screenshot the successful order page") — something CLI switches can't do
- **Report integration**: pytest-playwright automatically embeds screenshots/videos/traces as attachments in the pytest-html report — open the failed case and they're all there. A zero-config "failure scene archive".
- **Quick choice**: interactive debugging → trace; CI evidence → only-on-failure/retain-on-failure; business evidence → code `page.screenshot()`; demos → `--video on` (temporary; don't put it in addopts — recording has real overhead)
- **Report ladder (by investment)**:

  | Tier | Tool | Notes |
  |---|---|---|
  | Terminal | pytest built-in | `-v`, `--durations=10` (slowest 10 tests) |
  | JUnit XML | built-in `--junitxml=test-results/junit.xml` | CI-standard format (Jenkins/GitLab/Azure all consume it) |
  | HTML | pytest-html (**separate install**, not built-in) | single-file report, view in browser, share with the team |
  | Allure | allure-pytest + allure CLI (heavy) | step trees, screenshot attachments, history trends — for big projects: `pytest --alluredir=...` → `allure serve ...` |
  | Playwright built-in | trace/screenshots/video | failure-scene evidence, embeddable as attachments in HTML/Allure reports |

- **Engineering habit**: keep all artifacts (reports/screenshots/videos/traces) in `test-results/`, and gitignore it (reports don't belong in version control)
- ⚠️ **pytest-playwright vs pytest-html directory conflict (important!)**:
  - pytest-playwright registers an `autouse` session fixture that **deletes the entire `--output` directory (default test-results) at session start** — that directory is its turf for screenshots/videos/traces
  - Therefore **the HTML report must never be written into test-results/**: when all tests pass there are no artifacts to re-create the directory, and report writing fails with FileNotFoundError (a failure re-creates the directory via trace artifacts — it works by luck, masquerading as flaky!)
  - Correct setup: report in its own directory `--html=reports/report.html`, Playwright artifacts stay in `test-results/`
  - pytest-html 4.x creates the report's parent directory itself; a `pytest_sessionstart` hook can't protect you either (Playwright's deletion happens after the hook) — order: configure creates dir → sessionstart (your hook) → first test setup (Playwright deletes it)
- **Hook concept**: fixed function names (e.g. `pytest_sessionstart`) that pytest calls automatically at the matching lifecycle moment — no decorator/import needed; same "convention over configuration" family as fixtures (injection by name)
- **Where hooks/fixtures can be defined**: conftest.py (officially a "local plugin", ✅) or third-party plugin packages (pytest-playwright's page fixture comes from there, ✅); **defining them in plain test files `test_*.py` has no effect** (❌)
- **conftest directory scoping**: each directory's conftest only affects that directory and below; closer to the test = higher priority; subdirectories can override same-named fixtures/hooks from parents — shared things go in the root conftest, local things in lower-level conftests
- **pytest-html install & usage**:

  ```bash
  pip install pytest-html    # must install first; not built into pytest
  pytest --html=reports/report.html --self-contained-html
  # --self-contained-html: inlines CSS/JS into one HTML file, shareable as a single file
  ```

- Suggested adoption order: terminal -v + trace → pytest-html → junitxml → allure (only for big projects)

---

## 10. Flaky Tests

- **Definition**: same code, same input, nothing changed — yet the test sometimes passes and sometimes fails. Keywords: nondeterministic, unreproducible.
- **Three root-cause categories**:
  1. **The test itself (the bulk)**: timing races (asserting immediately after an action, or "fixing" it with `sleep()` — a slow machine still fails), hardcoded timeouts too short, test coupling (shared state / execution order dependency), test data conflicts, fragile locators (text/coordinates/deep XPath)
  2. **The environment**: network jitter, third-party site rate limiting (pitfall #10's saucedemo goto timeout is a live example), insufficient CI resources, browser version differences
  3. **The system under test**: genuine intermittent bugs (async tasks/cache), legitimate async behavior (animations/lazy loading) wrongly assumed synchronous
  - Investigation order: test timing first → environment second → suspect a real product bug last
- **Strategy: prevent → detect → stop the bleeding → cure**:
  - **Prevent**: use `expect` auto-waiting, ban `sleep()`; rely on Playwright auto-waiting (click waits for visible/stable/enabled); isolate tests (function fixtures, independent data, no order dependence); stable locators (data-testid/role)
  - **Detect**: CI re-run statistics (flag tests that fail randomly at high frequency); failure-scene evidence (trace/screenshot/video); local reproduction (loop `--lf`)
  - **Stop the bleeding**: bounded retries (pytest-rerunfailures, `@pytest.mark.flaky(reruns=2)`, **cap retries at 1-2** — unlimited retries hide problems); quarantine (move known-flaky tests to a separate job that doesn't block the main pipeline — visible and tracked, just not in the way)
  - **Cure**: flaky is a bug to fix, not "just re-run it"; converge the quarantine list to zero over time
- **Interview answer structure**: definition in one sentence → three root-cause categories → four-step handling (prevent/detect/stop-the-bleeding/cure) → a real example (e.g. the saucedemo goto timeout); bonus words: retry caps, quarantine, trace forensics, test isolation

---

## 11. Learning Roadmap

- **The right way to "rebuild from memory"**: don't tear down the current project — start a new one, on a different site (the-internet.herokuapp.com, the classic practice site), and rebuild from scratch without copying old code (conftest + base_page + 2-3 pages + fixtures + split tests + report config), then compare decisions against the old project
- **Layer 1: finish saucedemo** — the checkout flow (three pages chained), the **cross-page assertion "total = sum of items"**, sort verification (zip pairwise comparison), negative cases (wrong password / locked_out_user), CSV/JSON data-driven tests
- **Layer 2: pytest depth** — fixture dependency chains and session scope, conftest directory layering (subdirectory overrides), real hooks (pytest_collection_modifyitems / pytest_runtest_makereport), pytest-rerunfailures, Allure
- **Layer 3: Playwright power moves (priority)**:
  - ⭐⭐⭐ **storage_state auth reuse (company standard; prerequisite for splitting tests)**:
    - **Background: Playwright's three-layer structure** — browser (the program) / context (an independent session, like an incognito window — **cookies live here**) / page (a tab). Auth state lives at the context layer, so saving/loading must operate on contexts; and the plugin's default page fixture never hands you the moment of context creation, so you work around it
    - **storage_state fixture = "issuing a pass"**: open a temporary context → walk through a real UI login (cookies land in this context) → `context.storage_state(path=...)` exports the auth state to JSON → close the temporary context → return the file path (session scope: one pass per session)
    - **browser_context_args fixture = "writing the pass into the door-opening recipe"**: the plugin calls it before creating each test's context to get the parameter dict; a same-name override of the plugin's original (the parameter with the same name refers to the original); `{**original_dict, "storage_state": path}` merges via dict unpacking (adding one auth-state ingredient); every test's page is then born authenticated
    - **`**` dict unpacking**: spreads a dict's key-value pairs into a new dict; later keys with the same name override earlier ones — the idiomatic Python way to merge dicts
    - Principle: log in once, `context.storage_state(path="auth.json")` saves cookies/localStorage to a file; inject it at new_context time; no more UI login
    - Standard implementation (two-piece conftest):

      ```python
      AUTH_FILE = "auth.json"

      @pytest.fixture(scope="session")
      def storage_state(browser) -> str:
          """Log in once and store the auth state; runs once per session"""
          context = browser.new_context()          # use the plugin's browser fixture, build your own context
          page = context.new_page()
          login = LoginPage(page)
          login.load()
          login.login(USERNAME, PASSWORD)
          context.storage_state(path=AUTH_FILE)     # store the auth state
          context.close()
          return AUTH_FILE

      @pytest.fixture(scope="session")
      def browser_context_args(browser_context_args, storage_state):
          """Official extension point: called before the plugin builds a context;
          injecting storage_state makes every test's page authenticated"""
          return {**browser_context_args, "storage_state": storage_state}
      ```

    - Afterwards, business fixtures drop the three login lines and go straight to `inventory.load()`; each test saves 3-5 seconds of UI login
    - Notes: ① auth.json is sensitive → gitignore it ② regenerate every session, so cookie expiry is a non-issue ③ parallel: one login per worker ④ fallback: if verify fails after load, the auth state expired — catch it in the fixture and re-login
    - Applicability: cookie/localStorage auth ✅; dynamic tokens / server-side sessions ❌ (use UI login or fetch a token via API)
  - ⭐⭐⭐ page.route network interception (mock APIs / slow networks / block images — UI tests independent of the backend)
  - ⭐⭐ waiting strategies (wait_for_response / expect_navigation), popups & multi-tabs (expect_page / dialog), upload & download (set_input_files)
  - ⭐ mobile emulation (--device), API+UI hybrid (APIRequestContext for data setup)
- **Layer 4: rebuild from memory on a new site**, one Playwright API per scenario (iframes/drag-and-drop/dynamic loading/file upload/popups/multi-window)
- Suggested pace: Layer 1 this week → fixture depth + storage_state next week → the-internet rebuild after that
- **Verifying download controls (the expect_download three layers)**:
  - Core: `page.expect_download()` — ⚠️ register it **before** the click (downloads can finish instantly); sync API: `with page.expect_download() as info:` → `download = info.value`
  - **L1 event happened**: expect_download didn't time out = the control really triggered a download
  - **L2 metadata**: `download.suggested_filename` (name), `download.save_as(tmp_path / "x.pdf")` (save into pytest's temp dir, auto-cleaned), `st_size > 0` (not empty)
  - **L3 content** (only when the file is a business deliverable): PDF magic bytes `f.read(4) == b"%PDF"` → pypdf page count / text extraction for business fields; CSV/JSON parsed with their modules
  - Traps: asynchronously generated files start at 0 bytes — assert size **after** `save_as()`; a page feedback signal (button disabled / toast) pairs with download verification as a double check
  - Fallback: if the download path is weird, drop to the network layer — `expect_response(lambda r: "pdf" in r.url)` and check status 200
  - Depth choice: L1+L2 is the company norm; L3 only for deliverable files (statements/contracts)
- **Three remaining gaps (to learn)**:
  - **Visual Testing**: the `pytest-playwright-visual` plugin — `assert.snapshot(page.screenshot())` compares against a baseline pixel-by-pixel; `mask=[locator]` excludes dynamic areas, `threshold` tunes tolerance, `--update-snapshots` refreshes baselines — a big-company UI standard
  - **CI/CD in practice**: GitHub Actions headless runs + secrets for credentials — wire the local framework into a pipeline
  - **Auth scenarios**: storage_state reuse (already listed in Layer 3 with a full implementation)

---

## 12. Command Cheat Sheet

### Running (selection & filtering)

| Command | Purpose |
|---|---|
| `pytest` | run all (per testpaths) |
| `pytest tests/test_cart.py` | one file |
| `pytest tests/test_cart.py::test_xxx` | one test |
| `pytest -k "cart"` | filter by name (substring, **case-sensitive**, supports and/or/not) |
| `pytest -k "cart and not remove"` | combined filter / negation |
| `pytest -m smoke` | filter by marker (register markers in pyproject first) |
| `pytest --collect-only` | collect without running (verify count/syntax) |

### Running (failure control & debugging)

| Command | Purpose |
|---|---|
| `pytest -x` | stop at first failure |
| `pytest --maxfail=3` | stop after 3 failures |
| `pytest --lf` | only last-failed (debugging hero) |
| `pytest --ff` | run failed first |
| `pytest -s` | don't swallow print output |
| `pytest -v` / `-q` | verbose / quiet |
| `pytest --durations=10` | show the slowest 10 tests |

### Running (Playwright-specific, pytest-playwright plugin)

| Command | Purpose |
|---|---|
| `pytest --headed` | headed mode (show the browser window) |
| `pytest --slowmo=500` | pause 500ms between actions |
| `pytest --browser=firefox` | switch browser (default chromium) |
| `pytest --browser-channel=chrome` | use the installed Chrome/Edge (msedge) |
| `pytest --device="iPhone 13"` | mobile viewport emulation |
| `pytest --screenshot=on / only-on-failure / off` | screenshots (only-on-failure recommended) |
| `pytest --video=on / retain-on-failure / off` | video (note: value names differ from screenshot!) |
| `pytest --tracing=on / retain-on-failure / off` | trace (retain-on-failure recommended, CI standard) |
| `pytest --output=artifacts/` | change the artifact dir (default test-results) |
| `pytest -n auto` | parallel (headless only, see section 9) |

### Reports

| Command | Purpose |
|---|---|
| `pytest --html=reports/report.html --self-contained-html` | HTML report (⚠️ don't write into test-results — Playwright deletes it) |
| `pytest --junitxml=test-results/junit.xml` | CI-standard XML report |
| `pytest --alluredir=results && allure serve results` | Allure report (heavy; big projects) |

### Inspection & tools

| Command | Purpose |
|---|---|
| `pytest --setup-plan` | show fixture plan without running |
| `pytest --setup-show` | show fixture SETUP/TEARDOWN while running |
| `pytest --trace-config` | show active plugins/config |
| `pytest --fixtures` | list all available fixtures |
| `playwright show-trace test-results` | open the trace time machine |
| `playwright codegen <URL>` | record actions into code / find locators |
| `playwright install chromium` | install Playwright's bundled browsers |

### Common workflow combinations

```bash
# Daily full run: default addopts already carry -v/report/trace
pytest

# Debugging: last-failed only + prints + headed slowed down
pytest --lf -s --headed --slowmo=500

# Feature development: cart-related only
pytest -k cart

# CI standard: headless + parallel + failure evidence + report
pytest -n auto --tracing=retain-on-failure --screenshot=only-on-failure \
       --junitxml=test-results/junit.xml
```

---

## Changelog

- 2026-09-12: initial version — first 12 Q&A rounds (pytest config, headed/headless, POM, locators, expect, tools, pitfalls)
- 2026-09-12: added expect-vs-assert, assertion placement, nested-DOM locators, assert messages, debugging ladder, fixtures basics, encapsulation principle, IDE-vs-runtime errors, TOML format, running & reports, pitfalls #8/#9/#10, pytest-html usage, flaky tests, learning roadmap
- 2026-09-12: correction — FileNotFoundError truth (pytest-playwright autouse fixture deletes test-results); exact=True semantics corrected against installed Playwright source
- 2026-09-13: added download verification, E2E splitting principles, storage_state full usage, fixture execution order, fixture Python mechanics, "fixtures don't run unless requested", AAA precondition fixturization, "remove the writing duplication, keep the running repetition"
- 2026-09-14: added redirect-type tests without bare assert, test file ownership rules, complete fixture extraction criteria, POM encapsulation interview phrasing, command cheat sheet
