################################################################################
# /home/gc/suitestream-adb/controller/Dockerfile
#
# 1) Base: Node 16 on Debian‐slim
# 2) Installs:
#    • android-tools-adb     → “adb” binary
#    • cec-utils             → “cec-client” binary
#    • iproute2, curl        → utilities
# 3) Copies in your proxy code:
#      - package.json       (for npm install)
#      - index.js, index.html (if you still need it), etc.
# 4) Listens on PORT 80 by default
################################################################################

FROM node:16-bullseye-slim

# 1) Install ADB + CEC utilities + extras
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      android-tools-adb \
      cec-utils       \
      iproute2        \
      curl            \
      python3         \
      python3-pip     \
      python3-tk      \ 
      curl \             
      rtmpdump \           
      mosquitto-clients \
      iputils-ping \       
      netcat-openbsd \     
      dnsutils \           
      
    && rm -rf /var/lib/apt/lists/*

# 2) Create app directory
WORKDIR /usr/src/app

# 3) Copy only package.json and install dependencies
COPY package.json ./
RUN npm install

# Install Python dependencies
RUN pip install --no-cache-dir \
       pychromecast

EXPOSE 5555

# 4) Copy the rest of your files (index.js, index.html if needed, etc.)
COPY . .

# 5) Expose 80 because you already have something on port 80
EXPOSE 80

# 6) Ensure the code reads PORT from env (default 80)
ENV PORT=80

# 7) Default command: run your proxy server
CMD ["node", "index.js"]
