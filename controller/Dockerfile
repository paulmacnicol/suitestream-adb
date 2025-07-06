# File: Dockerfile

FROM node:16-bullseye-slim

# 1) Install ADB, CEC, and networking tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      android-tools-adb \
      cec-utils \
      iproute2 \
      curl \
      rtmpdump \
      mosquitto-clients \
      iputils-ping \
      netcat-openbsd \
      dnsutils && \
    rm -rf /var/lib/apt/lists/*

# 2) Set working directory
WORKDIR /usr/src/app

# 3) Copy and install Node.js dependencies
COPY package.json package-lock.json* ./
RUN npm install --production

# 4) Copy application code
COPY . .

# 5) Expose port and start
ENV PORT=80
CMD ["node", "index.js"]
