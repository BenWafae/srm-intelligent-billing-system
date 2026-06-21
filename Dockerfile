FROM python:3.10.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=1000 -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python init_admin.py && uvicorn main:app --host 0.0.0.0 --port 8000"]
