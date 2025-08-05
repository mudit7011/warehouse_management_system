
FROM python:3.9-slim

WORKDIR /app


RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads data/processed data/exports logs

ENV FLASK_APP=src/part3_web_app/app.py
ENV FLASK_ENV=production

EXPOSE 5001

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]