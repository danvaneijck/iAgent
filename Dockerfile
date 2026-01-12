# Use a Python base image
FROM python:3.12-bookworm

# Set up environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
    apt-get install -y gcc mono-mcs && \
    rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
COPY injective_functions /app/injective_functions
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent script
COPY agent_server.py .

ENV PYTHONUNBUFFERED=1          
# Run the agent script
CMD ["python", "agent_server.py", "--port", "5000"]
