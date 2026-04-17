#!/usr/bin/env python3
"""
Invoice/Receipt to Odoo 13 — Standalone Processor
Watches a folder for new images, extracts data via Ollama vision,
posts to Odoo 13 (AP, Inventory, Expenses).
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from extract import extract_invoice_data
from post_odoo import OdooPoster

# ─── Config ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

WATCH_FOLDER = os.getenv("WATCH_FOLDER", "/mnt/c/Users/kusum/Downloads")
PROCESSED_FOLDER = os.path.join(WATCH_FOLDER, "processed")
FAILED_FOLDER = os.path.join(WATCH_FOLDER, "failed")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# ─── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("invoice-to-odoo.log"),
    ],
)
log = logging.getLogger("invoice-to-odoo")


# ─── Image Handler ────────────────────────────────────────────────
class InvoiceHandler(FileSystemEventHandler):
    """Watches for new images and processes them."""

    def __init__(self):
        self.poster = OdooPoster()
        os.makedirs(PROCESSED_FOLDER, exist_ok=True)
        os.makedirs(FAILED_FOLDER, exist_ok=True)

    def on_created(self, event):
        if event.is_directory:
            return
        ext = Path(event.src_path).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            return
        # Wait briefly for file to finish writing
        time.sleep(2)
        self.process(event.src_path)

    def on_modified(self, event):
        # Some downloaders create then rename — handle renames too
        if event.is_directory:
            return
        ext = Path(event.src_path).suffix.lower()
        if ext not in IMAGE_EXTENSIONS:
            return
        time.sleep(1)
        self.process(event.src_path)

    def process(self, image_path: str):
        """Extract from image and post to Odoo."""
        fname = os.path.basename(image_path)
        log.info(f"📸 New image detected: {fname}")

        # Skip if already in processed/failed
        if PROCESSED_FOLDER in image_path or FAILED_FOLDER in image_path:
            return

        try:
            # ── Step 1: Extract with Ollama Vision ──
            log.info(f"🔍 Extracting data from {fname}...")
            data = extract_invoice_data(image_path)

            if not data:
                raise ValueError("No data extracted from image")

            # Save extracted data as JSON alongside
            json_path = os.path.join(
                PROCESSED_FOLDER,
                os.path.splitext(fname)[0] + ".json",
            )
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log.info(f"✅ Extracted data saved: {json_path}")

            # ── Step 2: Post to Odoo ──
            log.info(f"📤 Posting to Odoo...")
            result = self.poster.post(data, image_path)

            log.info(f"✅ Posted to Odoo: {result}")

            # ── Step 3: Move image to processed ──
            dest = os.path.join(PROCESSED_FOLDER, fname)
            # Handle duplicates
            i = 1
            while os.path.exists(dest):
                base, ext = os.path.splitext(fname)
                dest = os.path.join(PROCESSED_FOLDER, f"{base}_{i}{ext}")
                i += 1
            os.rename(image_path, dest)
            log.info(f"📁 Moved to processed: {os.path.basename(dest)}")

        except Exception as e:
            log.error(f"❌ Failed to process {fname}: {e}")
            try:
                dest = os.path.join(FAILED_FOLDER, fname)
                os.rename(image_path, dest)
                log.info(f"📁 Moved to failed: {fname}")
            except Exception:
                pass


# ─── Main ─────────────────────────────────────────────────────────
def process_existing():
    """Process any images already in the watch folder."""
    log.info(f"📂 Scanning existing files in {WATCH_FOLDER}...")
    count = 0
    for f in sorted(Path(WATCH_FOLDER).iterdir()):
        if f.suffix.lower() in IMAGE_EXTENSIONS:
            count += 1
            handler = InvoiceHandler()
            handler.process(str(f))
    if count == 0:
        log.info("📂 No existing images found.")
    else:
        log.info(f"📂 Processed {count} existing images.")


def watch():
    """Watch folder for new images."""
    handler = InvoiceHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_FOLDER, recursive=False)
    observer.start()
    log.info(f"👁️  Watching {WATCH_FOLDER} for new images...")
    log.info("   Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("🛑 Stopping watcher...")
        observer.stop()
    observer.join()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Process existing files then exit
        process_existing()
    else:
        # First process existing, then watch
        process_existing()
        watch()


if __name__ == "__main__":
    main()
