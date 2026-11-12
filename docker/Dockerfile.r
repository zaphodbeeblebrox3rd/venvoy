# Multi-architecture venvoy R environment image
ARG R_VERSION=4.4
FROM docker.io/rocker/r-ver:${R_VERSION}

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV R_VERSION=${R_VERSION}

# Install comprehensive system dependencies for R packages and scientific computing
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    gfortran \
    # Version control
    git \
    # Network tools
    curl \
    wget \
    # Text processing
    vim \
    nano \
    # SSH server for 'venvoy remote' (Devin Remote-SSH from a laptop)
    openssh-server \
    openssh-client \
    # LaTeX for R Markdown
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-latex-extra \
    # Spatial analysis libraries
    libgdal-dev \
    libproj-dev \
    libgeos-dev \
    # Database connectivity
    libpq-dev \
    unixodbc-dev \
    # Image processing
    libmagick++-dev \
    # XML processing
    libxml2-dev \
    # SSL/TLS
    libssl-dev \
    # Compression
    libbz2-dev \
    liblzma-dev \
    # Cairo graphics
    libcairo2-dev \
    # Fonts
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Runtime directory required by sshd (used by 'venvoy remote')
RUN mkdir -p /run/sshd && chmod 0755 /run/sshd

# Set up R environment for package installation
RUN R -e "options(repos = c(CRAN = 'https://cran.rstudio.com/')); \
    options(download.file.method = 'libcurl'); \
    options(Ncpus = parallel::detectCores())"

# Set working directory
WORKDIR /workspace

# Create user with same UID as host user (for file permissions)
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g $GROUP_ID venvoy && \
    useradd -u $USER_ID -g $GROUP_ID -m -s /bin/bash venvoy

# Switch to user
USER venvoy

# Set up R environment
RUN echo 'options(repos = c(CRAN = "https://cran.rstudio.com/"))' >> ~/.Rprofile && \
    echo 'options(download.file.method = "libcurl")' >> ~/.Rprofile && \
    echo 'options(Ncpus = parallel::detectCores())' >> ~/.Rprofile

# Set up shell with better interactive experience
RUN echo 'export PS1="(📊 venvoy-R) \\u@\\h:\\w\\$ "' >> ~/.bashrc && \
    echo 'echo "🚀 Welcome to your R-powered venvoy environment!"' >> ~/.bashrc && \
    echo 'echo "📊 R $(R --version | head -1 | cut -d\" \" -f3) ready for your packages"' >> ~/.bashrc && \
    echo 'echo "📦 Package managers: install.packages() (CRAN), BiocManager (Bioconductor), renv (reproducible)"' >> ~/.bashrc && \
    echo 'echo "🔧 Pre-installed: build tools, LaTeX, spatial libraries, database connectors, graphics libraries"' >> ~/.bashrc && \
    echo 'echo "📂 Workspace: $(pwd)"' >> ~/.bashrc && \
    echo 'echo "💡 Install R packages: install.packages(c(\"package1\", \"package2\"))"' >> ~/.bashrc && \
    echo 'echo "🔧 Additional system packages: sudo apt-get update && sudo apt-get install package-name"' >> ~/.bashrc && \
    echo 'echo "📚 Ready for: tidyverse, sf, rmarkdown, shiny, plotly, and most CRAN/Bioconductor packages"' >> ~/.bashrc

# Default command
CMD ["/bin/bash"] 