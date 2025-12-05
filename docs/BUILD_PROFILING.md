# Docker Build Profiling Guide

## 🎯 Overview

This guide helps you identify bottlenecks in Docker image builds and optimize build performance.

## 🔧 Quick Start

### Basic Profiling

```bash
# Profile a full build with timing analysis
./scripts/profile-build.sh --build-arg PYTHON_VERSION=3.11

# Profile layer sizes
./scripts/profile-build.sh --mode layers --build-arg PYTHON_VERSION=3.11

# Profile cache efficiency
./scripts/profile-build.sh --mode cache --build-arg PYTHON_VERSION=3.11

# Run all profiling modes
./scripts/profile-build.sh --mode all --build-arg PYTHON_VERSION=3.11
```

## 📊 Profiling Methods

### 1. Build Timing Analysis

The profiler tracks time for each build step:

```bash
./scripts/profile-build.sh --mode full
```

**What to look for:**
- Steps taking > 30 seconds (potential bottlenecks)
- Network operations (apt-get, pip, conda installs)
- Compilation steps (if any)

### 2. Layer Size Analysis

Analyze which layers contribute most to image size:

```bash
./scripts/profile-build.sh --mode layers
```

**What to look for:**
- Large layers (> 100MB)
- Layers that could be combined
- Unnecessary files in layers

### 3. Cache Efficiency

Measure how well your build uses Docker's layer cache:

```bash
./scripts/profile-build.sh --mode cache
```

**What to look for:**
- Cache hit rate < 50% (poor cache utilization)
- Steps that invalidate cache unnecessarily
- Opportunities to reorder commands

## 🔍 Manual Profiling Techniques

### Using Docker BuildKit Progress

Enable detailed BuildKit output:

```bash
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

docker buildx build \
    --progress=plain \
    --build-arg PYTHON_VERSION=3.11 \
    -f docker/Dockerfile.base \
    -t venvoy:test \
    . 2>&1 | tee build.log
```

### Analyzing Build Logs

Extract timing information:

```bash
# Find slow steps
grep -E "RUN|COPY|ADD" build.log | grep -E "[0-9]+\.[0-9]+s"

# Find cache misses
grep "CACHED" build.log | wc -l

# Find network operations
grep -E "apt-get|pip install|conda install" build.log
```

### Using Docker History

Analyze layer sizes:

```bash
docker history venvoy:test --format "table {{.CreatedBy}}\t{{.Size}}" | head -20
```

### Using Dive (Advanced)

Install [dive](https://github.com/wagoodman/dive) for interactive layer analysis:

```bash
# Install dive
# On macOS: brew install dive
# On Linux: https://github.com/wagoodman/dive#installation

# Analyze image
dive venvoy:test
```

## 🐌 Common Bottlenecks in venvoy Builds

Based on the Dockerfile structure, here are likely bottlenecks:

### 1. **Multiple apt-get Operations** (Lines 24-36, 41-47)
**Issue:** Two separate `apt-get update` calls create unnecessary layers
**Solution:** Combine into single RUN command

### 2. **Conda Operations** (Lines 49-88)
**Issue:** Multiple conda commands (install, update, create, install packages)
**Solution:** 
- Combine conda operations where possible
- Use mamba from the start (faster than conda)
- Consider pre-built conda environments

### 3. **Network Downloads** (Lines 50, 94)
**Issue:** Downloading miniconda and pip packages over network
**Solution:**
- Use BuildKit cache mounts for pip cache
- Consider using a local miniconda installer if rebuilding frequently

### 4. **Layer Invalidation**
**Issue:** Early COPY commands invalidate cache for all subsequent layers
**Solution:** 
- Move COPY commands to the end
- Use .dockerignore to reduce context size

## 🚀 Optimization Strategies

### 1. Combine RUN Commands

**Before:**
```dockerfile
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2
RUN rm -rf /var/lib/apt/lists/*
```

**After:**
```dockerfile
RUN apt-get update && \
    apt-get install -y package1 package2 && \
    rm -rf /var/lib/apt/lists/*
```

### 2. Use BuildKit Cache Mounts

**Before:**
```dockerfile
RUN pip install package1 package2
```

**After:**
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install package1 package2
```

### 3. Optimize Layer Ordering

Order commands from least to most frequently changing:
1. System packages (rarely change)
2. Application dependencies (change occasionally)
3. Application code (changes frequently)

### 4. Use Multi-Stage Builds

For build-time dependencies:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y build-essential
RUN pip install --user package1 package2

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

### 5. Reduce Build Context

Create `.dockerignore`:

```
.git
.gitignore
*.md
docs/
tests/
.venv
__pycache__
*.pyc
```

## 📈 Measuring Improvements

After optimizing, compare:

1. **Build time:** `time docker build ...`
2. **Image size:** `docker images venvoy:test`
3. **Cache hits:** Count "CACHED" in build output
4. **Layer count:** `docker history venvoy:test | wc -l`

## 🔧 Advanced: BuildKit Tracing

For detailed performance analysis:

```bash
# Enable BuildKit tracing
export BUILDKIT_STEP_LOG_MAX_SIZE=50000000
export BUILDKIT_STEP_LOG_MAX_SPEED=10000000

docker buildx build \
    --progress=plain \
    --trace=/tmp/trace.json \
    -f docker/Dockerfile.base \
    -t venvoy:test \
    .
```

## 📝 Example Optimization Workflow

1. **Profile current build:**
   ```bash
   ./scripts/profile-build.sh --mode all --build-arg PYTHON_VERSION=3.11
   ```

2. **Identify bottlenecks:**
   - Review timing analysis
   - Check layer sizes
   - Analyze cache efficiency

3. **Implement optimizations:**
   - Combine RUN commands
   - Reorder layers
   - Add cache mounts
   - Optimize Dockerfile

4. **Re-profile:**
   ```bash
   ./scripts/profile-build.sh --mode all --build-arg PYTHON_VERSION=3.11
   ```

5. **Compare results:**
   - Build time reduction
   - Image size reduction
   - Cache hit rate improvement

## 🎯 Target Metrics

Aim for:
- **Build time:** < 5 minutes for full build
- **Cache hit rate:** > 80% on rebuilds
- **Image size:** Minimize without sacrificing functionality
- **Layer count:** < 20 layers

## 📚 Additional Resources

- [Docker BuildKit documentation](https://docs.docker.com/build/buildkit/)
- [Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [dive tool](https://github.com/wagoodman/dive) - Interactive layer analysis
- [BuildKit cache mounts](https://docs.docker.com/build/guide/cache/)

