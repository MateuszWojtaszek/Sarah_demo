from ddgs import DDGS
import trafilatura
import requests
import time

from avoid_block import scrape_with_playwright


# Ustaw na True, by używać Playwrighta (wolniej, ale omija blokady)
# Ustaw na False, by używać Requests (szybciej, ale bardziej podatne na błędy 403)
USE_PLAYWRIGHT = True


def is_wikipedia_link(text):
    text = text.strip()
    return (
        text.startswith("http://") or text.startswith("https://")
    ) and "wikipedia.org" in text


def search_general_knowledge(query, max_results=25):
    # bez operatorów -site i -filetype, bo i tak czasmi nie dzialaly
    safe_query = f"{query} research paper"
    print(f"🔍 Szukam w sieci: '{safe_query}'...")
    bad_domains = ["scribd.com", "academia.edu", "researchgate.net"]
    links = []

    try:
        with DDGS() as ddgs:
            results = ddgs.text(safe_query, max_results=max_results, region="wt-wt")
            for result in results:
                url = result["href"]
                if any(bad_domain in url for bad_domain in bad_domains):
                    print(f" Odrzucam toksyczną domenę: {url}")
                    continue
                links.append(url)
                print(f" Znaleziono link: {result['href']}")
        return links
    except Exception as e:
        print(f"Błąd podczas wyszukiwania: {e}")
        return []


def scrape_standard(url):
    if url.endswith(".pdf"):
        print(f"Pomijam PDF: {url}")
        return None

    print(f"\n📥 [TRYB REQUEST] Pobieranie z: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f" Odmowa dostępu (Błąd {response.status_code}).")
            return None

        cleaned_text = trafilatura.extract(response.text)
        if cleaned_text:
            print(
                f" Sukces (REQUEST)! Pobrana długość tekstu: {len(cleaned_text)} znaków."
            )
            return cleaned_text
        return None
    except Exception as e:
        print(f" Błąd REQUEST: {e}")
        return None


# Dla przykladowego i testowego wywołania
if __name__ == "__main__":
    zapytanie_uzytkownika = "depression"

    zebrane_teksty = []
    znalezione_linki = []

    print("=" * 40)
    print(f" START PROCESU (Tryb PLAYWRIGHT: {USE_PLAYWRIGHT})")

    if is_wikipedia_link(zapytanie_uzytkownika):
        print(" Wykryto bezpośredni link. Pomijam wyszukiwarkę.")
        znalezione_linki.append(zapytanie_uzytkownika)

        # LOGIKA PRZEŁĄCZNIKA DLA WIKIPEDII
        if USE_PLAYWRIGHT:
            tekst = scrape_with_playwright(zapytanie_uzytkownika)
        else:
            tekst = scrape_standard(zapytanie_uzytkownika)

        if tekst:
            zebrane_teksty.append(tekst[:15000])

    else:
        print(" Wpisano temat badawczy. Uruchamiam DuckDuckGo...")
        wymagana_ilosc = 3
        znalezione_linki = search_general_knowledge(
            zapytanie_uzytkownika, max_results=25
        )

        for link in znalezione_linki:
            if len(zebrane_teksty) >= wymagana_ilosc:
                print(f"\n Zebrano wymagane {wymagana_ilosc} teksty. Przerywam.")
                break

            # LOGIKA PRZEŁĄCZNIKA DLA WYSZUKIWANIA
            if USE_PLAYWRIGHT:
                tekst = scrape_with_playwright(link)
            else:
                tekst = scrape_standard(link)

            if tekst:
                if len(tekst) < 3000:
                    print(f" ODRZUCAM: Tekst za krótki ({len(tekst)} znaków).")
                    continue

                blacklist = [
                    "Ray ID",
                    "security check",
                    "Cloudflare",
                    "unusual activity",
                ]
                if any(bad_word in tekst for bad_word in blacklist):
                    print(" Wykryto antybot (Cloudflare/Captcha).")
                    continue

                print(" ZAAKCEPTOWANO źródło.")
                zebrane_teksty.append(tekst[:10000])

            time.sleep(1.5)

    połączony_tekst = "\n\n--- NASTĘPNE ŹRÓDŁO ---\n\n".join(zebrane_teksty)

    print("\n" + "=" * 40)
    print("PODSUMOWANIE")
    print(f"Pobrano artykułów: {len(zebrane_teksty)}")
    print(f"Całkowita liczba znaków dla LLM: {len(połączony_tekst)}")

    if połączony_tekst:
        print("\nPróbka tekstu:")
        print(połączony_tekst[:300] + "...\n")
