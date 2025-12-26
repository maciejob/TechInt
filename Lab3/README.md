# Lab3 – Blog z komentarzami i moderacją

Aplikacja składa się z:
- **Backendu API** napisanego w **FastAPI (Python)**
- **Frontend UI** w postaci statycznej strony **HTML + JavaScript**
- **Bazy danych SQLite**, przechowywanej lokalnie (poza kontenerem)

Całość uruchamiana jest przy użyciu **Docker Compose**.

## Wymagania systemowe

### Oprogramowanie
- **Docker Engine** ≥ 24
- **Docker Compose plugin**
- Przeglądarka internetowa

## Instrukcja uruchomienia

W katalogu Projektu wykonać polecenie:
docker compose up -d --build

## Dostęp do aplikacji

Interfejs użytkownika (UI):
http://localhost:8082

Backend API:
http://localhost:8002/api

##Zatrzymanie aplikacji

docker compose down

