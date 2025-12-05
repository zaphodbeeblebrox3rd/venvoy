#!/bin/bash
# Docker Build Profiling Script
# Profiles Docker builds to identify bottlenecks and optimization opportunities

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 Docker Build Profiler"
echo "========================"
echo ""

# Check if Docker BuildKit is available
if ! docker buildx version &> /dev/null; then
    echo -e "${RED}❌ Docker BuildX not found. Install it for better profiling:${NC}"
    echo "   docker buildx install"
    exit 1
fi

# Parse arguments
DOCKERFILE="docker/Dockerfile.base"
BUILD_ARG=""
IMAGE_TAG="venvoy-profile-test"
PROFILE_MODE="full"  # full, layers, cache, or all

while [[ $# -gt 0 ]]; do
    case $1 in
        --dockerfile|-f)
            DOCKERFILE="$2"
            shift 2
            ;;
        --build-arg)
            BUILD_ARG="$2"
            shift 2
            ;;
        --tag|-t)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --mode|-m)
            PROFILE_MODE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Profile Docker builds to identify bottlenecks"
            echo ""
            echo "Options:"
            echo "  --dockerfile, -f FILE    Dockerfile to profile (default: docker/Dockerfile.base)"
            echo "  --build-arg ARG          Build argument (e.g., PYTHON_VERSION=3.11)"
            echo "  --tag, -t TAG            Image tag for test build (default: venvoy-profile-test)"
            echo "  --mode, -m MODE          Profile mode: full, layers, cache, or all (default: full)"
            echo "  --help, -h               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --build-arg PYTHON_VERSION=3.11"
            echo "  $0 --mode layers"
            echo "  $0 --mode all"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ ! -f "$DOCKERFILE" ]; then
    echo -e "${RED}❌ Dockerfile not found: $DOCKERFILE${NC}"
    exit 1
fi

# Enable BuildKit for better output
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

echo -e "${BLUE}📋 Build Configuration:${NC}"
echo "   Dockerfile: $DOCKERFILE"
echo "   Image tag: $IMAGE_TAG"
if [ -n "$BUILD_ARG" ]; then
    echo "   Build arg: $BUILD_ARG"
fi
echo "   Profile mode: $PROFILE_MODE"
echo ""

# Function to profile full build with timing
profile_full_build() {
    echo -e "${YELLOW}⏱️  Profiling full build with timing...${NC}"
    echo ""
    
    local start_time=$(date +%s)
    
    # Build with detailed progress
    if [ -n "$BUILD_ARG" ]; then
        docker buildx build \
            --progress=plain \
            --no-cache \
            --build-arg "$BUILD_ARG" \
            -f "$DOCKERFILE" \
            -t "$IMAGE_TAG" \
            . 2>&1 | tee /tmp/docker-build-profile.log
    else
        docker buildx build \
            --progress=plain \
            --no-cache \
            -f "$DOCKERFILE" \
            -t "$IMAGE_TAG" \
            . 2>&1 | tee /tmp/docker-build-profile.log
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    echo -e "${GREEN}✅ Build completed in ${duration} seconds${NC}"
    echo ""
    
    # Extract timing information from build log
    echo -e "${BLUE}📊 Step Timing Analysis:${NC}"
    echo ""
    
    # Extract RUN command timings
    grep -E "^#\d+ \[.*RUN" /tmp/docker-build-profile.log | while read -r line; do
        step_num=$(echo "$line" | grep -oP '#\K\d+')
        step_info=$(echo "$line" | sed 's/^#\d+ \[.*\] //')
        echo "   Step $step_num: $step_info"
    done
    
    echo ""
}

# Function to analyze layer sizes
profile_layers() {
    echo -e "${YELLOW}📦 Analyzing layer sizes...${NC}"
    echo ""
    
    # Get image history with sizes
    docker history "$IMAGE_TAG" --format "table {{.CreatedBy}}\t{{.Size}}" | head -20
    
    echo ""
    echo -e "${BLUE}💡 Tip:${NC} Look for large layers that could be optimized"
    echo ""
}

# Function to profile cache efficiency
profile_cache() {
    echo -e "${YELLOW}💾 Profiling cache efficiency...${NC}"
    echo ""
    
    echo "Building with cache to measure cache hit rate..."
    
    local start_time=$(date +%s)
    
    if [ -n "$BUILD_ARG" ]; then
        docker buildx build \
            --progress=plain \
            --build-arg "$BUILD_ARG" \
            -f "$DOCKERFILE" \
            -t "$IMAGE_TAG-cached" \
            . 2>&1 | tee /tmp/docker-build-cached.log
    else
        docker buildx build \
            --progress=plain \
            -f "$DOCKERFILE" \
            -t "$IMAGE_TAG-cached" \
            . 2>&1 | tee /tmp/docker-build-cached.log
    fi
    
    local end_time=$(date +%s)
    local cached_duration=$((end_time - start_time))
    
    # Count cache hits
    local cache_hits=$(grep -c "CACHED" /tmp/docker-build-cached.log || echo "0")
    local total_steps=$(grep -c "^#\d+ \[" /tmp/docker-build-cached.log || echo "0")
    
    echo ""
    echo -e "${GREEN}✅ Cached build completed in ${cached_duration} seconds${NC}"
    echo ""
    echo -e "${BLUE}📊 Cache Statistics:${NC}"
    echo "   Cache hits: $cache_hits"
    echo "   Total steps: $total_steps"
    if [ "$total_steps" -gt 0 ]; then
        local hit_rate=$((cache_hits * 100 / total_steps))
        echo "   Cache hit rate: ${hit_rate}%"
    fi
    echo ""
}

# Function to analyze Dockerfile structure
analyze_dockerfile() {
    echo -e "${YELLOW}🔍 Analyzing Dockerfile structure...${NC}"
    echo ""
    
    local dockerfile_path="$DOCKERFILE"
    
    echo -e "${BLUE}📋 Dockerfile Statistics:${NC}"
    echo "   Total lines: $(wc -l < "$dockerfile_path")"
    echo "   FROM statements: $(grep -c "^FROM" "$dockerfile_path" || echo "0")"
    echo "   RUN statements: $(grep -c "^RUN" "$dockerfile_path" || echo "0")"
    echo "   COPY statements: $(grep -c "^COPY" "$dockerfile_path" || echo "0")"
    echo "   ENV statements: $(grep -c "^ENV" "$dockerfile_path" || echo "0")"
    echo ""
    
    echo -e "${BLUE}⚠️  Potential Issues:${NC}"
    
    # Check for multiple apt-get update calls
    local apt_updates=$(grep -c "apt-get update" "$dockerfile_path" || echo "0")
    if [ "$apt_updates" -gt 1 ]; then
        echo -e "   ${YELLOW}⚠️  Multiple 'apt-get update' calls ($apt_updates)${NC}"
        echo "      Consider combining RUN commands to reduce layers"
    fi
    
    # Check for uncombined RUN commands
    local run_commands=$(grep -c "^RUN" "$dockerfile_path" || echo "0")
    if [ "$run_commands" -gt 10 ]; then
        echo -e "   ${YELLOW}⚠️  Many RUN commands ($run_commands)${NC}"
        echo "      Consider combining related commands to reduce layers"
    fi
    
    # Check for pip installs without --no-cache-dir
    local pip_installs=$(grep -c "pip install" "$dockerfile_path" || echo "0")
    local pip_no_cache=$(grep -c "pip install.*--no-cache-dir" "$dockerfile_path" || echo "0")
    if [ "$pip_installs" -gt "$pip_no_cache" ]; then
        echo -e "   ${YELLOW}⚠️  Some pip installs missing --no-cache-dir${NC}"
        echo "      Add --no-cache-dir to reduce image size"
    fi
    
    echo ""
}

# Function to generate optimization recommendations
generate_recommendations() {
    echo -e "${YELLOW}💡 Optimization Recommendations:${NC}"
    echo ""
    
    echo -e "${GREEN}1. Layer Optimization:${NC}"
    echo "   • Combine multiple RUN commands where possible"
    echo "   • Use multi-stage builds for build dependencies"
    echo "   • Order commands from least to most frequently changing"
    echo ""
    
    echo -e "${GREEN}2. Cache Optimization:${NC}"
    echo "   • Place frequently changing commands (like COPY) near the end"
    echo "   • Use .dockerignore to exclude unnecessary files"
    echo "   • Consider using BuildKit cache mounts for package managers"
    echo ""
    
    echo -e "${GREEN}3. Size Optimization:${NC}"
    echo "   • Use --no-cache-dir for pip installs"
    echo "   • Clean up apt cache in the same RUN command"
    echo "   • Remove unnecessary packages after installation"
    echo "   • Use .dockerignore to reduce build context size"
    echo ""
    
    echo -e "${GREEN}4. Build Speed:${NC}"
    echo "   • Use BuildKit cache mounts for conda/pip caches"
    echo "   • Consider parallel builds for multi-arch images"
    echo "   • Use build cache effectively with proper layer ordering"
    echo ""
}

# Main execution
case "$PROFILE_MODE" in
    full)
        profile_full_build
        analyze_dockerfile
        generate_recommendations
        ;;
    layers)
        # Build first if image doesn't exist
        if ! docker image inspect "$IMAGE_TAG" &> /dev/null; then
            echo "Building image first..."
            if [ -n "$BUILD_ARG" ]; then
                docker buildx build --build-arg "$BUILD_ARG" -f "$DOCKERFILE" -t "$IMAGE_TAG" .
            else
                docker buildx build -f "$DOCKERFILE" -t "$IMAGE_TAG" .
            fi
        fi
        profile_layers
        ;;
    cache)
        # Build without cache first
        if ! docker image inspect "$IMAGE_TAG" &> /dev/null; then
            echo "Building image without cache first..."
            if [ -n "$BUILD_ARG" ]; then
                docker buildx build --no-cache --build-arg "$BUILD_ARG" -f "$DOCKERFILE" -t "$IMAGE_TAG" .
            else
                docker buildx build --no-cache -f "$DOCKERFILE" -t "$IMAGE_TAG" .
            fi
        fi
        profile_cache
        ;;
    all)
        analyze_dockerfile
        profile_full_build
        profile_layers
        profile_cache
        generate_recommendations
        ;;
    *)
        echo -e "${RED}❌ Unknown profile mode: $PROFILE_MODE${NC}"
        echo "Valid modes: full, layers, cache, all"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Profiling complete!${NC}"
echo ""
echo "📝 Build log saved to: /tmp/docker-build-profile.log"
if [ "$PROFILE_MODE" = "cache" ] || [ "$PROFILE_MODE" = "all" ]; then
    echo "📝 Cached build log saved to: /tmp/docker-build-cached.log"
fi
echo ""
echo "💡 Next steps:"
echo "   1. Review the timing analysis above"
echo "   2. Check layer sizes for optimization opportunities"
echo "   3. Review Dockerfile structure recommendations"
echo "   4. Implement optimizations and re-profile"

