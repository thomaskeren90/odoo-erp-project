# GitHub Push Guide

## Setup (First Time)
1. Create a new repo on GitHub (e.g., `odoo-erp-project`)
2. Run these commands:

```bash
cd /root/.openclaw/workspace/odoo-erp-project

# Initialize git
git init
git add .
git commit -m "Initial project setup"

# Add remote (replace YOUR_USERNAME and YOUR_REPO)
git remote add origin https://YOUR_USERNAME:YOUR_PAT@github.com/YOUR_USERNAME/odoo-erp-project.git

# Push
git branch -M main
git push -u origin main
```

## Regular Updates
After I make changes to project files:
```bash
cd /root/.openclaw/workspace/odoo-erp-project
git add .
git commit -m "Update: [describe changes]"
git push
```

## What Gets Saved
- `README.md` — project vision, requirements, phases
- `conversations/` — our discussion logs
- `docs/` — technical documentation
- `docker-compose.yml` — Odoo deployment config (when ready)
- `custom-addons/` — any custom modules we build
