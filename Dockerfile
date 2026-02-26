FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install firefox
RUN playwright install-deps firefox

COPY . .

CMD ["python3", "grailedbot2.py"]
