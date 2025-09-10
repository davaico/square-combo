"""
Sync service for handling revenue synchronization between Square and Combo.
"""

import logging
from datetime import date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from database.models import Client, Location, SyncLog
from adapters.square.client import SquareClient
from adapters.combo.client import ComboClient

logger = logging.getLogger(__name__)


class SyncService:
    """Service class for revenue synchronization operations."""

    def __init__(self, db: Session):
        self.db = db

    async def sync_client_revenue(
        self, client: Client, target_date: date
    ) -> Dict[str, Any]:
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
                return {"status": "skipped", "reason": "No locations found in Square"}
            square_location = square_locations[0]

            combo_locations = await combo_client.get_locations()
            if not combo_locations:
                logger.warning(f"No locations found in Combo for client {client.id}.")
                return {"status": "skipped", "reason": "No locations found in Combo"}
            combo_location = combo_locations[0]

            revenue_data = await square_client.get_daily_revenue(
                square_location["id"], target_date
            )
            if not revenue_data or revenue_data.get("net_sales_amount", 0) == 0:
                logger.info(
                    f"No revenue for '{square_location['name']}' on {target_date}."
                )
                return {"status": "success", "posted_revenue": 0}

            net_sales = revenue_data["net_sales_amount"] / 100.0
            await combo_client.post_revenue(
                location_id=combo_location["id"],
                date=target_date.strftime("%Y-%m-%d"),
                amount=net_sales,
            )
            logger.info(
                f"Successfully synced {net_sales} from '{square_location['name']}' to '{combo_location['name']}'."
            )
            return {"status": "success", "posted_revenue": net_sales}

            # --- Future Robust Implementation (example to be tested later) ---
            # This is the intended final logic that should be used in production.
            # It relies on a database mapping of locations.

            # # Step 1: Fetch mapped locations for the client from the database
            # mapped_locations = self.db.query(Location).filter(Location.client_id == client.id, Location.is_active == True).all()
            # if not mapped_locations:
            #     logger.warning(f"No mapped locations found for client {client.id}. Skipping sync.")
            #     return {"status": "skipped", "reason": "No mapped locations"}

            # # Step 2: For each mapped location, sync the revenue
            # sync_logs = []
            # for location in mapped_locations:
            #     log = await self.sync_location_revenue(
            #         client=client,
            #         location=location,
            #         target_date=target_date,
            #         square_client=square_client,
            #         combo_client=combo_client
            #     )
            #     sync_logs.append(log)

            # return {"status": "completed", "logs": [log.id for log in sync_logs]}

        except Exception as e:
            logger.error(
                f"An error occurred during sync for client {client.id}: {e}",
                exc_info=True,
            )
            return {"status": "failed", "error": str(e)}

        finally:
            await square_client.close()
            await combo_client.close()

    async def sync_location_revenue(
        self,
        client: Client,
        location: Location,
        target_date: date,
        square_client: SquareClient,
        combo_client: ComboClient,
    ) -> SyncLog:
        """
        Sync revenue for a single location.

        Args:
            client: Client object
            location: Location object
            target_date: Date to sync revenue for
            square_client: Square API client
            combo_client: Combo API client

        Returns:
            SyncLog object with sync results
        """
        logger.info(f"Syncing revenue for location {location.id} on {target_date}")

        # TODO: Implement location-specific sync logic
        pass

    def create_sync_log(
        self,
        client_id: int,
        location_id: int,
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
            location_id: Location ID
            sync_date: Date of the synced data
            status: Sync status (success, failed, pending)
            revenue_amount: Revenue amount synced
            error_message: Error message if failed
            square_response: Square API response
            combo_response: Combo API response

        Returns:
            Created SyncLog object
        """
        # TODO: Implement sync log creation
        logger.info(f"Creating sync log for client {client_id}, location {location_id}")
        pass
