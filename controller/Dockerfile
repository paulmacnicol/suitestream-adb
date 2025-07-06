# /home/gc/suitestream-adb/controller/Dockerfile

FROM node:16-bullseye-slim

# 1) Install ADB + CEC + Python3 + utilities
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
      dnsutils \
      python3 \
      python3-pip \
      python3-tk && \
    rm -rf /var/lib/apt/lists/*

# 2) Make "python" point to python3, and "pip" to pip3
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3   /usr/bin/pip

# 3) Set working directory
WORKDIR /usr/src/app

# 4) Copy and install Node.js dependencies
COPY package.json package-lock.json* ./
RUN npm install --production

# 5) Copy in your application code
COPY . .

# 6) Install Python dependencies
RUN pip install pychromecast

# 7) Expose ports
#EXPOSE 80    # your proxy server
#EXPOSE 5555  # adb default port (if you need it mapped)

# 8) Default startup
ENV PORT=80
CMD ["node", "index.js"]
