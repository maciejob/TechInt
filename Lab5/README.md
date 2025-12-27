# Lab5 – Kanban

## Opis
Projekt **Lab5** to prosta tablica **Kanban**, umożliwiająca zarządzanie zadaniami
w trzech predefiniowanych kolumnach:
- **Todo**
- **Doing**
- **Done**

Aplikacja pozwala na:
- dodawanie zadań,
- przypisywanie zadań do kolumn,
- przenoszenie zadań pomiędzy kolumnami,
- zachowanie kolejności zadań w kolumnach (`ord`).

Aplikacja składa się z:
- **Backendu API** napisanego w **FastAPI (Python)**  
- **Frontend UI** w postaci statycznej strony **HTML + JavaScript**
- **Bazy danych SQLite**, przechowywanej lokalnie (poza kontenerem)

## Wymagania systemowe

- **Docker Engine** ≥ 24
- **Docker Compose plugin**
- Przeglądarka internetowa

## Uruchomienie aplikacji

docker compose up -d --build

Interfejs użytkownika (UI):
http://localhost:8084

Backend API:
http://localhost:8004/api

## Zatrzymanie aplikacji

docker compose down

## Reset Danych

Usunąć plik db/kanban.db


