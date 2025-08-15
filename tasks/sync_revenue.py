"""
Daily revenue synchronization task.
This module contains the main logic for syncing revenue data from Square to Combo.
"""
import asyncio
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from database.database import SessionLocal
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
        
        # Calculate target date (previous day by default)
        target_date = date.today() - timedelta(days=settings.SYNC_DAYS_BACK)
        
        # Get all active clients
        # TODO: Implement client retrieval and sync logic
        logger.info(f"Syncing revenue data for date: {target_date}")
        
        # For each client:
        # 1. Fetch locations from Square
        # 2. For each location, fetch revenue data
        # 3. Map to Combo format and post to Combo API
        # 4. Log results
        
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
