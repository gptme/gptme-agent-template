# Container for full e2e agent setup testing
# Tests fork.sh, dotfiles, scripts, and service validation

FROM ubuntu:24.04

# Avoid prompts during apt installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    sudo \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create test user (simulates real agent setup)
RUN useradd -m -s /bin/bash testuser && \
    echo "testuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set working directory
WORKDIR /home/testuser

# Copy template files
COPY --chown=testuser:testuser . /home/testuser/gptme-agent-template

# Switch to test user
USER testuser
WORKDIR /home/testuser

# Run tests as entry point
ENTRYPOINT ["/home/testuser/gptme-agent-template/tests/container/run-tests.sh"]
