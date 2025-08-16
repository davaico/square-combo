"""
Admin routes for client and sync management.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from services.client_service import ClientService
from services.sync_service import SyncService

router = APIRouter()


@router.get("/clients")
async def list_clients(db: Session = Depends(get_db)):
    """
    List all registered clients.

    Args:
        db: Database session
    """
    # TODO: Implement client listing
    pass


@router.get("/clients/{client_id}/sync-status")
async def get_sync_status(client_id: int, db: Session = Depends(get_db)):
    """
    Get sync status for a specific client.

    Args:
        client_id: Client ID
        db: Database session
    """
    # TODO: Implement sync status retrieval
    pass


@router.post("/clients/{client_id}/sync")
async def trigger_manual_sync(client_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger revenue sync for a client.

    Args:
        client_id: Client ID
        db: Database session
    """
    # TODO: Implement manual sync trigger
    pass
