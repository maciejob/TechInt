# Lab1 – Wypożyczalnia książek

## Opis
Projekt **Lab1** to prosta aplikacja typu klient–serwer realizująca funkcjonalność wypożyczalni książek.

Aplikacja składa się z:
- **Backendu API** napisanego w **FastAPI (Python)**  
- **Frontend UI** w postaci statycznej strony **HTML + JavaScript**
- **Bazy danych SQLite**, przechowywanej lokalnie (poza kontenerem)

Całość uruchamiana jest przy użyciu **Docker Compose**.


---

## Funkcjonalności
- Dodawanie członków wypożyczalni (unikalny email)
- Dodawanie książek (autor, tytuł, liczba egzemplarzy)
- Wypożyczanie książek
- Zwracanie książek
- Lista aktualnych i historycznych wypożyczeń
- Walidacja:
  - brak dostępnych egzemplarzy → błąd `409`
  - próba ponownego zwrotu → błąd `409`

---

## Wymagania systemowe

- **Docker Engine** ≥ 24
- **Docker Compose plugin** (docker compose)
- Przeglądarka internetowa

> Nie jest wymagane lokalne instalowanie Pythona ani bibliotek – wszystko działa w kontenerach.

---

## Struktura katalogów

Lab1/
├── api/
│ ├── Dockerfile
│ └── main.py
├── ui/
│ └── index.html
├── db/
│ └── library.db # tworzona automatycznie przy pierwszym uruchomieniu
├── docker-compose.yml
└── README.md

---

## Instrukcja uruchomienia

W katalogu z projektem wykonać: 
docker compose up -d --build


## Dostęp do aplikacji

Po uruchomieniu:

Interfejs użytkownika (UI):
http://localhost:8080

Backend API:
http://localhost:8000/api





