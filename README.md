# Playwright Practice

UI automation practice project for [Sauce Demo](https://www.saucedemo.com/), built with **Python + pytest + Playwright**.

## Tech Stack

- Python 3.12
- pytest 9 + pytest-playwright
- pytest-html (reports) + pytest-xdist (parallel execution)

## Project Structure

```
├── conftest.py              # Shared fixtures: login, storage_state (auth reuse)
├── pyproject.toml           # pytest config: addopts, markers, report path
├── pages/                   # Page Object layer (locators live here, never in tests)
│   ├── base_page.py
│   ├── login_page.py
│   ├── inventory_page.py
│   ├── inventory_item_page.py
│   ├── cart_page.py
│   ├── checkout_step_one_page.py
│   ├── checkout_step_two_page.py
│   └── checkout_complete_page.py
└── tests/                   # Test layer (business assertions only)
    ├── test_inventory.py
    ├── test_product_detail.py
    ├── test_cart.py
    └── test_checkout.py     # E2E main flow
```

## Design Highlights

- **Page Object Model** — locators are encapsulated in page classes; tests express business intent only
- **Fixture layering** — `storage_state` fixture logs in once per session and reuses the auth state, so every test skips UI login
- **Test organization** — one test verifies one thing; parametrized tests for multiple products; `smoke` / `regression` markers
- **Failure evidence** — HTML report + trace / screenshot / video retained on failure
- **E2E main flow** — full checkout journey including price breakdown and PDF download verification

## Setup

```bash
pip install pytest playwright pytest-playwright pytest-html pytest-xdist
playwright install chromium
```

## Run Tests

```bash
pytest                  # run all (headed off by default, see pyproject addopts)
pytest -k cart          # filter by test name
pytest -m smoke         # run smoke layer only
pytest --headed --slowmo=500   # watch the browser, slowed down
pytest -n 2             # parallel execution (headless)
```

Reports: `reports/report.html` · Failure traces: `test-results/` (open with `playwright show-trace test-results`)

## How I Learned This — AI-Assisted Learning, Replicable Workflow

**Why:** I wanted to learn Playwright *properly* — page objects, fixtures, reports, trace, engineering practices. Most quality video courses, especially from abroad, are expensive. So I tried a different path: **a real project + a real-time AI dialogue**, learning iteratively instead of watching.

**The method** (this is the whole trick):

1. **Start with a real target, not a tutorial.** Pick a site built for test practice (this one: saucedemo.com). A real project generates real errors — and real errors are the best teachers.
2. **Start minimal.** One test, one assertion (open a page, check the title). Green in 10 minutes.
3. **Learn through errors.** Run → fail → ask the AI *why* → understand the principle → **fix it yourself** → re-run. The AI diagnoses; you always type the fix.
4. **Ask "why" at every turn.** Every API choice is a chance to dig into the principle: Why `expect` and not `assert`? What is an "accessible name"? How do fixtures really work (decorator + registry)? Each answer becomes a note.
5. **Keep a living knowledge base.** After each concept, the AI maintains a bullet+example notes file — and every future Q&A gets appended to it. The knowledge accumulates in a document, not in chat history: [playwright-notes.md](docs/playwright-notes.md) (中文) / [playwright-notes-en.md](docs/playwright-notes-en.md) (English).
6. **Iterate in layers.** Page Objects → fixtures → storage_state auth reuse → reports/trace → test splitting → parallel → engineering practices (privacy, flaky handling). Each layer is driven by a real need, not a syllabus.
7. **Do exercises that force understanding.** Intentional bug hunts with the trace viewer, a test-splitting refactor, code reviews with the AI. Watching is passive; fixing a deliberately planted bug is not.
8. **Turn it into interview material.** Concepts get distilled into English one-liners and answer structures as you learn them.

**Key principles that made it work:**

- **The learner drives.** The AI never fixes for you unless asked — you write the code, you configure, you split the tests.
- **Fix it yourself.** Understanding comes from typing the fix, not from watching it being fixed.
- **Notes are long-term assets.** The doc is the product; the conversation is just the workshop.
- **A real project beats videos.** Every concept here was learned because a real failure demanded it.

Total journey to this repo: a few days of part-time practice, zero video hours, ~12 sections of accumulated notes. If it worked for me, it can work for you — pick any framework, pick a practice site, and start with one test.
