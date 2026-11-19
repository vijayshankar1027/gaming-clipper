FROM python:3.10-slim

# System updates and FFmpeg installation
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-liberation \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Ensure working directories exist with write permissions
RUN mkdir -p outputs temp models && chmod -R 777 outputs temp models

# Default port for Render is 10000 (handled via $PORT in app.py)
ENV PORT=10000
EXPOSE 10000

CMD ["python", "app.py"]
