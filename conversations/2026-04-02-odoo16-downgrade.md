# Conversation Log - 2026-04-02

## Topic: Odoo 17 → 16 Downgrade + Chart of Accounts Setup

### Problem
- Odoo 17 Community Edition locks accounting features behind Enterprise subscription
- Both "Accounting" and "Invoicing" modules require paid subscription in CE 17
- User needed free accounting solution

### Decision: Downgrade to Odoo 16 CE
- Odoo 16 Community has full free accounting (COA, journals, reconciliation, reports)
- Only bank auto-sync requires Enterprise — manual entries work fine

### Changes Made

#### 1. docker-compose.yml
- `image: odoo:17.0` → `image: odoo:16.0`
- `container_name: odoo17` → `container_name: odoo16`
- `container_name: odoo17-db` → `container_name: odoo16-db`

#### 2. Custom Chart of Accounts Module (`addons/custom_coa/`)
Created a full COA module with:

**5 Banks (1110xx)**
| Code | Account |
|------|---------|
| 111001 | Bank BCA |
| 111002 | Bank Mandiri |
| 111003 | Bank BNI |
| 111004 | Bank BRI |
| 111005 | Bank CIMB Niaga |

**Inventory (1120xx)**
| Code | Account |
|------|---------|
| 112001 | Persediaan Barang |

**Sales Revenue (4100xx)**
| Code | Account |
|------|---------|
| 410001 | Pendapatan Penjualan Produk |
| 410002 | Pendapatan Jasa |

**Purchase / COGS (5100xx)**
| Code | Account |
|------|---------|
| 510001 | Harga Pokok Penjualan |
| 510002 | Pembelian Barang |

**Expenses - Toko (6110xx)**
| Code | Account |
|------|---------|
| 611001 | Beban Sewa Toko |
| 611002 | Beban Listrik Toko |
| 611003 | Beban Operasional Toko |
| 611004 | Beban Gaji Karyawan Toko |

**Expenses - Pribadi (6120xx)**
| Code | Account |
|------|---------|
| 612001 | Beban Hidup Pribadi |
| 612002 | Beban Transportasi Pribadi |
| 612003 | Beban Lainnya Pribadi |

**Expenses - Kos (6130xx)**
| Code | Account |
|------|---------|
| 613001 | Beban Sewa Kos |
| 613002 | Beban Listrik Kos |
| 613003 | Beban Air Kos |
| 613004 | Beban Perawatan Kos |

**Journals Created:**
- BCA (Bank), MANDIRI (Bank), BNI (Bank), BRI (Bank), CIMB (Bank)
- EXP (General - Expense)

### Setup Instructions for User
```bash
# On laptop after pulling from GitHub:
git pull
docker compose down -v
docker compose up -d
```

Then in browser (http://localhost:8069):
1. Create database (Country: Indonesia)
2. Install Invoicing module (free in Odoo 16)
3. Apps → search "Custom Chart" → Install
4. Accounting → Chart of Accounts → verify 18 accounts

### Security Note
- GitHub PAT was shared in chat — user advised to revoke and create new token
- Token was used only to clone, edit, and push to thomaskeren90/odoo-erp-project

### Status
- ✅ GitHub repo updated with Odoo 16 + custom COA module
- ✅ User running `docker compose up -d` on laptop
- ⏳ Waiting for user to confirm setup works
