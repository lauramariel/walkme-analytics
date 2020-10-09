FROM python:3.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install wheel && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
COPY . .

ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0 --log-level=debug"

CMD ["gunicorn", "main:app"]