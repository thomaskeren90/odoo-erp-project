# Session Log — 2026-04-03

## Task: Install custom_coa Module into Odoo 13 Container

**Environment:**
- Host: Laptop (macOS/zsh)
- Docker containers: `odoo13` (Odoo 13.0-20221005), `odoo13-db` (PostgreSQL 13), `ollama_brain`, `n8n_matrix`
- Database: `tokoodoo13` | User: `odoo13` | Password: `odoo13`
- Addons path: `/mnt/extra-addons`

## Steps Performed

1. Verified `custom_coa` module files exist inside container:
   - `/mnt/extra-addons/custom_coa/__init__.py`
   - `/mnt/extra-addons/custom_coa/__manifest__.py` (v13.0.1.0.0)
   - `/mnt/extra-addons/custom_coa/data/chart_of_accounts.xml`
   - `/mnt/extra-addons/custom_coa/data/journals.xml`

2. Attempted CLI install — hit issues:
   - First attempt without `-d` flag used `default` DB → no DB found
   - Second attempt with `-d tokoodoo13` but no `--db_host` → tried local socket connection → failed
   - `odoo.conf` has no `db_host` setting; running Odoo instance gets DB connection from Docker environment variables

3. Final working command:
   ```bash
   docker exec odoo13 odoo -c /etc/odoo/odoo.conf \
     --db_host=odoo13-db \
     --db_user=odoo13 \
     --db_password=odoo13 \
     -d tokoodoo13 \
     -i custom_coa \
     --stop-after-init
   ```

4. Module loaded successfully:
   - `chart_of_accounts.xml` — 20 accounts (5 banks, inventory, sales, COGS, expenses)
   - `journals.xml` — 5 bank journals + 1 expense journal

5. Restarted container: `docker restart odoo13`

## Notes

- Odoo web UI "Update Apps List" only visible in Developer Mode
- CLI install is more reliable than web UI for custom modules
- Developer Mode URL: `http://localhost:8069/web?debug=1`

## Quick Reference (Future Installs)

```bash
# Install any module via CLI
docker exec odoo13 odoo -c /etc/odoo/odoo.conf \
  --db_host=odoo13-db \
  --db_user=odoo13 \
  --db_password=odoo13 \
  -d tokoodoo13 \
  -i MODULE_NAME \
  --stop-after-init

# Then restart
docker restart odoo13
```
