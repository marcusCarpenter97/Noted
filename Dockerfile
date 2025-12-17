FROM python:3.12

WORKDIR /app

COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt

COPY src app/Noted

ENV PYTHONPATH=/app
ENV DB_PATH=/data/database.db

# CMD ["python", "cli.py"]
