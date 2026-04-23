# 🦊 SARAh — AI Research Assistant

SARAh to aplikacja webowa zbudowana w Streamlit, która automatycznie przeszukuje internet, pobiera artykuły i generuje zwięzłe podsumowania przy użyciu modeli LLM od NVIDIA.

[![Demo SARAh](screenshots/task1/start.png)](https://github.com/user-attachments/assets/85b05c03-7722-4262-8ff8-a1ed433ab845)

## Funkcjonalności

- 🔍 Automatyczne wyszukiwanie źródeł przez DuckDuckGo
- 🌐 Scrapowanie stron z omijaniem zabezpieczeń (Playwright + Chromium)
- 🧠 Dwa modele LLM do wyboru: GLM-5.1 (głębokie) / Qwen3 (szybkie)
- ⚡ Cache wyników scrapowania i odpowiedzi LLM
- 📊 Panel analityczny z wykresami (kompresja tekstu, tokeny, czas AI)
- 📈 Zbieranie metryk produkcyjnych przez Prometheus + Grafana

## Uruchomienie

```bash
cp .env.example .env  # uzupełnij kluczami API
make up               # buduje i startuje wszystko
Serwis	Adres
SARAh	http://localhost:8501
Grafana	http://localhost:3000
Prometheus	http://localhost:9090
Stack
Frontend: Streamlit
Scraping: Playwright, Trafilatura
LLM: NVIDIA API (GLM-5.1, Qwen3)
Monitoring: Prometheus, Grafana
Infrastruktura: Docker, Docker Compose
```
