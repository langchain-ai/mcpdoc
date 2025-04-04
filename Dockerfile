# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install curl first
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Copy project dependency files first
COPY pyproject.toml uv.lock ./

# Install uv and project dependencies in one step
# Ensure PATH is updated within this RUN command's context before calling uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    export PATH="/root/.cargo/bin:/root/.local/bin:${PATH}" && \
    uv pip install --system -r pyproject.toml

# Set the PATH environment variable for subsequent commands and the final CMD/ENTRYPOINT
ENV PATH="/root/.cargo/bin:/root/.local/bin:${PATH}"

# Copy the rest of the application code
COPY ./mcpdoc ./mcpdoc
COPY mcpdoc_config.yaml /app/mcpdoc_config.yaml

# Expose the port if using SSE (though we default to stdio)
# EXPOSE 8080

# Command to run the MCP server using stdio transport
CMD ["uvx", "--from", "mcpdoc", "mcpdoc", "--yaml", "/app/mcpdoc_config.yaml", "--transport", "stdio"]