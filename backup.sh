#!/bin/bash
# Odoo ERP Backup & Restore Script
# Usage:
#   ./backup.sh backup          → backup all databases
#   ./backup.sh restore <file>  → restore from backup file

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

backup() {
    mkdir -p "$BACKUP_DIR"
    
    echo "🔄 Backing up Odoo databases..."
    
    # Backup sewing_business database
    docker exec odoo17-db pg_dump -U odoo -Fc sewing_business > "$BACKUP_DIR/sewing_business_${TIMESTAMP}.dump"
    echo "✅ sewing_business backed up"
    
    # Backup banking database
    docker exec odoo17-db pg_dump -U odoo -Fc banking > "$BACKUP_DIR/banking_${TIMESTAMP}.dump"
    echo "✅ banking backed up"
    
    # Backup filestore (attachments)
    docker cp odoo17:/var/lib/odoo/. "$BACKUP_DIR/filestore_${TIMESTAMP}/" 2>/dev/null
    echo "✅ filestore backed up"
    
    # Create a single archive
    tar -czf "$BACKUP_DIR/odoo_full_backup_${TIMESTAMP}.tar.gz" \
        "$BACKUP_DIR/sewing_business_${TIMESTAMP}.dump" \
        "$BACKUP_DIR/banking_${TIMESTAMP}.dump" \
        "$BACKUP_DIR/filestore_${TIMESTAMP}/" 2>/dev/null
    
    echo ""
    echo "📦 Full backup: $BACKUP_DIR/odoo_full_backup_${TIMESTAMP}.tar.gz"
    echo "💡 Copy this file to your new laptop, then run: ./backup.sh restore <file>"
}

restore() {
    if [ -z "$1" ]; then
        echo "❌ Usage: ./backup.sh restore <backup_file.tar.gz>"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    echo "🔄 Restoring from $BACKUP_FILE..."
    
    # Extract
    RESTORE_DIR="/tmp/odoo_restore_$$"
    mkdir -p "$RESTORE_DIR"
    tar -xzf "$BACKUP_FILE" -C "$RESTORE_DIR"
    
    # Restore databases
    echo "📦 Restoring sewing_business database..."
    docker exec -i odoo17-db pg_restore -U odoo -d sewing_business --clean --if-exists \
        < "$RESTORE_DIR"/*/sewing_business_*.dump 2>/dev/null || \
    docker exec -i odoo17-db pg_restore -U odoo -d sewing_business --clean --if-exists \
        < "$RESTORE_DIR"/sewing_business_*.dump 2>/dev/null
    echo "✅ sewing_business restored"
    
    echo "📦 Restoring banking database..."
    docker exec -i odoo17-db pg_restore -U odoo -d banking --clean --if-exists \
        < "$RESTORE_DIR"/*/banking_*.dump 2>/dev/null || \
    docker exec -i odoo17-db pg_restore -U odoo -d banking --clean --if-exists \
        < "$RESTORE_DIR"/banking_*.dump 2>/dev/null
    echo "✅ banking restored"
    
    # Restore filestore
    if [ -d "$RESTORE_DIR/filestore_"* ] || [ -d "$RESTORE_DIR"/*/filestore_* ]; then
        docker cp "$RESTORE_DIR"/filestore_*/. odoo17:/var/lib/odoo/ 2>/dev/null || \
        docker cp "$RESTORE_DIR"/*/filestore_*/. odoo17:/var/lib/odoo/ 2>/dev/null
        echo "✅ filestore restored"
    fi
    
    rm -rf "$RESTORE_DIR"
    echo ""
    echo "🎉 Restore complete! Open http://localhost:8069"
}

case "$1" in
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    *)
        echo "Usage:"
        echo "  ./backup.sh backup              → Backup all databases"
        echo "  ./backup.sh restore <file.tar.gz> → Restore from backup"
        ;;
esac
