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

logger = logging.getLogger(__name__)

async def sync_daily_revenue():
    """
    Main function to sync daily revenue for all active clients.
    This function is called by the cron job.
    """
    logger.info("Starting daily revenue sync process")

    db = SessionLocal()
    try:
        sync_service = SyncService(db)
        client_service = ClientService(db)
        setup_service = SetupService(db)

        # Calculate target date (previous day by default)
        target_date = date.today() - timedelta(days=settings.SYNC_DAYS_BACK)
        logger.info(f"Syncing daily revenue for {target_date}")

        # Get list of current clients
        clients = client_service.get_all_active_clients()
        logger.info(f"Found {len(clients)} active clients")

        for client in clients:
            # Validate square access token expiry date for client
            if client.square_access_token_expiry_date < datetime.now():
                logger.info(f"Refreshing access token for client {client.square_merchant_id}")
                new_token = await setup_service.refresh_square_access_token(client.square_refresh_token)
                if not new_token:
                    logger.error(f"Failed to refresh access token for client {client.square_merchant_id}")
                    continue
                #Save new access token and refresh token to database
                update_token = {
                    "square_access_token": new_token.get("access_token"),
                    "square_refresh_token": new_token.get("refresh_token"),
                    "square_access_token_expiry_date": new_token.get("expires_at"),
                }
                client = client_service.update_client(client.id, update_token)

            logger.info(f"Syncing daily revenue for client {client.square_merchant_id}")
            result = await sync_service.sync_client_revenue(client, target_date)
            logger.info(f"Sync result: {result}")

    except Exception as e:
        logger.error(f"Error during daily revenue sync: {e}")
        raise
    finally:
        db.close()
        logger.info("Daily revenue sync process completed")


def setup_cron_job():
    """
    Set up the cron job for daily revenue sync.
    This function should be called during application startup.
    """
    # TODO: Implement cron job setup using python-crontab
    logger.info("Setting up cron job for daily revenue sync")
    pass


if __name__ == "__main__":
    # Allow running the sync manually for testing
    asyncio.run(sync_daily_revenue())
