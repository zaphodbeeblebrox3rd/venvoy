# venvoy Build Scripts

This directory contains scripts for building and managing venvoy container images.

## Active Scripts

### Main Build Scripts

- **`build-and-push.sh`** - Main orchestrator script that builds all images
  - Usage: `./scripts/build-and-push.sh [--python] [--bootstrap] [--all]`
  - Builds combined Python+R images and bootstrap image
  - Automatically runs cleanup preview after builds

- **`build-python-r.sh`** - Builds combined Python+R environment images
  - Builds 5 version pairs: Python 3.13/R 4.5, 3.12/4.4, 3.11/4.3, 3.11/4.2, 3.10/4.2
  - Creates multi-architecture images (amd64, arm64)
  - Tag format: `python{VERSION}-r{VERSION}` (e.g., `python3.13-r4.5`)

- **`build-bootstrap.sh`** - Builds the bootstrap image used for venvoy installation

### Utility Scripts

- **`cleanup-docker-tags.sh`** - Cleans up old Docker Hub tags
  - Usage: `./scripts/cleanup-docker-tags.sh [--dry-run] [--execute]`
  - Removes old separate Python/R tags, architecture-specific tags, and other unnecessary tags
  - Protects new combined tags and bootstrap/latest tags

- **`publish.py`** - Publishing automation script

- **`profile-build.sh`** - Build profiling and performance analysis

- **`diagnose-macos-path.sh`** - macOS-specific path diagnostics

- **`fix-macos-path.sh`** - macOS-specific path fixes

- **`issue-register.sh`** - Issue registration utility

- **`test-upgrade-fix.sh`** - Upgrade testing script

## Removed Scripts

The following scripts have been **removed** as they are no longer needed:

### Python/R Image Scripts (Replaced by Combined Images)
- ~~`build-r.sh`~~ - Removed (replaced by combined images)
- ~~`build-python-amd64.sh`~~ - Removed (replaced by combined images)
- ~~`build-python-arm64.sh`~~ - Removed (replaced by combined images)
- ~~`build-r-amd64.sh`~~ - Removed (replaced by combined images)
- ~~`build-r-arm64.sh`~~ - Removed (replaced by combined images)

### Bootstrap Architecture-Specific Scripts (Replaced by Multi-Arch Build)
- ~~`build-bootstrap-amd64.sh`~~ - Removed (replaced by multi-arch build)
- ~~`build-bootstrap-arm64.sh`~~ - Removed (replaced by multi-arch build)

All functionality is now provided by:
- `build-python-r.sh` - Builds combined multi-architecture Python+R images
- `build-bootstrap.sh` - Builds multi-architecture bootstrap images

## Image Tag Format

### Current (Combined Images)
- `python3.13-r4.5` - Python 3.13 with R 4.5
- `python3.12-r4.4` - Python 3.12 with R 4.4
- `python3.11-r4.3` - Python 3.11 with R 4.3
- `python3.11-r4.2` - Python 3.11 with R 4.2
- `python3.10-r4.2` - Python 3.10 with R 4.2
- `latest` - Points to Python 3.11 / R 4.3

### Deprecated (Old Separate Images)
These tags are being phased out and will be cleaned up:
- `python3.9`, `python3.10`, `python3.11`, `python3.12`, `python3.13` - Old separate Python images
- `r4.2`, `r4.3`, `r4.4`, `r4.5` - Old separate R images

## Building Images

### Build All Images
```bash
./scripts/build-and-push.sh
```

### Build Only Combined Python+R Images
```bash
./scripts/build-and-push.sh --python
```

### Build Only Bootstrap Image
```bash
./scripts/build-and-push.sh --bootstrap
```

### Build Combined Images Directly
```bash
./scripts/build-python-r.sh
```

## Cleaning Up Old Tags

After building new images, clean up old separate tags:

```bash
# Preview what would be deleted
./scripts/cleanup-docker-tags.sh --dry-run

# Actually delete old tags
./scripts/cleanup-docker-tags.sh --execute
```

The cleanup script will:
- Protect new combined tags (`python3.13-r4.5`, etc.)
- Delete old separate Python tags (`python3.9`, `python3.10`, etc.)
- Delete old separate R tags (`r4.2`, `r4.3`, etc.)
- Delete architecture-specific tags (`-amd64`, `-arm64`)
- Keep `latest` and `bootstrap` tags

