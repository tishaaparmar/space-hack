# Use Ubuntu 22.04 as specified by the PS requirements
FROM ubuntu:22.04

# Prevent interactive prompts during apt installations
ENV DEBIAN_FRONTEND=noninteractive

# Update system and install Python 3.10 and curl
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x (required for Next.js 14+)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy and install python dependencies
COPY backend/requirements.txt /app/backend/
# Add requests and sgp4 for the data ingest scripts
RUN pip3 install --no-cache-dir requests sgp4 -r /app/backend/requirements.txt

# Copy and install JS dependencies
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm ci --legacy-peer-deps

# Copy the entire workspace into the container
WORKDIR /app
COPY . /app/

# Build the Next.js app for production performance
WORKDIR /app/frontend
RUN NEXT_TELEMETRY_DISABLED=1 npm run build

# Make the startup script executable
WORKDIR /app
RUN chmod +x start.sh

# Expose the API (8000) and Frontend (3000) ports
EXPOSE 3000 8000

# Start both servers when the container runs
CMD ["./start.sh"]
