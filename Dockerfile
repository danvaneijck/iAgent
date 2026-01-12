# Use a Python base image
FROM python:3.12-bookworm

# Set up environment variables early
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && \
    apt-get install -y gcc mono-mcs && \
    rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# 1. Copy ONLY requirements first
COPY requirements.txt .

# 2. Install requirements (This layer creates the cache)
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy application code AFTER requirements
# Now changing code won't trigger a re-install of pip packages
COPY injective_functions /app/injective_functions
COPY agent_server.py .

# Run the agent script
CMD ["python", "agent_server.py", "--port", "5000"]