#!/bin/bash
# Cleanup script for Docker Hub repository
# Removes unnecessary tags to reduce repository size
#
# This script uses Docker Hub API to:
# - List all tags in the repository
# - Identify tags that can be safely deleted
# - Delete unnecessary tags (architecture-specific, branch/PR tags, old semver tags)
#
# Usage:
#   ./scripts/cleanup-docker-tags.sh --dry-run    # Show what would be deleted
#   ./scripts/cleanup-docker-tags.sh --execute    # Actually delete the tags
#
# Requirements:
#   - docker.env file in project root with DOCKER_USERNAME and DOCKER_TOKEN
#   - curl and jq installed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

REGISTRY="docker.io"
IMAGE_NAME="zaphodbeeblebrox3rd/venvoy"
REPO="${REGISTRY}/${IMAGE_NAME}"
# Extract namespace (username) from IMAGE_NAME
NAMESPACE=$(echo "$IMAGE_NAME" | cut -d'/' -f1)
REPOSITORY_NAME=$(echo "$IMAGE_NAME" | cut -d'/' -f2)

# Required tags that should NEVER be deleted
# These are the new combined Python+R images
REQUIRED_TAGS=(
    "python3.13-r4.5"
    "python3.12-r4.4"
    "python3.11-r4.3"
    "python3.11-r4.2"
    "python3.10-r4.2"
    "latest"
    "bootstrap"
)

DRY_RUN=true
EXECUTE=false
DELETE_UNTAGGED=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --execute)
            DRY_RUN=false
            EXECUTE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            EXECUTE=false
            shift
            ;;
        --delete-untagged)
            DELETE_UNTAGGED=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Cleanup Docker Hub repository tags"
            echo ""
            echo "Options:"
            echo "  --dry-run           Show what would be deleted (default)"
            echo "  --execute           Actually delete the tags (requires docker.env with credentials)"
            echo "  --delete-untagged   Also delete untagged images after deleting tags"
            echo "  --help, -h          Show this help message"
            echo ""
            echo "Requirements:"
            echo "  - docker.env file in project root with DOCKER_USERNAME and DOCKER_TOKEN"
            echo "  - curl and jq installed"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run    # Preview what would be deleted"
            echo "  $0 --execute    # Delete unnecessary tags"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🧹 Docker Hub Repository Cleanup"
echo "================================="
echo "Repository: $REPO"
echo "Mode: $([ "$DRY_RUN" = true ] && echo "DRY RUN (preview only)" || echo "EXECUTE (will delete tags)")"
echo ""

# Check for required tools
if ! command -v curl &> /dev/null; then
    echo "❌ curl not found. Please install curl."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "❌ jq not found. Please install jq (JSON processor)."
    echo "   On Ubuntu/Debian: sudo apt-get install jq"
    echo "   On macOS: brew install jq"
    exit 1
fi

# Load credentials from docker.env
DOCKER_ENV_FILE="$PROJECT_ROOT/docker.env"
if [ ! -f "$DOCKER_ENV_FILE" ]; then
    echo "❌ docker.env file not found at: $DOCKER_ENV_FILE"
    echo ""
    echo "Please create docker.env with:"
    echo "  DOCKER_USERNAME=\"your_username\""
    echo "  DOCKER_TOKEN=\"your_docker_hub_token\""
    echo ""
    echo "To get a Docker Hub token:"
    echo "  1. Go to https://hub.docker.com/settings/security"
    echo "  2. Create new access token with 'Read, Write, Delete' permissions"
    echo "  3. Save it in docker.env"
    exit 1
fi

# Source docker.env (handle quoted values)
set -a
source "$DOCKER_ENV_FILE"
set +a

if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_TOKEN" ]; then
    echo "❌ docker.env must contain DOCKER_USERNAME and DOCKER_TOKEN"
    echo "   Current file: $DOCKER_ENV_FILE"
    exit 1
fi

echo "✅ Loaded credentials from docker.env"
echo "   Username: $DOCKER_USERNAME"
echo ""

# Test authentication by making a simple API call
if [ "$EXECUTE" = true ]; then
    echo "🔐 Testing authentication..."
    test_url="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/"
    test_response=$(curl -s -w "\n%{http_code}" -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$test_url")
    test_http_code=$(echo "$test_response" | tail -n1)
    test_body=$(echo "$test_response" | sed '$d')
    
    if [ "$test_http_code" != "200" ]; then
        echo "❌ Authentication test failed (HTTP $test_http_code)"
        if echo "$test_body" | jq -e '.detail' > /dev/null 2>&1; then
            local error=$(echo "$test_body" | jq -r '.detail')
            echo "   Error: $error"
        fi
        echo ""
        echo "Please verify:"
        echo "  1. DOCKER_USERNAME is correct"
        echo "  2. DOCKER_TOKEN is valid and not expired"
        echo "  3. Token has 'Read, Write, Delete' permissions"
        echo "  4. You have access to the repository: $IMAGE_NAME"
        exit 1
    fi
    echo "✅ Authentication successful"
    echo ""
fi

# Function to check if tag is required
is_required_tag() {
    local tag=$1
    for required in "${REQUIRED_TAGS[@]}"; do
        if [ "$tag" = "$required" ]; then
            return 0
        fi
    done
    return 1
}

# Function to check if tag should be deleted
should_delete_tag() {
    local tag=$1
    
    # Never delete required tags
    if is_required_tag "$tag"; then
        return 1
    fi
    
    # Delete old separate Python tags (e.g., python3.9, python3.10, python3.11, python3.12, python3.13)
    # These have been replaced by combined Python+R images
    if [[ "$tag" =~ ^python3\.(9|10|11|12|13)$ ]]; then
        return 0
    fi
    
    # Delete old separate R tags (e.g., r4.2, r4.3, r4.4, r4.5)
    # These have been replaced by combined Python+R images
    if [[ "$tag" =~ ^r4\.(2|3|4|5)$ ]]; then
        return 0
    fi
    
    # Delete architecture-specific tags (redundant with multi-arch manifests)
    if [[ "$tag" == *"-amd64" ]] || [[ "$tag" == *"-arm64" ]]; then
        return 0
    fi
    
    # Delete branch tags (e.g., main-python3.11, feature-xyz-python3.11)
    if [[ "$tag" =~ ^[a-zA-Z0-9_-]+-python[0-9]+\.[0-9]+$ ]] || \
       [[ "$tag" =~ ^[a-zA-Z0-9_-]+-r[0-9]+\.[0-9]+$ ]]; then
        # But don't delete if it's just the base tag (e.g., "main" alone)
        if [[ "$tag" =~ ^[a-zA-Z0-9_-]+-(python|r)[0-9] ]]; then
            return 0
        fi
    fi
    
    # Delete PR tags (e.g., pr-123-python3.11)
    if [[ "$tag" =~ ^pr-[0-9]+-python[0-9]+\.[0-9]+$ ]] || \
       [[ "$tag" =~ ^pr-[0-9]+-r[0-9]+\.[0-9]+$ ]]; then
        return 0
    fi
    
    # Delete old semver tags (e.g., 1.2.3-python3.11, 1.2-python3.11)
    if [[ "$tag" =~ ^[0-9]+\.[0-9]+\.[0-9]+-python[0-9]+\.[0-9]+$ ]] || \
       [[ "$tag" =~ ^[0-9]+\.[0-9]+\.[0-9]+-r[0-9]+\.[0-9]+$ ]] || \
       [[ "$tag" =~ ^[0-9]+\.[0-9]+-python[0-9]+\.[0-9]+$ ]] || \
       [[ "$tag" =~ ^[0-9]+\.[0-9]+-r[0-9]+\.[0-9]+$ ]]; then
        return 0
    fi
    
    # Keep everything else (unknown format - be conservative)
    return 1
}

# Function to list all tags from Docker Hub API
list_all_tags() {
    local page=1
    local page_size=100
    local all_tags=()
    
    echo "📋 Fetching tags from Docker Hub API..."
    
    while true; do
        local url="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/tags?page=${page}&page_size=${page_size}"
        local response=$(curl -s -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$url")
        
        # Check for API errors
        if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
            local error=$(echo "$response" | jq -r '.detail')
            echo "❌ Docker Hub API error: $error"
            exit 1
        fi
        
        # Extract tag names
        local tags=$(echo "$response" | jq -r '.results[].name' 2>/dev/null || echo "")
        
        if [ -z "$tags" ] || [ "$tags" = "null" ]; then
            break
        fi
        
        # Add tags to array
        while IFS= read -r tag; do
            if [ -n "$tag" ]; then
                all_tags+=("$tag")
            fi
        done <<< "$tags"
        
        # Check if there are more pages
        local next=$(echo "$response" | jq -r '.next' 2>/dev/null)
        if [ "$next" = "null" ] || [ -z "$next" ]; then
            break
        fi
        
        page=$((page + 1))
    done
    
    printf '%s\n' "${all_tags[@]}"
}

# Function to URL-encode a string
urlencode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * ) printf -v o '%%%02x' "'$c"
        esac
        encoded+="${o}"
    done
    echo "${encoded}"
}

# Function to get a Bearer token from Docker's auth service
get_bearer_token() {
    # Request a Bearer token with delete scope for the repository
    # URL-encode the scope parameter
    local scope="repository:${IMAGE_NAME}:delete"
    local encoded_scope=$(urlencode "$scope")
    local auth_url="https://auth.docker.io/token?service=registry.docker.io&scope=${encoded_scope}"
    
    local response=$(curl -s -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$auth_url")
    
    # Check for errors
    if echo "$response" | jq -e '.error' > /dev/null 2>&1; then
        local error=$(echo "$response" | jq -r '.error_description // .error' 2>/dev/null)
        echo "   ⚠️  Auth error: $error" >&2
        echo "" >&2
        return 1
    fi
    
    # Extract the token from the response
    local token=$(echo "$response" | jq -r '.token' 2>/dev/null)
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        echo "   ⚠️  Failed to extract token from auth response" >&2
        echo "" >&2
        return 1
    fi
    
    echo "$token"
}

# Note: Docker Hub API v2 uses Basic auth (username:token) for DELETE operations
# Bearer tokens from auth.docker.io are for registry API, not Hub API

# Function to get tag details including manifest digest
get_tag_manifest_digest() {
    local tag=$1
    local encoded_tag=$(urlencode "$tag")
    local url="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/tags/${encoded_tag}/"
    
    local response=$(curl -s -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$url")
    
    # Extract the digest from the images array (first image's digest)
    local digest=$(echo "$response" | jq -r '.images[0].digest' 2>/dev/null)
    
    if [ -z "$digest" ] || [ "$digest" = "null" ]; then
        echo ""
        return 1
    fi
    
    echo "$digest"
}

# Function to get all manifest digests from all tags
get_all_tagged_manifests() {
    local page=1
    local page_size=100
    local all_digests=()
    
    echo "📋 Fetching manifest digests from all tags..."
    
    while true; do
        local url="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/tags?page=${page}&page_size=${page_size}"
        local response=$(curl -s -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$url")
        
        # Check for API errors
        if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
            break
        fi
        
        # Extract all digests from all images in all tags
        local digests=$(echo "$response" | jq -r '.results[].images[]?.digest' 2>/dev/null | grep -v "^null$" | grep -v "^$")
        
        if [ -z "$digests" ]; then
            break
        fi
        
        # Add digests to array
        while IFS= read -r digest; do
            if [ -n "$digest" ]; then
                all_digests+=("$digest")
            fi
        done <<< "$digests"
        
        # Check if there are more pages
        local next=$(echo "$response" | jq -r '.next' 2>/dev/null)
        if [ "$next" = "null" ] || [ -z "$next" ]; then
            break
        fi
        
        page=$((page + 1))
    done
    
    # Remove duplicates and return
    printf '%s\n' "${all_digests[@]}" | sort -u
}

# Function to list all images/manifests in the repository
list_all_images() {
    local page=1
    local page_size=100
    local all_images=()
    
    # Try the Image Management API endpoint
    while true; do
        local url="https://hub.docker.com/v2/repositories/${IMAGE_NAME}/images?page=${page}&page_size=${page_size}"
        local response=$(curl -s -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" "$url")
        
        # Check for API errors
        if echo "$response" | jq -e '.detail' > /dev/null 2>&1; then
            # If first page fails, the endpoint might not be available
            if [ $page -eq 1 ]; then
                return 1
            fi
            break
        fi
        
        # Try to extract image digests - the response format may vary
        local images=$(echo "$response" | jq -r '.results[]?.digest // .results[]?.manifest_digest // empty' 2>/dev/null | grep -v "^null$" | grep -v "^$")
        
        if [ -z "$images" ]; then
            # If no images found and we're on page 1, the endpoint might not work
            if [ $page -eq 1 ]; then
                return 1
            fi
            break
        fi
        
        # Add images to array
        while IFS= read -r image; do
            if [ -n "$image" ]; then
                all_images+=("$image")
            fi
        done <<< "$images"
        
        # Check if there are more pages
        local next=$(echo "$response" | jq -r '.next' 2>/dev/null)
        if [ "$next" = "null" ] || [ -z "$next" ]; then
            break
        fi
        
        page=$((page + 1))
    done
    
    if [ ${#all_images[@]} -eq 0 ]; then
        return 1
    fi
    
    printf '%s\n' "${all_images[@]}"
}

# Function to find untagged images
find_untagged_images() {
    local tagged_digests_file=$(mktemp)
    local all_images_file=$(mktemp)
    
    # Get all tagged manifest digests
    get_all_tagged_manifests > "$tagged_digests_file" 2>/dev/null
    
    # Get all images in repository
    if ! list_all_images > "$all_images_file" 2>/dev/null; then
        # If we can't list all images, we can't reliably find untagged ones
        # Return empty (caller should handle this gracefully)
        rm -f "$tagged_digests_file" "$all_images_file"
        echo "⚠️  Cannot list all images - Docker Hub API may not support this" >&2
        echo "   Untagged images must be deleted manually via Image Management tab" >&2
        return 1
    fi
    
    # Find images that are not in the tagged list
    comm -23 <(sort "$all_images_file") <(sort "$tagged_digests_file")
    
    rm -f "$tagged_digests_file" "$all_images_file"
}

# Function to delete untagged images using Docker Hub API
delete_untagged_images() {
    local digests=("$@")
    
    if [ ${#digests[@]} -eq 0 ]; then
        return 0
    fi
    
    # Docker Hub API endpoint for deleting images
    # Use Basic auth (username:token) for Docker Hub API v2
    local url="https://hub.docker.com/v2/namespaces/${NAMESPACE}/delete-images"
    
    # Build JSON payload with digests
    local json_payload=$(printf '%s\n' "${digests[@]}" | jq -R . | jq -s '{digests: ., ignore_warnings: true}')
    
    local response=$(curl -s -w "\n%{http_code}" \
        -X DELETE \
        -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json" \
        -d "$json_payload" \
        "$url")
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "202" ] || [ "$http_code" = "204" ]; then
        return 0
    else
        echo "   ⚠️  Failed to delete untagged images (HTTP $http_code): $body" >&2
        return 1
    fi
}

# Function to delete a tag via Docker Hub API v2
# Uses the correct endpoint format: /v2/namespaces/{namespace}/repositories/{repository}/tags/{tag}
delete_tag() {
    local tag=$1
    
    # Use Docker Hub API v2 with correct endpoint format
    local encoded_tag=$(urlencode "$tag")
    local url="https://hub.docker.com/v2/namespaces/${NAMESPACE}/repositories/${REPOSITORY_NAME}/tags/${encoded_tag}"
    
    local response=$(curl -s -w "\n%{http_code}" \
        -X DELETE \
        -u "${DOCKER_USERNAME}:${DOCKER_TOKEN}" \
        -H "Accept: application/json" \
        "$url")
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "204" ] || [ "$http_code" = "200" ]; then
        return 0
    elif [ "$http_code" = "404" ]; then
        # Tag already deleted
        return 0
    elif [ "$http_code" = "401" ]; then
        echo "   ⚠️  Authentication failed (HTTP 401)" >&2
        echo "   💡 Docker Hub API tag deletion requires:" >&2
        echo "      - Personal Access Token (not account password)" >&2
        echo "      - Token with 'Read, Write, Delete' permissions" >&2
        echo "      - Token created at: https://hub.docker.com/settings/security" >&2
        echo "   💡 Note: Docker Hub may restrict tag deletion via API" >&2
        echo "   💡 Alternative: Delete tags manually via Docker Hub web UI" >&2
        if [ "${DEBUG:-false}" = "true" ]; then
            echo "   🔍 Response: $body" >&2
        fi
        return 1
    else
        echo "   ⚠️  Failed to delete tag (HTTP $http_code): $body" >&2
        return 1
    fi
}

# Main execution
echo "✅ Tags that will be KEPT (required):"
for tag in "${REQUIRED_TAGS[@]}"; do
    echo "   • $tag"
done
echo ""

# Fetch all tags
all_tags=($(list_all_tags))
total_tags=${#all_tags[@]}

echo "📊 Found $total_tags total tags"
echo ""

# Categorize tags
tags_to_delete=()
tags_to_keep=()

for tag in "${all_tags[@]}"; do
    if should_delete_tag "$tag"; then
        tags_to_delete+=("$tag")
    else
        tags_to_keep+=("$tag")
    fi
done

delete_count=${#tags_to_delete[@]}
keep_count=${#tags_to_keep[@]}

echo "📊 Tag Analysis:"
echo "   Total tags: $total_tags"
echo "   Tags to keep: $keep_count"
echo "   Tags to delete: $delete_count"
echo ""

if [ $delete_count -eq 0 ]; then
    echo "✅ No tags to delete. Repository is clean!"
    exit 0
fi

echo "🗑️  Tags that will be deleted:"
for tag in "${tags_to_delete[@]}"; do
    echo "   • $tag"
done
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No tags will be deleted"
    echo ""
    
    # Check for untagged images if requested
    if [ "$DELETE_UNTAGGED" = true ]; then
        echo "🔍 Checking for untagged images..."
        untagged_digests=($(find_untagged_images 2>/dev/null))
        untagged_count=${#untagged_digests[@]}
        
        if [ $untagged_count -gt 0 ]; then
            echo "   Found $untagged_count untagged image(s) that would be deleted:"
            for digest in "${untagged_digests[@]:0:10}"; do
                echo "   • $digest"
            done
            if [ $untagged_count -gt 10 ]; then
                echo "   ... and $((untagged_count - 10)) more"
            fi
            echo ""
        else
            echo "   ✅ No untagged images found"
            echo ""
        fi
    fi
    
    echo "To actually delete these tags, run:"
    if [ "$DELETE_UNTAGGED" = true ]; then
        echo "  $0 --execute --delete-untagged"
    else
        echo "  $0 --execute"
        echo ""
        echo "To also delete untagged images, run:"
        echo "  $0 --execute --delete-untagged"
    fi
    exit 0
fi

# Execute deletion
echo "⚠️  EXECUTE MODE - Will delete $delete_count tags"
echo ""
read -p "Are you sure you want to delete these tags? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Cancelled. No tags were deleted."
    exit 0
fi

echo ""
echo "🗑️  Deleting tags..."
deleted=0
failed=0

for tag in "${tags_to_delete[@]}"; do
    echo -n "   Deleting $tag... "
    if delete_tag "$tag"; then
        echo "✅"
        deleted=$((deleted + 1))
    else
        echo "❌"
        failed=$((failed + 1))
    fi
    # Small delay to avoid rate limiting
    sleep 0.5
done

echo ""
echo "📊 Cleanup Summary:"
echo "   Tags deleted: $deleted"
if [ $failed -gt 0 ]; then
    echo "   Tags failed: $failed"
fi
echo "   Tags kept: $keep_count"
echo ""

# Handle untagged image deletion if requested
if [ "$DELETE_UNTAGGED" = true ] && [ "$EXECUTE" = true ]; then
    echo ""
    echo "🗑️  Checking for untagged images..."
    
    untagged_digests=($(find_untagged_images))
    untagged_count=${#untagged_digests[@]}
    
    if [ $untagged_count -gt 0 ]; then
        echo "   Found $untagged_count untagged image(s)"
        echo ""
        read -p "Delete $untagged_count untagged image(s)? (yes/no): " confirm_untagged
        
        if [ "$confirm_untagged" = "yes" ]; then
            echo ""
            echo "🗑️  Deleting untagged images..."
            
            # Delete in batches to avoid overwhelming the API
            batch_size=10
            deleted_untagged=0
            failed_untagged=0
            
            for ((i=0; i<untagged_count; i+=batch_size)); do
                batch=("${untagged_digests[@]:i:batch_size}")
                echo -n "   Deleting batch of ${#batch[@]} image(s)... "
                
                if delete_untagged_images "${batch[@]}"; then
                    echo "✅"
                    deleted_untagged=$((deleted_untagged + ${#batch[@]}))
                else
                    echo "❌"
                    failed_untagged=$((failed_untagged + ${#batch[@]}))
                fi
                
                # Small delay between batches
                sleep 1
            done
            
            echo ""
            echo "📊 Untagged Images Summary:"
            echo "   Images deleted: $deleted_untagged"
            if [ $failed_untagged -gt 0 ]; then
                echo "   Images failed: $failed_untagged"
            fi
        else
            echo "   Skipped untagged image deletion"
        fi
    else
        echo "   ✅ No untagged images found"
    fi
elif [ $deleted -gt 0 ]; then
    echo "ℹ️  Note: Untagged images were not deleted"
    echo "   • To delete untagged images, use: $0 --execute --delete-untagged"
    echo "   • Or manually delete them in Docker Hub's Image Management tab"
    echo "   • Go to: https://hub.docker.com/r/${IMAGE_NAME} → Image Management"
    echo ""
fi

echo "✅ Cleanup complete!"
