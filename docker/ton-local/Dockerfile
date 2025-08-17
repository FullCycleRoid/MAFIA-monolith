FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for mock server
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app

# Create a simple mock TON API server
COPY ton-mock-server.js /app/

EXPOSE 8081 8082

CMD ["node", "ton-mock-server.js"]
