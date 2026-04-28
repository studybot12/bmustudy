FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE $PORT

CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 wsgi:app
