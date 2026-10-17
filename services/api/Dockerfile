FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/app
COPY app ./app
ENV FORTE_PORT=8000
EXPOSE 8000
CMD ["python3", "-m", "app.main"]
