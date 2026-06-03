FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash \
    git \
    curl \
    ca-certificates \
    python3 \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global user.name "AI User" && \
    git config --global user.email "ai@local" && \
    git config --global init.defaultBranch main

# Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource.sh && \
    bash /tmp/nodesource.sh && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* /tmp/nodesource.sh

# AI CLI 工具
RUN npm install -g @anthropic-ai/claude-code @openai/codex && \
    npm cache clean --force

RUN useradd -m -s /bin/bash ai-user
USER ai-user
WORKDIR /workspace

CMD ["/bin/bash"]
