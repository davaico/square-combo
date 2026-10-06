"""Fail closed on ambiguous mapping and persist every attempted location result."""

import logging
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy.orm import Session

from adapters.combo.client import ComboClient
from adapters.square.client import SquareClient
from database.models import Client, LocationMapping, SyncLog
from utils.config import settings
from utils.http import safe_error

logger = logging.getLogger(__name__)


class MappingError(ValueError):
    pass


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    def map_square_combo_locations(
        self,
        square_locations: list[dict],
        combo_locations: list[dict],
        client_id: int | None = None,
    ) -> list[dict]:
        if not square_locations or not combo_locations:
            raise MappingError("No active source or destination locations")
        squares = {location["id"]: location for location in square_locations}
        combos = {location["id"]: location for location in combo_locations}
        if len(squares) != len(square_locations) or len(combos) != len(combo_locations):
            raise MappingError("Duplicate provider location IDs")
        explicit = (
            self.db.query(LocationMapping).filter_by(client_id=client_id).all()
            if client_id is not None
            else []
        )
        pairs = {mapping.square_location_id: mapping.combo_location_id for mapping in explicit}
        if pairs and (set(pairs) - set(squares) or set(pairs.values()) - set(combos)):
            raise MappingError("Stored location mapping refers to unavailable locations")
        names = {}
        for combo in combo_locations:
            name = combo.get("name", "").strip().casefold()
            if name in names:
                names[name] = None  # ambiguous names never choose an arbitrary location
            else:
                names[name] = combo["id"]
        used = set()
        result = []
        for square in square_locations:
            combo_id = pairs.get(square["id"])
            if combo_id is None:
                name = square.get("name", "").strip().casefold()
                combo_id = names.get(name) if name else None
                if (
                    not combo_id
                    and settings.ALLOW_SINGLE_LOCATION_MAPPING
                    and len(squares) == len(combos) == 1
                ):
                    combo_id = next(iter(combos))
            if not combo_id or combo_id in used:
                raise MappingError(
                    "Unmapped or ambiguous location; configure explicit unique mappings"
                )
            used.add(combo_id)
            result.append(
                {
                    "square_location_id": square["id"],
                    "combo_location_id": combo_id,
                    "square_location_name": square.get("name"),
                    "combo_location_name": combos[combo_id].get("name"),
                }
            )
        return result

    async def sync_client_revenue(self, client: Client, target_date: date) -> list[dict]:
        try:
            async with (
                SquareClient(client.square_access_token) as square,
                ComboClient(client.combo_api_key) as combo,
            ):
                mapped = self.map_square_combo_locations(
                    await square.get_locations(), await combo.get_locations(), client.id
                )
                results = []
                for location in mapped:
                    result = await self.sync_location_revenue(square, combo, location, target_date)
                    try:
                        log = self.create_sync_log(client.id, location, target_date, result)
                        result["sync_log_id"] = log.id
                    except Exception as error:
                        self.db.rollback()
                        result = {
                            "status": "failed",
                            "error": f"Audit write failed: {safe_error(error)}",
                        }
                    results.append(result)
                return results
        except Exception as error:
            self.db.rollback()
            reason = str(error) if isinstance(error, MappingError) else safe_error(error)
            logger.warning("Client %d synchronization failed: %s", client.id, reason)
            return [{"status": "failed", "error": reason}]

    async def sync_location_revenue(
        self, square: SquareClient, combo: ComboClient, location: dict, target_date: date
    ) -> dict:
        try:
            revenue = await square.get_daily_revenue(location["square_location_id"], target_date)
            if revenue is None:
                raise ValueError("Missing revenue response")
            minor_units = revenue["net_sales_amount"]
            if (
                not isinstance(minor_units, int)
                or isinstance(minor_units, bool)
                or revenue["currency"] != settings.REVENUE_CURRENCY
            ):
                raise ValueError("Invalid revenue amount or currency")
            amount = Decimal(minor_units) / Decimal(100)
            if abs(amount) >= Decimal("100000000"):
                raise ValueError("Revenue exceeds audit amount capacity")
            # A valid zero is an update too; negative refund-only days are supported.
            await combo.post_revenue(location["combo_location_id"], target_date.isoformat(), amount)
            return {"status": "success", "posted_revenue": amount}
        except Exception as error:
            return {"status": "failed", "error": safe_error(error)}

    def create_sync_log(
        self, client_id: int, location: dict, target_date: date, result: dict
    ) -> SyncLog:
        log = SyncLog(
            client_id=client_id,
            **location,
            sync_date=datetime.combine(target_date, time()),
            status=result["status"],
            revenue_amount=result.get("posted_revenue"),
            error_message=result.get("error"),
        )
        self.db.add(log)
        try:
            self.db.commit()
            self.db.refresh(log)
        except Exception:
            self.db.rollback()
            raise
        return log
