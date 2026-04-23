# Plik: app/avoid_block.py
import trafilatura
from playwright.sync_api import sync_playwright


def scrape_with_playwright(url):
    """
    Funkcja pobierająca tekst za pomocą niewidocznej przeglądarki Chromium.
    Służy do omijania zaawansowanych blokad (Cloudflare, paywalle).
    """
    if url.endswith(".pdf"):
        print(f"  ⚠️ Pomijam PDF: {url}")
        return None

    print(f"\n📥 [TRYB PLAYWRIGHT] Uruchamiam przeglądarkę dla: {url}")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = context.new_page()
            page.goto(url, timeout=15000)

            html_content = page.content()
            browser.close()

            cleaned_text = trafilatura.extract(html_content)

            if cleaned_text:
                print(
                    f"  Sukces (PLAYWRIGHT)! Pobrana długość tekstu: {len(cleaned_text)} znaków."
                )
                return cleaned_text
            else:
                print(" Pusty tekst. Strona mogła ukryć treść.")
                return None

        except Exception as e:
            print(f"  Tryb PLAYWRIGHT natrafił na błąd: {e}")
            return None
