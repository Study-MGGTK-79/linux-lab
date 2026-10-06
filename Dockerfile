FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Установка необходимых утилит для прохождения всех модулей курса
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    wget \
    vim \
    nano \
    git \
    sudo \
    procps \
    htop \
    psmisc \
    iproute2 \
    iputils-ping \
    net-tools \
    dnsutils \
    tcpdump \
    traceroute \
    iptables \
    ufw \
    nftables \
    openssh-server \
    openssh-client \
    openssl \
    ca-certificates \
    rsyslog \
    logrotate \
    cron \
    tree \
    tar \
    gzip \
    bzip2 \
    xz-utils \
    unzip \
    strace \
    lsof \
    build-essential \
    gcc \
    make \
    acl \
    attr \
    lvm2 \
    fdisk \
    parted \
    dosfstools \
    e2fsprogs \
    xfsprogs \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    apparmor-utils \
    auditd \
    sysstat \
    fail2ban \
    man-db \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя для практических заданий
RUN useradd -m -s /bin/bash student && \
    echo "student:student123" | chpasswd && \
    usermod -aG sudo student && \
    echo "student ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/student

WORKDIR /course

CMD ["/bin/bash"]
