# ---- Builder Stage ----
FROM python:3.12-alpine AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Final Stage ----
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Create a non-root user
RUN addgroup -S afmw && adduser -S afmw -G afmw

# Copy only the installed Python dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Set permissions and create necessary directories
RUN mkdir -p logs && chown -R afmw:afmw /app

# Switch to the non-root user
USER afmw
