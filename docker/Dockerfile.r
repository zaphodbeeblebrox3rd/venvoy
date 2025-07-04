# Multi-architecture venvoy R environment image
ARG R_VERSION=4.4
FROM rocker/r-ver:${R_VERSION}

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV R_VERSION=${R_VERSION}

# Install system dependencies for R packages and scientific computing
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

# Install key R packages for scientific computing
RUN R -e "install.packages(c( \
    'renv', \
    'devtools', \
    'tidyverse', \
    'data.table', \
    'ggplot2', \
    'dplyr', \
    'readr', \
    'tidyr', \
    'stringr', \
    'lubridate', \
    'purrr', \
    'forcats', \
    'rmarkdown', \
    'knitr', \
    'shiny', \
    'plotly', \
    'DT', \
    'jsonlite', \
    'httr', \
    'rvest', \
    'xml2' \
), repos='https://cran.rstudio.com/')"

# Install Bioconductor (for life sciences)
RUN R -e "if (!requireNamespace('BiocManager', quietly = TRUE)) install.packages('BiocManager'); \
    BiocManager::install(c('Biobase', 'limma', 'edgeR', 'DESeq2'))"

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
    echo 'echo "📊 R $(R --version | head -1 | cut -d\" \" -f3) with scientific packages"' >> ~/.bashrc && \
    echo 'echo "📦 Package managers: renv (reproducible), install.packages() (CRAN), BiocManager (Bioconductor)"' >> ~/.bashrc && \
    echo 'echo "📚 Pre-installed: tidyverse, data.table, rmarkdown, shiny, plotly, and more"' >> ~/.bashrc && \
    echo 'echo "🔬 Bioconductor ready for life sciences analysis"' >> ~/.bashrc && \
    echo 'echo "📂 Workspace: $(pwd)"' >> ~/.bashrc && \
    echo 'echo "💡 Home directory mounted at: /home/venvoy/host-home"' >> ~/.bashrc

# Default command
CMD ["/bin/bash"] 