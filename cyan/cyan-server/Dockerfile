#
# Haproxy Dockerfile
#
# https://github.com/dockerfile/haproxy
#

# Pull base image.
FROM dockerfile/ubuntu

# Install Haproxy.
RUN \
  sed -i 's/^# \(.*-backports\s\)/\1/g' /etc/apt/sources.list && \
  apt-get update && \
  apt-get install -y haproxy=1.5.3-1~ubuntu14.04.1 supervisor && \
  sed -i 's/^ENABLED=.*/ENABLED=1/' /etc/default/haproxy && \
  rm -rf /var/lib/apt/lists/*
RUN apt-get install -y tmux

# Add binaries
ADD bin/etcd /etcd
ADD bin/confd /confd

# Add config
ADD config /config
ADD launch-confd.sh /launch-confd.sh

# Define mountable directories.
#RUN mkdir /config
#VOLUME ["/config"]
# Define default command.
CMD ["/usr/bin/supervisord", "-c", "/config/supervisor.conf"]

# Expose ports.
EXPOSE 8000
EXPOSE 443
EXPOSE 4001
EXPOSE 8080

