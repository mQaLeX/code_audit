FROM ubuntu:22.04

LABEL maintainer="code_audit_agent"
LABEL description="Docker environment for code audit with penetration testing tools"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list && \
    sed -i 's@//.*security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    autoconf \
    automake \
    libtool \
    pkg-config \
    gdb \
    valgrind \
    strace \
    ltrace \
    clang \
    clangd \
    llvm \
    lldb \
    universal-ctags \
    cscope \
    global \
    curl \
    wget \
    git \
    vim \
    nano \
    netcat-openbsd \
    nmap \
    net-tools \
    iputils-ping \
    tcpdump \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libcurl4-openssl-dev \
    libjpeg-dev \
    libpng-dev \
    libsqlite3-dev \
    libpq-dev \
    libmysqlclient-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libldap2-dev \
    libc6-dev \
    libsodium-dev \
    libpcap-dev \
    libevent-dev \
    libjson-c-dev \
    libjansson-dev \
    jq \
    binwalk \
    foremost \
    file \
    xxd \
    hexedit \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf

RUN pip3 install --no-cache-dir \
    requests \
    aiohttp \
    httpx \
    beautifulsoup4 \
    lxml \
    scrapy \
    pwntools \
    ropgadget \
    capstone \
    keystone-engine \
    unicorn \
    angr \
    z3-solver \
    sympy \
    pycryptodome \
    pyelftools \
    r2pipe \
    ropper \
    flask \
    django \
    fastapi \
    uvicorn \
    pytest \
    ipython \
    rich \
    textual \
    openai \
    python-dotenv \
    pyyaml \
    toml \
    && rm -rf /root/.cache/pip

RUN mkdir -p /root/.config/clangd && \
    echo "CompileFlags:" > /root/.config/clangd/config.yaml && \
    echo "  Add: [-std=c17, -Wall, -Wextra]" >> /root/.config/clangd/config.yaml

RUN mkdir -p /workspace && \
    echo 'export PS1="\[\033[01;32m\]\u@code-audit\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "' >> /root/.bashrc && \
    echo "alias ll='ls -alF'" >> /root/.bashrc && \
    echo "alias la='ls -A'" >> /root/.bashrc && \
    echo "alias l='ls -CF'" >> /root/.bashrc && \
    echo "alias grep='grep --color=auto'" >> /root/.bashrc && \
    echo "alias fgrep='fgrep --color=auto'" >> /root/.bashrc && \
    echo "alias egrep='egrep --color=auto'" >> /root/.bashrc

WORKDIR /workspace

VOLUME ["/workspace"]

CMD ["/bin/bash"]
