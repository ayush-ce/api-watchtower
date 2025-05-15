from playwright.sync_api import sync_playwright

from tools.utils import CHUNK_SIZE, MAX_TOKENS, chunk_text, num_tokens_from_string

playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
page = browser.new_page()


def navigate_to_url(url):
    print(f"🌐 Navigating to: {url}")
    page.goto(url, wait_until="domcontentloaded")


def extract_text_from_browser():
    print(f"📄 Extracting text from: {page.url}")
    text = page.inner_text("body")
    total_tokens = num_tokens_from_string(text)
    print(f"🔢 Total tokens: {total_tokens}")

    if total_tokens > MAX_TOKENS:
        print("⚠️ Chunking large page")
        return {"text_chunks": chunk_text(text, CHUNK_SIZE), "chunked": True}
    return {"text_chunks": [text], "chunked": False}


def navigate_and_extract_text(url):
    print(f"🌐 Navigating to and extracting from: {url}")
    page.goto(url, wait_until="domcontentloaded")
    return extract_text_from_browser()


def extract_links_from_browser():
    print("🔗 Extracting links")
    return page.eval_on_selector_all("a", "elements => elements.map(el => el.href)")


def click_element_in_browser(selector):
    print(f"🖱️ Clicking on element: {selector}")
    try:
        page.click(selector, timeout=5000)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_elements(selector, attributes):
    print(f"🔍 Getting elements by selector: {selector} with attributes: {attributes}")
    script = f"""
        Array.from(document.querySelectorAll("{selector}")).map(el => {{
            return {{
                {', '.join([f'"{attr}": el.getAttribute("{attr}")' for attr in attributes])}
            }};
        }})
    """
    return page.evaluate(script)


def get_current_url():
    return page.url


def go_back():
    print("🔙 Going back to previous page")
    page.go_back()
