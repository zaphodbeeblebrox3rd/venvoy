#!/bin/bash
# Build and push multi-architecture venvoy images

set -e

# Supported Python versions
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13")

# Supported platforms (architectures)
PLATFORMS="linux/amd64,linux/arm64"

echo "🔨 Building multi-architecture venvoy images..."

# Ensure buildx is available
if ! docker buildx version &> /dev/null; then
    echo "❌ Docker BuildX not available. Please install Docker BuildX."
    echo "   Docker Desktop includes BuildX by default."
    echo "   For Linux: docker buildx install"
    exit 1
fi

# Create and use a new builder instance for multi-arch builds
BUILDER_NAME="venvoy-multiarch"
if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "🔧 Creating multi-architecture builder..."
    docker buildx create --name "$BUILDER_NAME" --use
else
    echo "🔧 Using existing multi-architecture builder..."
    docker buildx use "$BUILDER_NAME"
fi

# Build bootstrap image (single multi-arch image)
echo "📦 Building bootstrap image for all architectures..."
docker buildx build \
    --platform "$PLATFORMS" \
    --build-arg PYTHON_VERSION=3.11 \
    -f docker/Dockerfile.bootstrap \
    -t zaphodbeeblebrox3rd/venvoy:bootstrap \
    --push \
    .

echo "✅ Bootstrap image built and pushed"

# Build environment images for each Python version
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "📦 Building Python ${version} environment image for all architectures..."
    
    # Create a temporary Dockerfile for the environment image
    cat > docker/Dockerfile.env << EOF
# Multi-architecture venvoy environment image for Python ${version}
FROM python:${version}-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    curl \\
    git \\
    wget \\
    vim \\
    ca-certificates \\
    gnupg \\
    lsb-release \\
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (client only, no daemon) for Remote Containers extension compatibility
# This allows Cursor/VSCode Remote Containers to work properly
RUN install -m 0755 -d /etc/apt/keyrings && \\
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \\
    chmod a+r /etc/apt/keyrings/docker.gpg && \\
    echo "deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \\
    apt-get update && \\
    apt-get install -y docker-ce-cli && \\
    rm -rf /var/lib/apt/lists/*

# Install mambaforge with explicit architecture handling
RUN ARCH=\$(dpkg --print-architecture) && \\
    case "\$ARCH" in \\
        amd64) CONDA_ARCH="x86_64" ;; \\
        arm64) CONDA_ARCH="aarch64" ;; \\
        *) CONDA_ARCH="x86_64" ;; \\
    esac && \\
    wget "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-\${CONDA_ARCH}.sh" -O /tmp/miniconda.sh && \\
    bash /tmp/miniconda.sh -b -p /opt/conda && \\
    rm /tmp/miniconda.sh && \\
    /opt/conda/bin/conda install -n base -c conda-forge mamba -y

# Add conda to PATH
ENV PATH="/opt/conda/bin:\$PATH"

# Initialize conda
RUN conda init bash

# Create environment using mamba
RUN mamba create -n venvoy python=${version} -c conda-forge -y

# Install uv for ultra-fast Python package management
RUN /opt/conda/envs/venvoy/bin/pip install --no-cache-dir uv

# Activate environment by default
ENV CONDA_DEFAULT_ENV=venvoy
ENV CONDA_PREFIX=/opt/conda/envs/venvoy
ENV PATH="/opt/conda/envs/venvoy/bin:\$PATH"

# Install common AI/ML packages using mamba
RUN mamba install -n venvoy -c conda-forge \\
    numpy \\
    pandas \\
    matplotlib \\
    seaborn \\
    jupyter \\
    ipython \\
    requests \\
    python-dotenv \\
    -y

# Set working directory
WORKDIR /workspace

# Create user with same UID as host user (for file permissions)
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g \$GROUP_ID venvoy && \\
    useradd -u \$USER_ID -g \$GROUP_ID -m -s /bin/bash venvoy

# Switch to user
USER venvoy

# Set up shell with better interactive experience
RUN echo 'conda activate venvoy' >> ~/.bashrc && \\
    echo 'export PS1="(🤖 venvoy) \\\\u@\\\\h:\\\\w\\\\$ "' >> ~/.bashrc && \\
    echo 'echo "🚀 Welcome to your AI-ready venvoy environment!"' >> ~/.bashrc && \\
    echo 'echo "🐍 Python \$(python --version) with AI/ML packages"' >> ~/.bashrc && \\
    echo 'echo "📦 Package managers: mamba (fast conda), uv (ultra-fast pip), pip"' >> ~/.bashrc && \\
    echo 'echo "📊 Pre-installed: numpy, pandas, matplotlib, jupyter, and more"' >> ~/.bashrc && \\
    echo 'echo "🔍 Auto-saving environment.yml on package changes"' >> ~/.bashrc && \\
    echo 'echo "📂 Workspace: \$(pwd)"' >> ~/.bashrc && \\
    echo 'echo "💡 Home directory mounted at: /home/venvoy/host-home"' >> ~/.bashrc

# Default command
CMD ["/bin/bash"]
EOF

    # Build and push the environment image
    docker buildx build \
        --platform "$PLATFORMS" \
        -f docker/Dockerfile.env \
        -t zaphodbeeblebrox3rd/venvoy:python${version} \
        --push \
        .
    
    echo "✅ Python ${version} environment image built and pushed"
    
    # Clean up temporary Dockerfile
    rm -f docker/Dockerfile.env
done

echo "🎉 All multi-architecture images built and pushed successfully!"
echo ""
echo "📋 Available multi-arch images:"
echo "   • zaphodbeeblebrox3rd/venvoy:bootstrap (venvoy CLI tools)"
for version in "${PYTHON_VERSIONS[@]}"; do
    echo "   • zaphodbeeblebrox3rd/venvoy:python${version} (Python ${version} environment)"
done
echo ""
echo "🏗️  Supported architectures:"
echo "   • linux/amd64 (Intel/AMD x86_64)"
echo "   • linux/arm64 (Apple Silicon, ARM64 servers)"
echo ""
echo "🚀 Users can now run: curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash"
echo "   Docker will automatically pull the correct architecture for their system!"
echo ""
echo "💡 When users run 'venvoy init --python-version 3.13', it will use the"
echo "   pre-built multi-architecture zaphodbeeblebrox3rd/venvoy:python3.13 image." 