# Finance Automation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task if we decide to harden this beyond the current prototype.

**Goal:** Build a pleasant, local-first finance ingestion workflow where Patryk can send bank exports/receipts from iPhone or Mac into an iCloud Drive inbox and Florian imports or stages them automatically.

**Architecture:** Apple Shortcuts handles the human side: share-sheet capture, bank label, file rename, save to iCloud Drive. A macOS watcher processes the synced folder, imports known CSVs into the encrypted finance DB, archives originals, and leaves PDFs/images for OCR/manual review. Open Banking connectors remain optional later.

**Tech Stack:** Apple Shortcuts, iCloud Drive, Python stdlib, existing `finance_db.py`, launchd, macOS Keychain-backed finance encryption.

---

## Phase 1: Capture and import MVP

### Task 1: Create Finance Inbox folder

**Objective:** Ensure the iCloud Drive inbox exists and is visible on iPhone/Mac.

**Files:**
- Directory: `~/Library/Mobile Documents/com~apple~CloudDocs/Finance Inbox`

**Command:**
```bash
mkdir -p "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Finance Inbox"
```

**Verify:** Folder appears in Finder under iCloud Drive.

### Task 2: Use existing watcher prototype

**Objective:** Process files from the Finance Inbox.

**Files:**
- Created: `/Volumes/T7/hermes/scripts/finance-inbox/finance_inbox_watcher.py`
- Created: `/Volumes/T7/hermes/scripts/finance-inbox/README.md`
- Created: `/Volumes/T7/hermes/scripts/finance-inbox/com.florian.finance-inbox.plist`

**Run:**
```bash
python3 /Volumes/T7/hermes/scripts/finance-inbox/finance_inbox_watcher.py --once --dry-run
```

**Expected:** JSON list of skipped/processable files, no imports performed.

### Task 3: Initialize finance DB encryption

**Objective:** Ensure imports do not leave sensitive transaction data unencrypted.

**Files:**
- Uses: `/Volumes/T7/hermes/skills/openclaw-imports/financial-management/scripts/finance_db.py`

**Command:**
```bash
python3 /Volumes/T7/hermes/skills/openclaw-imports/finance-tracker/scripts/finance_init.py
```

**Verify:** Keychain item `clawdbot-finance-encryption` exists and `finance_db.py stats` runs.

### Task 4: Build Apple Shortcut

**Objective:** Let Patryk share exports from iPhone/Mac into the inbox.

**Shortcut:** `Send Finance Export to Florian`

**Actions:** See `/Volumes/T7/hermes/scripts/finance-inbox/README.md`.

**Verify:** Share a dummy file, choose `revolut`, and confirm it appears as `revolut_YYYY-MM-DD_HHMMSS_*` in iCloud Drive Finance Inbox.

### Task 5: Test one real CSV

**Objective:** Confirm end-to-end import with one safe export.

**Steps:**
1. Export a Revolut/ING/bunq CSV.
2. Use the Shortcut to save it.
3. Run watcher once.
4. Run finance stats.

**Commands:**
```bash
python3 /Volumes/T7/hermes/scripts/finance-inbox/finance_inbox_watcher.py --once
python3 /Volumes/T7/hermes/skills/openclaw-imports/financial-management/scripts/finance_db.py stats
```

**Expected:** CSV is archived; transaction count increases; DB is re-encrypted.

## Phase 2: Make it nice

### Task 6: Add OCR/PDF staging report

**Objective:** When PDF/screenshots arrive, generate a short review queue instead of silently archiving.

**Implementation idea:** Add `pending_review.jsonl` in `/Volumes/T7/hermes/cache/finance/` with file path, source bank, timestamp, and reason.

### Task 7: Add daily finance inbox cron/launchd summary

**Objective:** Tell Patryk if files were imported, failed, or need review.

**Implementation idea:** launchd runs watcher every 5 minutes; a Hermes cron sends a daily short summary only when there is activity.

### Task 8: Add bank-specific export guides

**Objective:** Reduce friction by documenting exact export taps for ING, Revolut, bunq, AmEx.

**Files:**
- Create: `/Volumes/T7/hermes/scripts/finance-inbox/guides/revolut.md`
- Create: `/Volumes/T7/hermes/scripts/finance-inbox/guides/ing.md`
- Create: `/Volumes/T7/hermes/scripts/finance-inbox/guides/bunq.md`
- Create: `/Volumes/T7/hermes/scripts/finance-inbox/guides/amex.md`

## Phase 3: Optional live-ish connectors

### Task 9: bunq direct API

**Objective:** Add true API sync for bunq personal accounts if Patryk has an eligible plan.

**Use:** Existing finance-tracker bunq scripts, but audit before enabling.

### Task 10: Open Banking provider spike

**Objective:** Test Salt Edge/Enable Banking/GoCardless only after MVP works.

**Success criterion:** We can connect one personal ING/Revolut account with read-only AIS, store tokens in Keychain, and sync without exposing raw data to third-party AI services.
