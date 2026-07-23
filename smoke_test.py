from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    page.goto("https://2048game.online/")
    page.wait_for_timeout(2000)

    print("=== PAGE TITLE ===")
    print(page.title())

    print("=== localStorage KEYS (before move) ===")
    print(page.evaluate("() => Object.keys(localStorage)"))

    page.keyboard.press("ArrowUp")
    page.wait_for_timeout(1000)

    print("=== localStorage KEYS (after move) ===")
    print(page.evaluate("() => Object.keys(localStorage)"))

    print("=== localStorage gameState ===")
    try:
        print(page.evaluate("() => localStorage.getItem('gameState')"))
    except Exception as e:
        print(f"Error reading gameState: {e}")

    print("=== .tile-container outerHTML ===")
    try:
        print(page.locator(".tile-container").first.evaluate("el => el.outerHTML"))
    except Exception as e:
        print(f"Error reading .tile-container: {e}")

    page.wait_for_timeout(3000)
    browser.close()
