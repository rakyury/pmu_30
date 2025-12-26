# PMU-30 Emulator Docker Image
# Builds and runs the firmware emulator for testing without hardware
#
# Build:  docker build -t pmu30-emulator .
# Run:    docker run -it --rm -p 8080:8080 -p 5555:5555 pmu30-emulator
#
# Ports:
#   8080 - Web UI (if enabled)
#   5555 - Protocol server (TCP)

FROM ubuntu:22.04

LABEL maintainer="PMU-30 Team"
LABEL description="PMU-30 Power Management Unit Emulator"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install PlatformIO
RUN pip3 install --no-cache-dir platformio

# Set working directory
WORKDIR /app/firmware

# Copy firmware source
COPY . /app/firmware/

# Build the emulator
RUN pio run -e pmu30_emulator

# Expose ports
# 8080: Web UI
# 5555: Protocol server
EXPOSE 8080 5555

# Set the entrypoint to run the emulator
ENTRYPOINT [".pio/build/pmu30_emulator/program"]

# Default arguments (can be overridden)
CMD ["--port", "5555"]
