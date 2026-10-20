from __future__ import annotations
import json
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import CatalogCategory, CatalogItem

CATEGORY_NAMES = {
    "Oblast": "Oblasti podpory", "Cinnost": "Činnosti", "Forma": "Forma kontaktu", "Misto": "Místo podpory",
    "Metoda": "Způsob práce", "Jazyk": "Jazyk kontaktu", "Vysledek": "Výsledek podpory",
    "DalsiKrok": "Navazující krok", "Pokrok": "Hodnocení pokroku", "NavaznaSluzba": "Návazná služba"
}

def seed_catalog(db: Session, path: str | Path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    existing_cats = {x.key for x in db.scalars(select(CatalogCategory)).all()}
    for i, key in enumerate(CATEGORY_NAMES, start=1):
        if key not in existing_cats:
            db.add(CatalogCategory(key=key, name=CATEGORY_NAMES[key], sort_order=i))
    existing = {x.item_id: x for x in db.scalars(select(CatalogItem)).all()}
    for row in data:
        item = existing.get(row["PolozkaID"])
        if item:
            continue
        db.add(CatalogItem(
            item_id=row["PolozkaID"], category_key=row["Kategorie"], parent_item_id=row.get("NadrazenaID") or None,
            name=row["Nazev"], sort_order=int(row.get("Poradi") or 0), active=bool(row.get("Aktivni", True)), visible=True,
        ))
    db.commit()
