###
### Stage 1: Language Runtime
###
### Replace this stage with your project's language runtime (python:3.x, ruby:3.x, openjdk:21, etc.)
### Then update the COPY command in Stage 2 to copy the appropriate binaries/libraries
###
FROM golang:1.25 AS golang

###
### Stage 2: DevContainer
###
FROM node:20

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

# Install basic development tools and networking utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  nano \
  vim \
  wget \
  ca-certificates \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---- Language Runtime (from multi-stage) ----
# If using a different language, update this section:
# Python: COPY --from=python /usr/local /usr/local
# Ruby: COPY --from=ruby /usr/local /usr/local
# Java: COPY --from=openjdk /usr/local/openjdk-* /usr/local/jdk
COPY --from=golang /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:${PATH}"

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global \
 && chown -R node:node /usr/local/share

ARG USERNAME=node

# Persist bash history
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
 && mkdir /commandhistory \
 && touch /commandhistory/.bash_history \
 && chown -R $USERNAME /commandhistory

# DevContainer marker
ENV DEVCONTAINER=true

# Workspace and Claude config
RUN mkdir -p /workspace /home/node/.claude \
 && chown -R node:node /workspace /home/node/.claude

WORKDIR /workspace

# ---- git-delta ----
ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) \
 && wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" \
 && dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" \
 && rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Switch to non-root user
USER node

# NPM globals
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Shell & editor defaults
ENV SHELL=/bin/zsh
ENV EDITOR=nano
ENV VISUAL=nano

# ---- ZSH + powerline10k ----
ARG ZSH_IN_DOCKER_VERSION=1.2.0
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  -x

# ---- Claude ----
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} backlog.md

# ---- Firewall script ----
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh \
 && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall \
 && chmod 0440 /etc/sudoers.d/node-firewall

USER node
