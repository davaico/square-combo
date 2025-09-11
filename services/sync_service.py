"""
Sync service for handling revenue synchronization between Square and Combo.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from database.models import Client, SyncLog
from adapters.square.client import SquareClient
from adapters.combo.client import ComboClient

logger = logging.getLogger(__name__)


class SyncService:
    """Service class for revenue synchronization operations."""

    def __init__(self, db: Session):
        self.db = db

    async def sync_client_revenue(
        self, client: Client, target_date: date
    ) -> list[Dict[str, Any]]:
        """
        Sync revenue for a single client across all their locations.

        Args:
            client: Client object
            target_date: Date to sync revenue for

        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting revenue sync for client {client.id} on {target_date}")

        # Initialize API clients
        square_client = SquareClient(
            access_token=client.square_access_token,
        )
        combo_client = ComboClient(api_key=client.combo_api_key)

        try:
            # --- Current Simplified Implementation ---
            # This logic syncs the first available Square location to the first available Combo location.
            # It is intended for basic testing and demonstration.

            square_locations = await square_client.get_locations()
            if not square_locations:
                logger.warning(f"No locations found in Square for client {client.id}.")
                return [{"status": "skipped", "reason": "No locations found in Square"}]

            combo_locations = await combo_client.get_locations()
            if not combo_locations:
                logger.warning(f"No locations found in Combo for client {client.id}.")
                return [{"status": "skipped", "reason": "No locations found in Combo"}]

            mapped_locations = self.map_square_combo_locations(square_locations, combo_locations)

            result: list[dict[str, Any]] = []
            for mapped_location in mapped_locations:
                response = await self.sync_location_revenue(square_client, combo_client, mapped_location, target_date)
                self.create_sync_log(
                    client.id,
                    mapped_location.get("square_location_id"),
                    mapped_location.get("combo_location_id"),
                    mapped_location.get("square_location_name"),
                    mapped_location.get("combo_location_name"),
                    target_date,
                    response.get("status"),
                    response.get("posted_revenue"),
                    response.get("error"),
                )
                result.append(response)
            return result

        except Exception as e:
            logger.error(
                f"An error occurred during sync for client {client.id}: {e}",
                exc_info=True,
            )
            return [{"status": "failed", "error": str(e)}]

        finally:
            await square_client.close()
            await combo_client.close()

    def map_square_combo_locations(self,
                                   square_locations: list[dict[str, Any]],
                                   combo_locations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(square_locations) == 1 and len(combo_locations) == 1:
            square_location = square_locations[0]
            combo_location = combo_locations[0]
            return [{
                "square_location_id": square_location["id"],
                "square_location_name": square_location.get("name"),
                "combo_location_id": combo_location["id"],
                "combo_location_name": combo_location.get("name")
            }]

        combo_lookup = {cbl["name"]: cbl for cbl in combo_locations}

        merged: list[dict[str, Any]] = []
        for square_location in square_locations:
            name = square_location["name"]
            combo_location = combo_lookup.get(name)

            if combo_location:
                merged.append({
                    "square_location_id": square_location["id"],
                    "square_location_name": name,
                    "combo_location_id": combo_location["id"],
                    "combo_location_name": name
                })

        return merged

    async def sync_location_revenue(self,
                                    square_client: SquareClient,
                                    combo_client: ComboClient,
                                    mapped_location: dict[str, Any],
                                    target_date: date) -> dict[str, Any]:
        try:
            revenue_data = await square_client.get_daily_revenue(
                mapped_location["square_location_id"], target_date
            )
            if not revenue_data or revenue_data.get("net_sales_amount", 0) == 0:
                logger.info(
                    f"No revenue for '{mapped_location["square_location_name"]}' on {target_date}."
                )
                return {"status": "success", "posted_revenue": 0}

            net_sales = revenue_data["net_sales_amount"] / 100.0
            await combo_client.post_revenue(
                location_id=mapped_location["combo_location_id"],
                date=target_date.strftime("%Y-%m-%d"),
                amount=net_sales,
            )
            return {"status": "success", "posted_revenue": net_sales}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def create_sync_log(
        self,
        client_id: int,
        square_location_id: str,
        combo_location_id: str,
        square_location_name: str,
        combo_location_name: str,
        sync_date: date,
        status: str,
        revenue_amount: Optional[float] = None,
        error_message: Optional[str] = None,
        square_response: Optional[str] = None,
        combo_response: Optional[str] = None,
    ) -> SyncLog:
        """
        Create a sync log entry.

        Args:
            client_id: Client ID
            square_location_id: Square Location ID
            combo_location_id: Combo Location ID
            square_location_name: Square Location Name
            combo_location_name: Combo Location Name
            sync_date: Date of the synced data
            status: Sync status (success, failed, pending)
            revenue_amount: Revenue amount synced
            error_message: Error message if failed
            square_response: Square API response
            combo_response: Combo API response

        Returns:
            Created SyncLog object
        """
        logger.info(f"Creating sync log for client {client_id}, between Square location: {square_location_name} and Combo location: {combo_location_name}")
        sync_log = SyncLog(
            client_id=client_id,
            square_location_id=square_location_id,
            combo_location_id=combo_location_id,
            square_location_name=square_location_name,
            combo_location_name=combo_location_name,
            sync_date=sync_date,
            status=status,
            revenue_amount=revenue_amount,
            error_message=error_message,
            square_response=square_response,
            combo_response=combo_response,
        )
        self.db.add(sync_log)
        self.db.commit()
        self.db.refresh(sync_log)
        return sync_log
