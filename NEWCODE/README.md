# AWS Cost AI Agent - Production Ready

**Version 3.2.0** - Internal Network Only • Vertex AI Powered

## Overview
AI-powered AWS cost monitoring with Google Cloud Vertex AI for intelligent analysis and anomaly detection.

## Features
✅ **Vertex AI Integration** - Service Account authentication (no API keys)
✅ **Internal Network Only** - Binds to 127.0.0.1 (localhost)
✅ **AI-Powered Analysis** - Cost anomaly detection with explanations
✅ **Automated Alerts** - Email notifications for cost spikes
✅ **Weekly Reports** - Executive summaries with recommendations
✅ **S3 Storage** - Automatic data persistence

## Quick Installation

### Prerequisites
- Amazon Linux 2023 / Ubuntu 20.04+ / RHEL 8+
- Python 3.11+
- Root/sudo access
- GCP Service Account JSON file
- AWS credentials (for S3)
- Datadog API keys

### Install
```bash
cd /opt
sudo git clone YOUR_REPO aws-cost-agent
cd aws-cost-agent/NEWCODE

# Run installer
sudo chmod +x deployment/scripts/install.sh
sudo ./deployment/scripts/install.sh
