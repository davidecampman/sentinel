# 1. Use Ubuntu 24.04 LTS as the foundation
FROM ubuntu:24.04

# 2. IMMEDIATE SECURITY UPDATE & LOCALE SETUP
# We combine these into one RUN command to keep the image small
RUN apt-get update && apt-get upgrade -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    locales tzdata && \
    sed -i -e 's/# \(en_US\.UTF-8 .*\)/\1/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8 && \
    ln -sf /usr/share/zoneinfo/UTC /etc/localtime && \
    echo "UTC" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 3. Set Environment Variables
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
ENV TZ=UTC

# 4. Copy filesystem files to root
COPY ./fs/ /

# 5. Install software (The scripts you provided)
RUN bash /ins/install_base_packages1.sh
RUN bash /ins/install_base_packages2.sh
RUN bash /ins/install_base_packages3.sh
RUN bash /ins/install_base_packages4.sh

# 6. Install Python and SearXNG
RUN bash /ins/install_python.sh
RUN bash /ins/install_searxng.sh

# 7. Final Configuration
RUN bash /ins/configure_ssh.sh
RUN bash /ins/after_install.sh

# Keep container running infinitely
CMD ["tail", "-f", "/dev/null"]