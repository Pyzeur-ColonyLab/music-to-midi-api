# Transfer Guide - YourMT3 Checkpoint to Cloud Instance

Quick guide for transferring the checkpoint from your local machine to your cloud instance.

---

## 🚀 Recommended Method: Direct SCP Transfer

**Time**: ~2-5 minutes for 536MB

### Step 1: On Your Local Machine

```bash
# Navigate to your project directory
cd /Volumes/T7/Dyapason/instrument-recognition-app/music-to-midi-api

# Transfer amt/ directory to your instance
scp -r -i /path/to/your-key.pem amt/ ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/

# Example with real values:
# scp -r -i ~/.ssh/aws-key.pem amt/ ubuntu@54.123.45.67:/home/ubuntu/music-to-midi-api/
```

**Replace**:
- `/path/to/your-key.pem` → Your SSH private key path
- `YOUR_INSTANCE_IP` → Your instance's public IP address
- `ubuntu` → Your instance username (ubuntu for Ubuntu, ec2-user for Amazon Linux)

### Step 2: On Your Instance

```bash
# SSH into your instance
ssh -i /path/to/your-key.pem ubuntu@YOUR_INSTANCE_IP

# Navigate to project
cd /home/ubuntu/music-to-midi-api

# Verify transfer
ls -lh amt/
ls -lh amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt

# Should show ~536MB checkpoint file

# Run setup script (choose option 3 to verify)
./setup_checkpoint.sh
# Select: 3 (Already transferred via SCP/rsync)

# Continue with installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start server
python -m app.main
```

---

## 🔄 Alternative: Rsync (Better for Slow Connections)

**Benefits**: Resumable, shows progress, compresses during transfer

```bash
# From your local machine
cd /Volumes/T7/Dyapason/instrument-recognition-app/music-to-midi-api

# Transfer with rsync
rsync -avz --progress -e "ssh -i /path/to/your-key.pem" \
  amt/ \
  ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/amt/

# -a: Archive mode (preserves permissions)
# -v: Verbose
# -z: Compress during transfer
# --progress: Show progress bar
```

**If interrupted**, just run the same command again - it will resume!

---

## 📦 Alternative: Compressed Transfer (Fastest)

**Best for**: Large files, slow connections
**Time**: ~1-3 minutes

```bash
# 1. Compress on local machine
cd /Volumes/T7/Dyapason/instrument-recognition-app/music-to-midi-api
tar -czf amt.tar.gz amt/

# 2. Transfer compressed file
scp -i /path/to/your-key.pem amt.tar.gz ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/

# 3. SSH and extract on instance
ssh -i /path/to/your-key.pem ubuntu@YOUR_INSTANCE_IP
cd /home/ubuntu/music-to-midi-api
tar -xzf amt.tar.gz
rm amt.tar.gz  # Clean up

# 4. Verify
ls -lh amt/logs/2024/.../checkpoints/last.ckpt
```

---

## ☁️ Cloud Storage Method (For Multiple Instances)

If you'll deploy to multiple instances, upload once to cloud storage.

### AWS S3

**Upload (one-time, from local machine):**

```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure

# Compress and upload
cd /Volumes/T7/Dyapason/instrument-recognition-app/music-to-midi-api
tar -czf amt.tar.gz amt/
aws s3 cp amt.tar.gz s3://your-bucket-name/music-to-midi-api/amt.tar.gz

# Make private (recommended)
aws s3api put-object-acl \
  --bucket your-bucket-name \
  --key music-to-midi-api/amt.tar.gz \
  --acl private
```

**Download (on each instance):**

```bash
# On your instance
cd /home/ubuntu/music-to-midi-api

# Download from S3
aws s3 cp s3://your-bucket-name/music-to-midi-api/amt.tar.gz .

# Extract
tar -xzf amt.tar.gz
rm amt.tar.gz

# Verify
ls -lh amt/logs/2024/.../checkpoints/last.ckpt
```

### Google Cloud Storage

**Upload:**

```bash
# Install gcloud CLI
# Follow: https://cloud.google.com/sdk/docs/install

# Upload
gsutil cp amt.tar.gz gs://your-bucket-name/music-to-midi-api/
```

**Download:**

```bash
# On instance
gsutil cp gs://your-bucket-name/music-to-midi-api/amt.tar.gz .
tar -xzf amt.tar.gz
```

---

## ⚠️ Why NOT GitHub?

**Checkpoint is 535MB** - GitHub limits:
- ❌ 100MB max file size
- ❌ 1GB soft repository limit
- ❌ Git LFS costs money and is complex

**Use direct transfer instead!**

---

## 🔍 Verification Checklist

After transfer, verify everything is correct:

```bash
# On your instance
cd /home/ubuntu/music-to-midi-api

# Check amt/ directory exists
ls -ld amt/
# Should show: drwxr-xr-x ... amt/

# Check checkpoint exists
ls -lh amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt
# Should show: -rw-r--r-- ... 535M ... last.ckpt

# Check helper files
ls -lh amt/model_helper.py amt/html_helper.py
# Should show both files (~14K and ~5K)

# Check src directory
ls -ld amt/src/
# Should show: drwxr-xr-x ... amt/src/

# Run verification script
./setup_checkpoint.sh
# Select option 3: "Already transferred via SCP/rsync"
```

Expected output:
```
✅ YourMT3 checkpoint already exists
```

Or if running setup for first time:
```
🔍 Verifying transferred checkpoint...
✅ amt/ directory found
✅ Setup complete!
   Checkpoint size: 536M
```

---

## 🐛 Troubleshooting

### Transfer Hangs or Fails

```bash
# 1. Check SSH connection
ssh -i /path/to/your-key.pem ubuntu@YOUR_INSTANCE_IP

# 2. Check disk space on instance
df -h
# Need at least 1GB free

# 3. Try rsync instead (resumable)
rsync -avz --progress -e "ssh -i /path/to/your-key.pem" \
  amt/ ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/amt/
```

### Permission Denied

```bash
# Check SSH key permissions
chmod 400 /path/to/your-key.pem

# Check instance username
# Ubuntu: ubuntu
# Amazon Linux: ec2-user
# Debian: admin
```

### Checkpoint Not Found After Transfer

```bash
# SSH into instance
ssh -i /path/to/your-key.pem ubuntu@YOUR_INSTANCE_IP

# Check what was transferred
ls -R /home/ubuntu/music-to-midi-api/amt/

# Verify checkpoint path
find /home/ubuntu/music-to-midi-api/amt -name "last.ckpt"

# Should output:
# /home/ubuntu/music-to-midi-api/amt/logs/2024/.../checkpoints/last.ckpt
```

### Slow Transfer

```bash
# Use compression (faster)
rsync -avz --progress --compress-level=9 \
  -e "ssh -i /path/to/your-key.pem" \
  amt/ ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/amt/

# Or use tar+scp method (fastest)
```

---

## ⏱️ Transfer Time Estimates

| Method | Connection | Time |
|--------|-----------|------|
| SCP | 100 Mbps | ~5 minutes |
| SCP | 1 Gbps | ~30 seconds |
| Rsync (compressed) | 100 Mbps | ~3 minutes |
| Tar+SCP | 100 Mbps | ~2 minutes |
| S3 Upload | 100 Mbps | ~5 minutes |
| S3 Download (instance) | AWS network | ~10 seconds |

---

## 📝 Complete Deployment Workflow

**From scratch to running API:**

```bash
# === ON YOUR LOCAL MACHINE ===

# 1. Navigate to project
cd /Volumes/T7/Dyapason/instrument-recognition-app/music-to-midi-api

# 2. Transfer checkpoint
scp -r -i ~/.ssh/your-key.pem amt/ ubuntu@YOUR_IP:/home/ubuntu/music-to-midi-api/

# === ON YOUR INSTANCE (SSH) ===

# 3. Clone repository
git clone https://github.com/Pyzeur-ColonyLab/music-to-midi-api.git
cd music-to-midi-api

# 4. Verify checkpoint (transferred in step 2)
ls -lh amt/logs/2024/.../checkpoints/last.ckpt

# 5. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Start server
python -m app.main
```

**Total time**: ~10-15 minutes

---

## ✅ Quick Command Reference

```bash
# Basic SCP transfer
scp -r -i KEY amt/ USER@IP:/path/to/project/

# Rsync with progress
rsync -avz --progress -e "ssh -i KEY" amt/ USER@IP:/path/

# Compressed transfer
tar -czf amt.tar.gz amt/
scp -i KEY amt.tar.gz USER@IP:/path/
ssh -i KEY USER@IP "cd /path && tar -xzf amt.tar.gz && rm amt.tar.gz"

# Verify on instance
ssh -i KEY USER@IP "ls -lh /path/to/project/amt/logs/2024/.../checkpoints/last.ckpt"
```

---

**Need help?** Check [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.
