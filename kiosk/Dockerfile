################################################################################
# /home/gc/suitestream-adb/kiosk/Dockerfile
#
# Build a minimal ARM64 container that installs Chromium + ALSA, so we can
# render on :0.0 / :0.1 and playback on “both1” / “both2” as defined in
# /etc/asound.conf on the Pi.
################################################################################

# 1) Base image: Debian Bookworm (slim) for ARM64
FROM debian:bookworm-slim

# 2) Install Chromium, ALSA libraries, and minimal X11 dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        chromium \
        ca-certificates \
        fonts-liberation \
        libappindicator3-1 \
        libnss3 \
        lsb-release \
        xdg-utils \
        x11-xserver-utils \
        openbox \
        xserver-xorg-video-fbdev \
        xserver-xorg-core \
        libasound2      \
        alsa-utils      \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3) Create a non-root user “kiosk” (UID 1000) and add to 'audio' group
RUN useradd -m -s /bin/bash kiosk && \
    # Create Chromium config directory and set ownership
    mkdir -p /home/kiosk/.config/chromium && \
    chown -R kiosk:kiosk /home/kiosk/.config && \
    # Ensure kiosk user is in the 'audio' group so it can open /dev/snd
    usermod -aG audio kiosk

# 4) Switch to "kiosk" user
USER kiosk
ENV HOME=/home/kiosk
WORKDIR /home/kiosk

# 5) No ENTRYPOINT—docker-compose will pass the actual 'chromium' command
ENTRYPOINT []
CMD ["bash"]
