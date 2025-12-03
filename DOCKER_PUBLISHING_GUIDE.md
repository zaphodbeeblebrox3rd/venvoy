# Docker Image Publishing Guide

## 🎯 **Overview**

venvoy now uses **pre-built Docker images** instead of building locally. This makes initialization instant and truly portable across architectures.

## 📦 **Image Architecture**

### **Base Images** (for users)
- `zaphodbeeblebrox3rd/venvoy:python3.9`
- `zaphodbeeblebrox3rd/venvoy:python3.10`
- `zaphodbeeblebrox3rd/venvoy:python3.11`
- `zaphodbeeblebrox3rd/venvoy:python3.12`
- `zaphodbeeblebrox3rd/venvoy:python3.13`
- `zaphodbeeblebrox3rd/venvoy:latest` (points to python3.11)

### **R Environment Images** (for users)
- `zaphodbeeblebrox3rd/venvoy:r4.2`
- `zaphodbeeblebrox3rd/venvoy:r4.3`
- `zaphodbeeblebrox3rd/venvoy:r4.4`
- `zaphodbeeblebrox3rd/venvoy:r4.5`

### **Bootstrap Image** (for installer)
- `zaphodbeeblebrox3rd/venvoy:bootstrap` (contains venvoy CLI)

## 🚀 **My Publishing Steps**

### **1. Set up Docker Hub Repository**

1. **Create Docker Hub account** if you don't have one
2. **Create repository**: `zaphodbeeblebrox3rd/venvoy`
3. **Set repository to public**

### **2. Configure GitHub Secrets**

Add these secrets to your GitHub repository:

```
DOCKER_USERNAME=your_docker_user_name
DOCKER_PASSWORD=your_docker_hub_token
```

To create a Docker Hub token:
1. Go to Docker Hub → Account Settings → Security
2. Create new access token with "Read, Write, Delete" permissions
3. Use the token as `DOCKER_PASSWORD`

### **3. Manual Build & Push (First Time)**

```bash
# Login to Docker Hub
docker login

# Make script executable
chmod +x scripts/build-and-push.sh

# Build and push all images (Python, R, and bootstrap)
./scripts/build-and-push.sh

# Or build specific image types:
./scripts/build-and-push.sh --python     # Only Python images
./scripts/build-and-push.sh --r          # Only R images
./scripts/build-and-push.sh --bootstrap  # Only bootstrap image
./scripts/build-and-push.sh --python --r # Python and R (no bootstrap)
```

This will (by default):
- ✅ Build multi-architecture images for Python 3.9-3.13
- ✅ Build multi-architecture images for R 4.2-4.5
- ✅ Push to Docker Hub
- ✅ Create `latest` tag pointing to Python 3.11
- ✅ Build and push bootstrap image

### **4. Automated Publishing**

After the initial setup, images are automatically built and published:

**Triggers:**
- ✅ **Push to main** - When `docker/` files change
- ✅ **GitHub Release** - When you create a release
- ✅ **Manual trigger** - Via GitHub Actions UI

**What gets built:**
- All Python versions (3.9-3.13) for `linux/amd64` and `linux/arm64`
- All R versions (4.2-4.5) for `linux/amd64` and `linux/arm64`
- Bootstrap image with venvoy CLI
- Docker Hub README automatically updated

## 🔧 **User Experience After Publishing**

### **Installation** (instant)
```bash
curl -fsSL https://raw.githubusercontent.com/zaphodbeeblebrox3rd/venvoy/main/install.sh | bash
```

### **Environment Creation** (instant)
```bash
venvoy init --python-version 3.11  # Downloads pre-built image
venvoy run                          # Instant start
```

### **What Users See:**
```
🚀 Initializing venvoy environment: my-project
📦 Setting up Python 3.11 environment...
⬇️  Downloading environment (one-time setup)...
✅ Environment ready
✅ Environment 'my-project' ready!
```

## 🎁 **Benefits of Pre-built Images**

### **For Users:**
- ✅ **Instant setup** - No building, just download and run
- ✅ **Multi-architecture** - Works on Intel, AMD, and ARM automatically
- ✅ **Consistent environments** - Same image everywhere
- ✅ **Smaller downloads** - Optimized layers and caching

### **For Development:**
- ✅ **No build complexity** - Users never see Dockerfiles
- ✅ **Centralized updates** - Update images once, all users benefit
- ✅ **Better testing** - Test the exact images users will use
- ✅ **Faster CI/CD** - No building in user workflows

## 📋 **Maintenance**

### **Updating Images:**
1. **Modify** `docker/Dockerfile.base` 
2. **Commit and push** to main branch
3. **Images automatically rebuild** via GitHub Actions

### **Adding Python Versions:**
1. **Update** `PYTHON_VERSIONS` array in `scripts/build-and-push.sh`
2. **Update** matrix in `.github/workflows/build-images.yml`
3. **Update** documentation

### **Adding R Versions:**
1. **Update** `R_VERSIONS` array in the `build_r_images()` function in `scripts/build-and-push.sh`
2. **Update** documentation

### **Testing Images:**
```bash
# Test specific version
docker run --rm -it zaphodbeeblebrox3rd/venvoy:python3.11

# Test with venvoy CLI
venvoy init --python-version 3.11
venvoy run
```

## 🔗 **Links**

- **Docker Hub**: https://hub.docker.com/r/zaphodbeeblebrox3rd/venvoy
- **GitHub Actions**: https://github.com/zaphodbeeblebrox3rd/venvoy/actions
- **Build Script**: `scripts/build-and-push.sh`
- **Dockerfile**: `docker/Dockerfile.base` 