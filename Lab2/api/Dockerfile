FROM python:3.13-slim

WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn

COPY main.py /app/main.py

ENV DB_PATH=/data/shop.db

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
