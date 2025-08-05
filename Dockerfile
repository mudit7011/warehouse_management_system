cat > Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads data/processed data/exports logs

# Use PORT environment variable that Render provides
ENV PORT=5000
EXPOSE $PORT

ENV FLASK_APP=src/part3_web_app/app.py
ENV FLASK_ENV=production

# Use gunicorn for production
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 run:app
EOF