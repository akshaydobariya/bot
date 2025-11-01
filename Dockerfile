# Delta Exchange Trading Bot Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY run.py .

# Create necessary directories
RUN mkdir -p data logs

# Create non-root user for security
RUN groupadd -r trading && useradd -r -g trading trading
RUN chown -R trading:trading /app
USER trading

# Set web mode for cloud deployment
ENV WEB_MODE=true
ENV PORT=8000

# Set required environment variables with defaults
ENV JWT_SECRET_KEY=delta_exchange_trading_bot_jwt_secret_key_32_characters_minimum_for_security
ENV ENCRYPTION_KEY=delta_exchange_bot_encryption_key
ENV DATABASE_URL=sqlite:///data/trading_bot.db
ENV ENVIRONMENT=production
ENV DEFAULT_SYMBOL=BTCUSD
ENV RISK_PERCENTAGE=1.0
ENV STOP_LOSS_PERCENTAGE=2.0
ENV TAKE_PROFIT_PERCENTAGE=3.0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8000

# Run the bot in web mode
CMD ["python", "run.py"]