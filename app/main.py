import streamlit as st
import os
import re
import time
import pandas as pd
import urllib.parse
import altair as alt  # do czytelniejszych wykresów

from scraper import (
    is_wikipedia_link,
    search_general_knowledge,
    scrape_standard,  # standardowe czyszczenie
)
from avoid_block import (
    scrape_with_playwright,
)  # zrobione jako dodatek w ramach wykorzystywania w przyszłości w projekcie SARAh w kole naukowym KNKonar Konar
from llm import generate_summary_stream
from metrics import metrics

# Konfiguracja strony
st.set_page_config(
    page_title="Sarah — Researcher",
    page_icon="app/images/icon.jpg",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# SYSTEM cache
# Cache dla DuckDuckGo (Zapamiętuje linki na 24h)
@st.cache_data(show_spinner=False, ttl=86400)
def cached_search(query, max_results=30):
    return search_general_knowledge(query, max_results)


# Cache dla Scrapowania Playwrightem
@st.cache_data(show_spinner=False, ttl=86400)
def cached_scrape_playwright(url):
    return scrape_with_playwright(url)


# Ręczny słownik Cache dla modelu LLM
@st.cache_resource
def get_llm_cache():
    return {}


def load_local_css(file_name):
    try:
        with open(file_name, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"Nie znaleziono pliku CSS: {file_name}")


load_local_css(
    "app/style.css"
)  # CSS równiez zrobiony do uzywania w Projekcie Sarah w kole

if "llm_times" not in st.session_state:
    st.session_state.llm_times = []
if "query_input" not in st.session_state:
    st.session_state.query_input = ""

IMG_IDLE = "app/images/sarah.png"
IMG_SEARCH = "app/images/sarah_search.png"
IMG_THINK = "app/images/sarah_think2.gif"
IMG_DONE = "app/images/sarah_done.png"


def show_avatar(
    img_spot, caption_spot, badge_spot, img_path, caption, badge_html, phase=""
):
    """
    Funkcja odpowiadająca za wyświetlanie Avatarów SARAh poczas przywiatani,
    przeglądania internetu, myślenia i skończenia zadania
    """
    if os.path.exists(img_path):
        img_spot.image(img_path)
    else:  # gdyby nie bylo obrazka z jakiegos powodu to lisek
        img_spot.markdown(
            f'<div style="font-size:80px;text-align:center;padding:16px">🦊</div>',
            unsafe_allow_html=True,
        )

    if phase in ["searching", "thinking"]:
        st.markdown(  # animacja pulsowania
            "<style>div[data-testid='stImage'] img { animation: pandaPulse 1.2s ease-in-out infinite !important; }</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<style>div[data-testid='stImage'] img { animation: none !important; }</style>",
            unsafe_allow_html=True,
        )
    # Podpisy pod avatarem
    badge_spot.markdown(
        f'<div style="display:flex;justify-content:center;margin-top:8px"><span class="sarah-badge {badge_html[0]}">{badge_html[1]}</span></div>',
        unsafe_allow_html=True,
    )
    caption_spot.markdown(
        f'<div class="sarah-caption">{caption}</div>', unsafe_allow_html=True
    )


def show_welcome():
    """
    Główny Kod aplikacji, słózy do wyswietlania strony, obslugi zapytan i ukazywania metryk
    """
    st.markdown(
        """
    <div class="sarah-header">
        <div class="sarah-eyebrow">Twój asystent badań</div>
        <h1 class="sarah-title">Cześć, tu <em>SARAh</em>!</h1>
        <div class="sarah-sub">Co chciałbyś dzisiaj zbadać?</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    # podzial strony na kolumny 1|2
    col_avatar, col_input = st.columns([1, 2], gap="large")

    with col_avatar:
        img_spot = st.empty()
        badge_spot = st.empty()
        caption_spot = st.empty()
        progress_spot = st.empty()

        show_avatar(
            img_spot,
            caption_spot,
            badge_spot,
            IMG_IDLE,
            "Jestem gotowa, podaj temat!",
            ("", "🦊 Gotowa"),
            "idle",
        )

    with col_input:
        st.markdown(
            '<div class="section-label">Temat lub link do zbadania</div>',
            unsafe_allow_html=True,
        )

        user_query = st.text_input(
            label="query",
            label_visibility="collapsed",
            placeholder="np. Informatyka Afektywna",  # (;
            value=st.session_state.query_input,
            key="main_query_field",
        )

        st.markdown(
            '<div class="section-label" style="margin-top:14px">Poziom rozumowania</div>',
            unsafe_allow_html=True,
        )
        # mozliwosc wyboru modelu
        model_choice = st.radio(
            label="model_choice",
            label_visibility="collapsed",
            options=["high", "fast"],
            format_func=lambda x: (
                "🧠 Głębokie (GLM-5.1)" if x == "high" else "⚡ Szybkie (Qwen3)"
            ),
            horizontal=True,
            key="model_choice_radio",
        )

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        ask_clicked = st.button("Zapytaj Sarah →", use_container_width=True)

    st.markdown("<hr class='panda-sep'>", unsafe_allow_html=True)

    if ask_clicked:
        if not user_query or not user_query.strip():
            st.info("✏️ Napisz coś powyżej, żebym mogła zacząć działać.")
            return

        # scrapowanie
        show_avatar(
            img_spot,
            caption_spot,
            badge_spot,
            IMG_SEARCH,
            "🔍 Przeszukuję sieć...",
            ("badge-searching", "🔍 Szukam"),
            "searching",
        )
        # progress progressbara
        pb = progress_spot.progress(10)

        metrics["queries"].inc()
        zebrane_zrodla = []
        bledy_pobierania = 0

        if is_wikipedia_link(user_query):
            pb.progress(30)
            # Użycie funkcji z Cache
            tekst = cached_scrape_playwright(user_query)
            if tekst:
                zebrane_zrodla.append(
                    {"url": user_query, "tekst": tekst[:15000], "znaki": len(tekst)}
                )
            pb.progress(60)
        else:
            # Użycie funkcji z Cache
            znalezione_linki = cached_search(user_query, max_results=30)
            wymagana_ilosc = 3
            aktualny_postep = 10

            # przyrost paska postępu
            # Progress bar ma zakres 10→50 (czyli 40 jednostek) dla fazy scrapowania.
            krok = 40 / (len(znalezione_linki) if znalezione_linki else 1)

            for link in znalezione_linki:
                if len(zebrane_zrodla) >= wymagana_ilosc:
                    break

                pb.progress(min(int(aktualny_postep), 60))

                # Użycie funkcji z Cache
                tekst = (
                    None
                    if link.lower().endswith(".pdf")
                    else cached_scrape_playwright(link)
                )

                # > 3000 aby odrzucic krotkie np. Abstrakty
                if tekst and len(tekst) > 3000:
                    # jesli bylby to tekst z jakiejs kontroli np. Claudflare
                    # lista tworzona w trakcie analizy scrapowanych rzeczy
                    blacklist = [
                        "Ray ID",
                        "security check",
                        "Cloudflare",
                        "unusual activity",
                    ]
                    if not any(word in tekst for word in blacklist):
                        # limit tekstu aby nie zawalic LLM
                        zebrane_zrodla.append(
                            {"url": link, "tekst": tekst[:10000], "znaki": len(tekst)}
                        )
                    else:
                        bledy_pobierania += 1
                        metrics["scrape_errors"].inc()
                else:
                    bledy_pobierania += 1
                    metrics["scrape_errors"].inc()

                aktualny_postep += krok
                # celowe spowolnienie scrapowania, żeby nie wysyłać requestów do stron zbyt szybko jeden po drugim.
                # time.sleep(1) przy cache jest zbedny

        polaczony_tekst = "\n\n".join(
            [
                f"--- ŹRÓDŁO {i + 1}: {z['url']} ---\n{z['tekst']}"
                for i, z in enumerate(zebrane_zrodla)
            ]
        )
        if not polaczony_tekst:
            st.error(
                "Nie udało mi się pobrać wartościowych materiałów. Spróbuj zmodyfikować zapytanie."
            )
            return

        # LLM
        show_avatar(
            img_spot,
            caption_spot,
            badge_spot,
            IMG_THINK,
            "Generuję podsumowanie...",
            ("badge-thinking", "🧠 Myślę"),
            "thinking",
        )

        pb.progress(75)

        llm_start = time.time()
        reasoning_expander = st.expander(
            "🧠 Zobacz, jak Sarah analizuje te źródła (Reasoning)",
            expanded=True,
        )
        reasoning_placeholder = reasoning_expander.empty()

        st.markdown(
            '<div class="result-header" style="margin-bottom: 16px;"><span class="result-panda">🦊</span><span class="result-name">Sarah</span><span class="result-tag" style="background: oklch(90% 0.10 60 / 0.40); color: oklch(42% 0.18 50);">Piszę...</span></div>',
            unsafe_allow_html=True,
        )

        result_text_area = st.empty()

        proces_myslowy_full = ""
        podsumowanie_full = ""
        uzyto_cache = False

        # Inicjalizacja słownika Cache dla LLM
        llm_cache = get_llm_cache()
        cache_key = f"{user_query.strip().lower()}_{model_choice}"

        if cache_key in llm_cache:
            # Omijam API i ładuje z pamięci
            uzyto_cache = True
            metrics["cache_hits"].inc()
            proces_myslowy_full = llm_cache[cache_key]["reasoning"]
            podsumowanie_full = llm_cache[cache_key]["content"]

            if proces_myslowy_full:
                reasoning_placeholder.info(proces_myslowy_full)

            # Obsługa stremingu tekstu " ▌" na końcu to animowany kursor (tu dla spójności UI)
            result_text_area.markdown(podsumowanie_full + " ▌")
            time.sleep(0.3)

        else:
            # Standardowe generowanie
            for typ_tekstu, fragment in generate_summary_stream(
                user_query, polaczony_tekst, model_choice
            ):
                if typ_tekstu == "error":
                    st.error(fragment)
                    break
                elif typ_tekstu == "reasoning":
                    proces_myslowy_full += fragment
                    reasoning_placeholder.info(proces_myslowy_full + " ▌")
                elif typ_tekstu == "content":
                    podsumowanie_full += fragment
                    result_text_area.markdown(podsumowanie_full + " ▌")

            # do Cache na przyszłość
            if not "Wystąpił błąd LLM" in podsumowanie_full:
                llm_cache[cache_key] = {
                    "reasoning": proces_myslowy_full,
                    "content": podsumowanie_full,
                }

        llm_end = time.time()  # koniec mierzenia czasu odp, wyzej byl start
        czas_llm = round(llm_end - llm_start, 2)
        st.session_state.llm_times.append(czas_llm)
        metrics["llm_last_duration"].set(czas_llm)

        if proces_myslowy_full:
            reasoning_placeholder.info(proces_myslowy_full)

        # LLM czasami zwracal odp owiniete w code fence czyli ```markdown...
        podsumowanie_clean = re.sub(r"^```[a-zA-Z]*\n?", "", podsumowanie_full.strip())
        podsumowanie_clean = re.sub(r"\n?```$", "", podsumowanie_clean).strip()

        result_text_area.markdown(podsumowanie_clean)
        metrics["tokens_total"].inc(
            (len(polaczony_tekst) + len(podsumowanie_clean)) // 4
        )

        czas_label = f"⏱️ Czas AI: {czas_llm}s" + (" (⚡ CACHE)" if uzyto_cache else "")

        st.markdown(
            f"""
        <div class="result-chips-row" style="margin-top:24px; margin-bottom:24px;">
            <span class="result-chip">📚 Źródła: {len(zebrane_zrodla)}</span>
            <span class="result-chip">{czas_label}</span>
            <span class="result-chip">📄 Znaki wejściowe: {len(polaczony_tekst)}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # koniec przetwarzania
        pb.progress(100)
        show_avatar(
            img_spot,
            caption_spot,
            badge_spot,
            IMG_DONE,
            "Mam to dla Ciebie!",
            ("badge-done", "✅ Gotowe"),
            "done",
        )
        time.sleep(1)  # aby progress bar nie zniknal odrazu
        progress_spot.empty()

        # statystyki i wykresy
        ilosc_slow_zrodlo = len(polaczony_tekst) // 6  # przyblizenie slow po polsku
        czas_czytania_czlowiek = max(1, ilosc_slow_zrodlo // 200)
        kompresja = min(
            99,  # 99 to cap aby przypadkiem nie mylic ze redukcja jest 100%
            round((1 - (len(podsumowanie_clean) / max(len(polaczony_tekst), 1))) * 100),
        )

        st.markdown("""<div style="margin-top: 40px;"></div>""", unsafe_allow_html=True)
        st.markdown("### 📊 Panel Analityczny Sarah")
        st.markdown("---")

        k1, k2, k3 = st.columns(3)
        with k1:
            st.metric(
                label="⏳ Twój zaoszczędzony czas",
                value=f"{czas_czytania_czlowiek} min",
                delta="Przewidywany czas czytania",
            )
        with k2:
            st.metric(
                label="🗜️ Redukcja materiału",
                value=f"{kompresja}%",
                delta="Usunięto zbędny tekst",
                delta_color="normal",
            )
        with k3:
            st.metric(
                label="⚡ Czas analizy AI",
                value=f"{czas_llm} s",
                delta="Z PAMIĘCI (CACHE)" if uzyto_cache else model_choice.upper(),
                delta_color="normal" if uzyto_cache else "off",
            )

        # color -> szybka poprawka widocznosci tekstu
        st.markdown(
            """
        <div style="color: oklch(44% 0.06 40); font-size: 13px; margin-top: 10px;">
            * Szacowany czas czytania zebranych źródeł przez człowieka przy tempie 200 słów/minutę.<br>
            ** O ile procentowo krótsze jest wygenerowane podsumowanie względem surowych materiałów źródłowych.
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # wykresy
        col1, col2 = st.columns(2)

        with col1:
            # Kompresja
            st.markdown("#### 📏 Kompresja tekstu")
            st.caption(
                "Ilość znaków w pobranych źródłach w porównaniu do podsumowania:"
            )

            df_compare = pd.DataFrame(
                {
                    "Rodzaj tekstu": ["Źródła (oryginał)", "Podsumowanie AI"],
                    "Znaków": [len(polaczony_tekst), len(podsumowanie_clean)],
                }
            )

            # poziomy bar chart
            chart_compare = (
                alt.Chart(df_compare)
                .mark_bar(color="#7b5ea7", cornerRadiusEnd=4)
                .encode(
                    x=alt.X("Znaków:Q", title="Liczba znaków"),
                    y=alt.Y(
                        "Rodzaj tekstu:N",
                        title=None,
                        sort="-x",
                        axis=alt.Axis(labelAngle=0),
                    ),  # labelAngle=0 to poziome napisy
                )
                .properties(height=250)
            )
            st.altair_chart(chart_compare, use_container_width=True)

            # tokeny
            st.markdown("#### 🪙 Zużycie tokenów (Szacunek)")
            st.caption("Przybliżona ilość tokenów przetworzona przez serwery NVIDIA:")

            df_tokens = pd.DataFrame(
                {
                    "Strumień": ["Wejście (Prompt)", "Wyjście (Odpowiedź)"],
                    "Ilość Tokenów": [
                        # przyblizone bo api nie daje, chce pokazac tylko roznice pomiedzy wplywem wejsca a wyjscia
                        len(polaczony_tekst) // 4,
                        len(podsumowanie_clean) // 4,
                    ],
                }
            )

            chart_tokens = (
                alt.Chart(df_tokens)
                .mark_bar(color="#e56b3b", cornerRadiusEnd=4)
                .encode(
                    x=alt.X("Ilość Tokenów:Q", title="Szacowane tokeny"),
                    y=alt.Y(
                        "Strumień:N", title=None, sort="-x", axis=alt.Axis(labelAngle=0)
                    ),
                )
                .properties(height=250)
            )
            st.altair_chart(chart_tokens, use_container_width=True)

        with col2:
            # Czas
            st.markdown("#### ⏱️ Historia prędkości LLM")
            st.caption("Czas reakcji modelu (w sekundach) w trakcie obecnej sesji:")

            if len(st.session_state.llm_times) > 0:
                # numer zapytania (Oś X) dla lepszej orientacji
                df_time = pd.DataFrame(
                    {
                        "Zapytanie": range(1, len(st.session_state.llm_times) + 1),
                        "Sekundy": st.session_state.llm_times,
                    }
                )

                # mark_line(point=True) - wymusza rysowanie kropki nawet dla 1 punktu
                chart_time = (
                    alt.Chart(df_time)
                    .mark_line(
                        point=alt.OverlayMarkDef(filled=False, fill="white", size=60),
                        color="#3d8258",
                    )
                    .encode(
                        x=alt.X(
                            "Zapytanie:O",
                            title="Numer zapytania",
                            axis=alt.Axis(labelAngle=0),
                        ),
                        y=alt.Y("Sekundy:Q", title="Czas (s)"),
                        tooltip=[
                            "Zapytanie",
                            "Sekundy",
                        ],  # ładny dymek po najechaniu myszką
                    )
                    .properties(height=250)
                )
                st.altair_chart(chart_time, use_container_width=True)

            # scrapowanie
            st.markdown("#### 🕸️ Skuteczność Scrapowania")
            st.caption(
                "Rozkład linków zaakceptowanych vs odrzuconych (błędy/paywalle):"
            )

            df_scrape = pd.DataFrame(
                {
                    "Status": ["Pobrano (Sukces)", "Odrzucono (Blokada)"],
                    "Liczba": [len(zebrane_zrodla), bledy_pobierania],
                }
            )

            chart_scrape = (
                alt.Chart(df_scrape)
                .mark_bar(color="#4a7fa5", cornerRadiusEnd=4)
                .encode(
                    x=alt.X("Liczba:Q", title="Ilość linków"),
                    y=alt.Y("Status:N", title=None, axis=alt.Axis(labelAngle=0)),
                )
                .properties(height=250)
            )
            st.altair_chart(chart_scrape, use_container_width=True)

        # Lista linków na dole
        st.markdown("### 📚 Bibliografia")
        for i, zrodlo in enumerate(zebrane_zrodla):
            domena = urllib.parse.urlparse(zrodlo["url"]).netloc.replace("www.", "")
            st.markdown(
                f"**{i + 1}. {domena}** 🔗 [Otwórz artykuł]({zrodlo['url']}) (Pobrano: {zrodlo['znaki']} znaków)"
            )


if __name__ == "__main__":
    show_welcome()
