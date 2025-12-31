# Docker Repository Cleanup Guide

## 🎯 Overview

Your Docker Hub repository may accumulate unnecessary tags over time, especially from:
- GitHub Actions creating branch/PR tags
- Architecture-specific tags (`-amd64`, `-arm64`) that are redundant with multi-arch manifests
- Old semver version tags

## 📋 Required Tags (DO NOT DELETE)

These tags are actively used by venvoy and must be kept:

### Python Images
- `python3.9`
- `python3.10`
- `python3.11`
- `python3.12`
- `python3.13`
- `latest` (points to python3.11)

### R Images
- `r4.2`
- `r4.3`
- `r4.4`
- `r4.5`

### Bootstrap Image
- `bootstrap`

## 🗑️ Safe to Delete

### 1. Architecture-Specific Tags
These are **redundant** because venvoy uses multi-architecture manifests:
- `python3.11-amd64`
- `python3.11-arm64`
- `r4.4-amd64`
- `r4.4-arm64`
- `bootstrap-amd64`
- `bootstrap-arm64`
- `latest-amd64`
- `latest-arm64`

**Why safe?** The code constructs tags like `python{version}`, not `python{version}-amd64`. Docker automatically pulls the correct architecture from the multi-arch manifest.

### 2. GitHub Actions Temporary Tags
These are created during CI/CD but not needed long-term:
- `main-python3.11` (branch tags)
- `feature-xyz-python3.11` (branch tags)
- `pr-123-python3.11` (PR tags)
- `pr-456-r4.4` (PR tags)

### 3. Old Semver Tags
Keep only the **latest** version tags, delete older ones:
- `1.2.3-python3.11` (old versions)
- `1.2-python3.11` (old minor versions)
- `1.0.0-r4.4` (old versions)

Keep the most recent version tags if you want version pinning, but they're not required for normal operation.

## 🔧 How to Clean Up

### Option 1: Automated Cleanup Script (Recommended)

The cleanup script uses the Docker Hub API to automatically identify and delete unnecessary tags.

#### Setup

1. **Create `docker.env` file** in the project root:
   ```bash
   DOCKER_USERNAME="your_username"
   DOCKER_TOKEN="your_docker_hub_token"
   ```

2. **Get a Docker Hub token**:
   - Go to https://hub.docker.com/settings/security
   - Click "New Access Token"
   - Name it (e.g., "venvoy-cleanup")
   - Set permissions to "Read, Write, Delete"
   - Copy the token and add it to `docker.env`

3. **Install required tools** (if not already installed):
   ```bash
   # On Ubuntu/Debian
   sudo apt-get install curl jq
   
   # On macOS
   brew install curl jq
   ```

#### Usage

```bash
# Preview what would be deleted (safe, no changes made)
./scripts/cleanup-docker-tags.sh --dry-run

# Actually delete the tags (requires confirmation)
./scripts/cleanup-docker-tags.sh --execute
```

The script will:
- ✅ Load credentials from `docker.env`
- ✅ Fetch all tags from Docker Hub API
- ✅ Identify tags that can be safely deleted
- ✅ Show a summary of what will be deleted
- ✅ Ask for confirmation before deleting (in execute mode)
- ✅ Delete tags via Docker Hub API
- ✅ Provide a summary of the cleanup

#### What the Script Does

1. **Lists all tags** from Docker Hub (handles pagination automatically)
2. **Categorizes tags**:
   - Required tags (kept)
   - Architecture-specific tags (deleted)
   - Branch/PR tags (deleted)
   - Old semver tags (deleted)
3. **Shows preview** in dry-run mode
4. **Deletes tags** in execute mode (with confirmation)

### Option 2: Docker Hub Web Interface (Manual)

1. Go to https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy/tags
2. Review all tags
3. Select tags to delete (use checkboxes)
4. Click "Delete" button
5. Confirm deletion

**Recommended order:**
1. Delete all `*-amd64` and `*-arm64` tags first (biggest space savings)
2. Delete branch/PR tags
3. Delete old semver tags

### Option 3: Manual Docker Hub API

If you prefer to use the API directly:

```bash
# Load credentials from docker.env
source docker.env

# List all tags
curl -u "$DOCKER_USERNAME:$DOCKER_TOKEN" \
  "https://hub.docker.com/v2/repositories/zaphodbeeblebrox3rd/venvoy/tags?page_size=100" \
  | jq -r '.results[].name'

# Delete a specific tag
curl -X DELETE \
  -u "$DOCKER_USERNAME:$DOCKER_TOKEN" \
  "https://hub.docker.com/v2/repositories/zaphodbeeblebrox3rd/venvoy/tags/python3.11-amd64/"
```

## 📊 Expected Space Savings

- **Architecture-specific tags**: ~50-70% reduction (each tag duplicates the image)
- **Temporary tags**: ~10-20% reduction
- **Old semver tags**: ~5-10% reduction

**Total potential savings: 60-80% of repository size**

## ⚠️ Important Notes

1. **Multi-arch manifests**: The main tags (`python3.11`, `r4.4`, etc.) are multi-architecture manifests that contain both amd64 and arm64. Deleting the architecture-specific tags doesn't affect functionality.

2. **Code compatibility**: The venvoy code dynamically constructs tags:
   ```python
   image_name = f"zaphodbeeblebrox3rd/venvoy:python{self.python_version}"
   ```
   It never references `-amd64` or `-arm64` suffixes.

3. **Docker automatic selection**: When you pull `python3.11`, Docker automatically selects the correct architecture (amd64 or arm64) from the multi-arch manifest.

4. **Backup**: Before deleting, you can export important images:
   ```bash
   docker pull zaphodbeeblebrox3rd/venvoy:python3.11
   docker save zaphodbeeblebrox3rd/venvoy:python3.11 -o python3.11-backup.tar
   ```

5. **⚠️ Untagged Images - CRITICAL**: After deleting tags, you will see **untagged images** in Docker Hub's Image Management tab. These are **NOT automatically removed** by Docker Hub's garbage collection. You **MUST manually delete them** to free storage space:
   - Go to: https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy → **Image Management** tab
   - Filter or search for untagged images
   - Select the untagged images you want to delete
   - Click **"Preview and delete"** → **"Delete forever"**
   - This is the **only way** to reclaim storage from untagged images

## 🔍 Verification

After cleanup, verify everything still works:

```bash
# Test Python images
docker pull zaphodbeeblebrox3rd/venvoy:python3.11
docker pull zaphodbeeblebrox3rd/venvoy:latest

# Test R images
docker pull zaphodbeeblebrox3rd/venvoy:r4.4

# Test bootstrap
docker pull zaphodbeeblebrox3rd/venvoy:bootstrap

# Test with venvoy
venvoy init --python-version 3.11 --name test
venvoy run --name test
```

## 🚫 Preventing Future Bloat

1. **Update GitHub Actions**: Modify `.github/workflows/build-images.yml` to avoid creating temporary tags:
   ```yaml
   tags: |
     type=raw,value=python${{ matrix.python_version }}
     type=raw,value=latest,enable={{is_default_branch}}
   ```
   Remove: `type=ref,event=branch`, `type=ref,event=pr`, `type=semver` patterns

2. **Use combined images**: All images are now combined Python+R images built with `build-python-r.sh`. Architecture-specific builds are handled automatically via multi-arch manifests.

3. **Regular cleanup**: Schedule periodic cleanup (monthly/quarterly) to remove old tags.

## 📝 Summary

**Safe to delete:**
- ✅ All `*-amd64` and `*-arm64` tags
- ✅ Branch/PR tags from GitHub Actions
- ✅ Old semver version tags

**Must keep:**
- ✅ `python3.9` through `python3.13`
- ✅ `latest`
- ✅ `r4.2` through `r4.5`
- ✅ `bootstrap`

**Expected result:** 60-80% reduction in repository size with no impact on functionality.

