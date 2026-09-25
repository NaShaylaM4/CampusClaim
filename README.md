# CampusClaim

CampusClaim is a cloud-based campus lost-and-found claim system built with Flask.

Run the one-time migration below when upgrading an existing database to add return-coordination instructions. The migration is idempotent and preserves existing records:

```powershell
python database/migrate_add_return_instructions.py
```
