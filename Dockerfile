FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

COPY start.sh .
RUN chmod +x start.sh

CMD ["/bin/sh", "start.sh"]
