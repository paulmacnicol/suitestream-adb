################################################################################
# /home/gc/suitestream-adb/controller/Dockerfile
#
# Build a super‐simple Nginx container that serves our index.html as “Hello World.”
# We'll run this container in privileged mode and mount the host’s root filesystem
# to /host so that from inside you can chroot or otherwise run host commands if needed.
################################################################################

# Base off the official tiny Nginx Linux image
FROM nginx:alpine

# Copy our static “Hello World” page into Nginx’s default www directory
COPY index.html /usr/share/nginx/html/index.html

# (No ENTRYPOINT override—Nginx’s default is fine: it will run in the foreground.)