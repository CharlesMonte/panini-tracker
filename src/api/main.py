from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import DATA_DIR
from src.db import SessionLocal, init_db
from src.models import Person, Sticker
from src.repositories import get_people
from src.services import admin_service
from src.services.batch_service import apply_batch_add, preview_batch_add
from src.services.collection_service import (
    add_quantity,
    filter_stickers_by_kind,
    get_all_people_stats,
    get_collection_rows,
    get_person_stats,
    search_stickers,
    set_quantity,
)
from src.services.excel_import import preview_excel
from src.services.export_service import export_csv, export_excel
from src.services.exchange_service import (
    apply_batch_equivalent_trades,
    apply_batch_sales,
    apply_equivalent_trade,
    apply_sale,
    get_opportunity_summaries,
    get_sale_candidates,
    get_tradeable_stickers_between,
    preview_batch_equivalent_trades,
    preview_batch_sales,
)
from src.services.import_service import run_excel_import, run_source_names_import
from src.services.undo_service import get_recent_actions, undo_action, undo_batch



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Panini Tracker API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _bad_request(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _person_row(person: Person) -> dict:
    return {
        "id": person.id,
        "name": person.name,
        "display_order": person.display_order,
        "active": person.active,
    }


def _sticker_row(sticker: Sticker) -> dict:
    return {
        "id": sticker.id,
        "album_order": sticker.album_order,
        "raw_category": sticker.raw_category,
        "category_code": sticker.category_code,
        "category_name": sticker.category_name,
        "sticker_number": sticker.sticker_number,
        "sticker_code": sticker.sticker_code,
        "display_code": sticker.display_code,
        "player_name": sticker.player_name,
        "team_name": sticker.team_name,
        "label": sticker.label,
        "is_foil": sticker.is_foil,
        "is_team_photo": sticker.is_team_photo,
        "is_emblem": sticker.is_emblem,
        "source": sticker.source,
    }


class ActorPayload(BaseModel):
    actor_name: str | None = None


class PersonCreate(BaseModel):
    name: str
    display_order: int | None = None
    actor_name: str | None = None


class PersonPatch(BaseModel):
    active: bool | None = None
    display_order: int | None = None
    actor_name: str | None = None


class DeletePersonPayload(ActorPayload):
    confirm_name: str


class StickerPatch(BaseModel):
    sticker_code: str
    album_order: int
    category_code: str | None = None
    category_name: str | None = None
    player_name: str | None = None
    team_name: str | None = None
    label: str | None = None
    is_foil: bool = False
    is_team_photo: bool = False
    is_emblem: bool = False
    actor_name: str | None = None


class DeleteStickerPayload(ActorPayload):
    confirm_code: str


class QuantityPayload(ActorPayload):
    person_id: int
    sticker_id: int
    delta: int | None = None
    quantity: int | None = None


class BatchCodesPayload(ActorPayload):
    person_id: int
    raw_codes: str
    items: list[dict[str, Any]] | None = None


class TradeApplyPayload(ActorPayload):
    person_a_id: int
    person_b_id: int
    sticker_from_a_id: int
    sticker_from_b_id: int


class TradeBatchPreviewPayload(BaseModel):
    person_a_id: int
    person_b_id: int
    raw_codes_from_a: str
    raw_codes_from_b: str


class TradeBatchApplyPayload(ActorPayload):
    person_a_id: int
    person_b_id: int
    pairs: list[dict[str, Any]]


class SaleApplyPayload(ActorPayload):
    seller_id: int
    buyer_id: int
    sticker_id: int
    price: float | None = None


class SaleBatchPreviewPayload(BaseModel):
    seller_id: int
    buyer_id: int
    raw_codes: str


class SaleBatchApplyPayload(ActorPayload):
    seller_id: int
    buyer_id: int
    items: list[dict[str, Any]]


class UndoPayload(ActorPayload):
    action_id: int


class UndoBatchPayload(ActorPayload):
    batch_id: str


class ExcelPathPayload(BaseModel):
    path: str = "source_excel.xlsx"


class SourceNamesPayload(BaseModel):
    path: str = "source_names.txt"


class EnsureHoldingsPayload(ActorPayload):
    include_inactive: bool = True


class PurgePayload(BaseModel):
    confirm_text: str
    actor_name: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/people")
def people(db: Session = Depends(get_db), active_only: bool = True) -> list[dict]:
    return [_person_row(person) for person in get_people(db, active_only=active_only)]


@app.post("/people")
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> dict:
    try:
        return _person_row(admin_service.create_person(db, payload.name, payload.display_order, payload.actor_name))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.patch("/people/{person_id}")
def patch_person(person_id: int, payload: PersonPatch, db: Session = Depends(get_db)) -> dict:
    try:
        if payload.active is not None:
            admin_service.set_person_active(db, person_id, payload.active, payload.actor_name)
        if payload.display_order is not None:
            admin_service.update_person_display_order(db, person_id, payload.display_order, payload.actor_name)
        person = db.get(Person, person_id)
        if person is None:
            raise ValueError("Personne introuvable.")
        return _person_row(person)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.delete("/people/{person_id}")
def remove_person(person_id: int, payload: DeletePersonPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return {"deleted_name": admin_service.delete_person(db, person_id, payload.confirm_name, payload.actor_name)}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db), tracked_person_id: int | None = None) -> dict:
    people_rows = [_person_row(person) for person in get_people(db)]
    stickers_total = db.scalar(select(Sticker).count()) if False else len(search_stickers(db, ""))
    stats = get_all_people_stats(db)
    exchanges, sales = get_opportunity_summaries(db, limit=6)
    tracked = tracked_person_id or (people_rows[0]["id"] if people_rows else None)
    tracked_stats = get_person_stats(db, tracked) if tracked else None
    return {
        "people": people_rows,
        "stickers_total": stickers_total,
        "stats": stats,
        "exchange_summaries": exchanges,
        "sale_summaries": sales,
        "tracked_person_id": tracked,
        "tracked_stats": tracked_stats,
    }


@app.get("/stickers")
def stickers(
    db: Session = Depends(get_db),
    query: str = "",
    category: str | None = None,
    kind: str = "Tous",
    limit: int = Query(default=1000, ge=1, le=5000),
) -> list[dict]:
    rows = search_stickers(db, query, category)
    rows = filter_stickers_by_kind(rows, kind)
    return rows[:limit]


@app.get("/stickers/{sticker_id}")
def sticker(sticker_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(Sticker, sticker_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Sticker introuvable.")
    return _sticker_row(item)


@app.patch("/stickers/{sticker_id}")
def patch_sticker(sticker_id: int, payload: StickerPatch, db: Session = Depends(get_db)) -> dict:
    try:
        item = admin_service.update_sticker_metadata(db, sticker_id, **payload.model_dump())
        return _sticker_row(item)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.delete("/stickers/{sticker_id}")
def remove_sticker(sticker_id: int, payload: DeleteStickerPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return {"deleted_code": admin_service.delete_sticker(db, sticker_id, payload.confirm_code, payload.actor_name)}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/collection/{person_id}")
def collection(
    person_id: int,
    db: Session = Depends(get_db),
    status: str = "Tous",
    category: str | None = None,
) -> list[dict]:
    return get_collection_rows(db, person_id, status, category)


@app.get("/collection/{person_id}/stats")
def collection_stats(person_id: int, db: Session = Depends(get_db)) -> dict:
    return get_person_stats(db, person_id)


@app.post("/collection/quantity")
def update_quantity(payload: QuantityPayload, db: Session = Depends(get_db)) -> dict:
    try:
        if payload.quantity is not None:
            holding = set_quantity(db, payload.person_id, payload.sticker_id, payload.quantity, payload.actor_name)
        elif payload.delta is not None:
            holding = add_quantity(db, payload.person_id, payload.sticker_id, payload.delta, payload.actor_name)
        else:
            raise ValueError("Indiquez delta ou quantity.")
        return {"person_id": holding.person_id, "sticker_id": holding.sticker_id, "quantity": holding.quantity}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/collection/batch-preview")
def collection_batch_preview(payload: BatchCodesPayload, db: Session = Depends(get_db)) -> dict:
    return preview_batch_add(db, payload.person_id, payload.raw_codes)


@app.post("/collection/batch-apply")
def collection_batch_apply(payload: BatchCodesPayload, db: Session = Depends(get_db)) -> dict:
    try:
        items = payload.items or preview_batch_add(db, payload.person_id, payload.raw_codes)["items"]
        return apply_batch_add(db, payload.person_id, items, payload.actor_name)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/trades/options")
def trade_options(
    db: Session = Depends(get_db),
    person_a_id: int | None = None,
    person_b_id: int | None = None,
) -> dict:
    if not person_a_id or not person_b_id:
        return {"a_to_b": [], "b_to_a": []}
    return {
        "a_to_b": get_tradeable_stickers_between(db, person_a_id, person_b_id),
        "b_to_a": get_tradeable_stickers_between(db, person_b_id, person_a_id),
    }


@app.post("/trades/preview-batch")
def trade_batch_preview(payload: TradeBatchPreviewPayload, db: Session = Depends(get_db)) -> dict:
    return preview_batch_equivalent_trades(
        db,
        payload.person_a_id,
        payload.person_b_id,
        payload.raw_codes_from_a,
        payload.raw_codes_from_b,
    )


@app.post("/trades/apply")
def trade_apply(payload: TradeApplyPayload, db: Session = Depends(get_db)) -> dict:
    try:
        trade = apply_equivalent_trade(
            db,
            payload.person_a_id,
            payload.person_b_id,
            payload.sticker_from_a_id,
            payload.sticker_from_b_id,
            payload.actor_name,
        )
        return {"trade_id": trade.id, "status": trade.status}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/trades/apply-batch")
def trade_batch_apply(payload: TradeBatchApplyPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return apply_batch_equivalent_trades(db, payload.person_a_id, payload.person_b_id, payload.pairs, payload.actor_name)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/sales/options")
def sales_options(
    db: Session = Depends(get_db),
    seller_id: int | None = None,
    buyer_id: int | None = None,
) -> list[dict]:
    return get_sale_candidates(db, seller_id=seller_id, buyer_id=buyer_id)


@app.post("/sales/preview-batch")
def sales_batch_preview(payload: SaleBatchPreviewPayload, db: Session = Depends(get_db)) -> dict:
    return preview_batch_sales(db, payload.seller_id, payload.buyer_id, payload.raw_codes)


@app.post("/sales/apply")
def sales_apply(payload: SaleApplyPayload, db: Session = Depends(get_db)) -> dict:
    try:
        apply_sale(db, payload.seller_id, payload.buyer_id, payload.sticker_id, payload.actor_name, payload.price)
        return {"status": "applied"}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/sales/apply-batch")
def sales_batch_apply(payload: SaleBatchApplyPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return apply_batch_sales(db, payload.seller_id, payload.buyer_id, payload.items, payload.actor_name)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.get("/catalog")
def catalog(
    db: Session = Depends(get_db),
    query: str = "",
    category: str | None = None,
    kind: str = "Tous",
) -> list[dict]:
    return stickers(db, query=query, category=category, kind=kind, limit=5000)


@app.get("/history")
def history(db: Session = Depends(get_db), limit: int = Query(default=200, ge=1, le=1000)) -> list[dict]:
    return get_recent_actions(db, limit=limit)


@app.post("/history/undo")
def history_undo(payload: UndoPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return undo_action(db, payload.action_id, payload.actor_name)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.post("/history/undo-batch")
def history_undo_batch(payload: UndoBatchPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return undo_batch(db, payload.batch_id, payload.actor_name)
    except ValueError as exc:
        raise _bad_request(exc) from exc


def _uploaded_excel_path(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "upload.xlsx").suffix or ".xlsx"
    with NamedTemporaryFile(delete=False, suffix=suffix, dir=DATA_DIR / "input") as tmp:
        tmp.write(upload.file.read())
        return Path(tmp.name)


@app.post("/imports/excel/preview")
def imports_excel_preview(
    db: Session = Depends(get_db),
    path: str = Form(default="source_excel.xlsx"),
    file: UploadFile | None = File(default=None),
) -> dict:
    try:
        source_path = _uploaded_excel_path(file) if file else Path(path)
        preview = preview_excel(source_path)
        return {
            "sheet_name": preview.sheet_name,
            "sticker_count": preview.sticker_count,
            "people_names": preview.people_names,
            "ignored_rows": len(preview.ignored_rows),
            "path": str(source_path),
        }
    except Exception as exc:
        raise _bad_request(exc) from exc


@app.post("/imports/excel/apply")
def imports_excel_apply(payload: ExcelPathPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return run_excel_import(db, payload.path)
    except Exception as exc:
        raise _bad_request(exc) from exc


@app.post("/imports/source-names")
def imports_source_names(payload: SourceNamesPayload, db: Session = Depends(get_db)) -> dict:
    try:
        return run_source_names_import(db, payload.path)
    except Exception as exc:
        raise _bad_request(exc) from exc


@app.get("/exports/csv")
def exports_csv(db: Session = Depends(get_db)) -> FileResponse:
    path = DATA_DIR / "exports" / f"panini_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return FileResponse(export_csv(db, path), filename=path.name, media_type="text/csv")


@app.get("/exports/excel")
def exports_excel(db: Session = Depends(get_db)) -> FileResponse:
    path = DATA_DIR / "exports" / f"panini_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return FileResponse(
        export_excel(db, path),
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/admin/overview")
def admin_overview(db: Session = Depends(get_db)) -> dict:
    return {
        "overview": admin_service.get_database_overview(db),
        "people": admin_service.get_people_admin_rows(db),
        "categories": admin_service.get_category_admin_rows(db),
        "actions": admin_service.get_action_type_rows(db),
        "imports": admin_service.get_import_admin_rows(db, limit=200),
    }


@app.post("/admin/ensure-holdings")
def admin_ensure_holdings(payload: EnsureHoldingsPayload, db: Session = Depends(get_db)) -> dict:
    return admin_service.ensure_full_holdings_matrix(db, payload.include_inactive, payload.actor_name)


@app.delete("/admin/imports")
def admin_purge_imports(payload: PurgePayload, db: Session = Depends(get_db)) -> dict:
    try:
        return {"deleted": admin_service.purge_import_runs(db, payload.confirm_text, payload.actor_name)}
    except ValueError as exc:
        raise _bad_request(exc) from exc


@app.delete("/admin/history")
def admin_purge_history(payload: PurgePayload, db: Session = Depends(get_db)) -> dict:
    try:
        return {"deleted": admin_service.purge_action_log(db, payload.confirm_text)}
    except ValueError as exc:
        raise _bad_request(exc) from exc
