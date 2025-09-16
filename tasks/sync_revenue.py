"""
Daily revenue synchronization task.
This module contains the main logic for syncing revenue data from Square to Combo.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from database.database import SessionLocal
from services.client_service import ClientService
from services.setup_service import SetupService
from services.sync_service import SyncService
from utils.config import settings
from utils.logging import setup_logging

logger = logging.getLogger("tasks.sync_revenue")

async def sync_daily_revenue():
    """
    Main function to sync daily revenue for all active clients.
    This function is called by the cron job.
    """
    db = SessionLocal()
    try:
        sync_service = SyncService(db)
        client_service = ClientService(db)
        setup_service = SetupService(db)

        # Calculate target date (previous day by default)
        target_date = datetime.now() - timedelta(days=settings.SYNC_DAYS_BACK)
        logger.info(f"----- Starting daily revenue sync process for date: {target_date.date()} -----")

        # Get list of current clients
        clients = client_service.get_all_active_clients()
        logger.info(f"Found {len(clients)} active clients")

        for client in clients:
            logger.info(f"\tSyncing daily revenue for client {client.square_merchant_id}")
            # Validate square access token expiry date for client
            if client.square_access_token_expiry_date < datetime.now():
                logger.info(f"\t\tRefreshing access token for client {client.square_merchant_id}")
                new_token = await setup_service.refresh_square_access_token(client.square_refresh_token)
                if not new_token:
                    logger.error(f"\t\tFailed to refresh access token for client {client.square_merchant_id}")
                    continue
                #Save new access token and refresh token to database
                update_token = {
                    "square_access_token": new_token.get("access_token"),
                    "square_refresh_token": new_token.get("refresh_token"),
                    "square_access_token_expiry_date": new_token.get("expires_at"),
                }
                client = client_service.update_client(client.id, update_token)

            results = await sync_service.sync_client_revenue(client, target_date)
            has_error = False
            for result in results:
                if result.get("status") == "failed":
                    has_error = True
                    break

            if has_error:
                logger.error(f"\t\tSync result: {results}")
            else:
                logger.info(f"\t\tSync result: {results}")

    except Exception as e:
        logger.error(f"Error during daily revenue sync: {e}")
        raise
    finally:
        db.close()
        logger.info("Daily revenue sync process completed")

if __name__ == "__main__":
    setup_logging()
    asyncio.run(sync_daily_revenue())
