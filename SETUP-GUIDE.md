# Odoo CE 16 Setup Guide

## Quick Start

```bash
cd /root/.openclaw/workspace/odoo-erp-project
docker-compose up -d
```

Then open: **http://localhost:8069**

## First Run Setup

### 1. Create Master Password
- Default: `admin` (change this on first login!)

### 2. Create First Database: Sewing Machine Business
- Database Name: `sewing_business`
- Email: your email
- Password: set a strong one
- Language: Indonesian
- Country: Indonesia
- Demo data: No (fresh books)

### 3. Create Second Database: Banking
- Database Name: `banking`
- Same credentials
- Language: Indonesian
- Country: Indonesia
- Demo data: No

### 4. Initial Configuration (per database)
- [ ] Set company name & details
- [ ] Install modules: Accounting, Invoicing, Inventory
- [ ] Configure Chart of Accounts (Indonesian template)
- [ ] Set currency to IDR
- [ ] Configure bank journals
- [ ] Set fiscal year

## Useful Commands

```bash
# Start Odoo
docker-compose up -d

# Stop Odoo
docker-compose down

# View logs
docker logs -f odoo16

# Backup database
docker exec odoo16-db pg_dump -U odoo sewing_business > backup_sewing.sql

# Access Odoo shell
docker exec -it odoo16 odoo shell
```

## File Structure
```
odoo-erp-project/
├── docker-compose.yml     # Docker setup
├── config/
│   └── odoo.conf          # Odoo configuration
├── addons/                # Custom modules go here
├── backups/               # Database backups
├── docs/                  # Documentation
└── conversations/         # Chat history
```
