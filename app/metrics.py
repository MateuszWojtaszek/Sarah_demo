import streamlit as st
from prometheus_client import Counter, Gauge, start_http_server


@st.cache_resource
def _init():
    start_http_server(8000)  # dla prometheusa
    return {
        "queries": Counter("sarah_queries_total", "Liczba zapytań do Sarah"),
        "cache_hits": Counter(
            "sarah_cache_hits_total", "Zapytania obsłużone z cache LLM"
        ),
        "scrape_errors": Counter(
            "sarah_scrape_errors_total", "Błędy scrapowania (blokady, błędy 403)"
        ),
        "llm_last_duration": Gauge(
            "sarah_llm_last_duration_seconds",
            "Czas ostatniej odpowiedzi LLM w sekundach",
        ),
        "tokens_total": Counter(
            "sarah_tokens_total",
            "Szacowana łączna liczba przetworzonych tokenów",
        ),
    }


metrics = _init()
