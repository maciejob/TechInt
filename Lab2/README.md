# Lab2 – Sklep: koszyk i zamówienia

## Opis
Projekt **Lab2** to prosta aplikacja typu sklep internetowy realizująca:
- zarządzanie produktami,
- obsługę koszyka,
- składanie zamówień.

Aplikacja składa się z:
- **Backendu API** napisanego w **FastAPI (Python)**  
- **Frontend UI** w postaci statycznej strony **HTML + JavaScript**
- **Bazy danych SQLite**, przechowywanej lokalnie (poza kontenerem)

Całość uruchamiana jest przy użyciu **Docker Compose**.


## Wymagania systemowe

- **Docker Engine** ≥ 24
- **Docker Compose plugin**
- Przeglądarka internetowa

## Instrukcja uruchomienia

W katalogu projektu wykonać polecenie:
docker compose up -d --build

Po uruchomieniu:

Interfejs użytkownika (UI):
http://localhost:8081

Backend API:
http://localhost:8001/api

##Zatrzymanie aplikacji

docker compose down