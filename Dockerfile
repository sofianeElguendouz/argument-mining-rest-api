FROM python:3.11-bookworm

# Never prompt the user for choices on installation/configuration of packages
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

RUN set -ex \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
        build-essential \
        python3-dev \
        libpq-dev \
        locales

ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

RUN set -ex \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# Install uv
ENV VIRTUAL_ENV=/usr/local
ADD --chmod=755 https://astral.sh/uv/install.sh /install.sh
RUN /install.sh && rm /install.sh
RUN /root/.cargo/bin/uv pip install --system --no-cache-dir --upgrade pip setuptools wheel

RUN mkdir /orbis_am_tool

WORKDIR /orbis_am_tool

ADD requirements.txt /orbis_am_tool/
RUN /root/.cargo/bin/uv pip install --system --no-cache-dir --upgrade -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

ENTRYPOINT [ "/bin/bash", "/orbis_am_tool/entrypoint.sh" ]