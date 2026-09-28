# CampusClaim

CampusClaim is a cloud-based campus lost-and-found claim system built with Flask.

For an existing database, run the additive migrations needed by its current schema. They preserve existing records and tables:

```powershell
python database/migrate_add_return_instructions.py
```

Run the LOST-report linking migration as well:

```powershell
python database/migrate_add_lost_item_id.py
```

Create the private messaging table for existing databases:

```powershell
python database/migrate_add_messages.py
```
