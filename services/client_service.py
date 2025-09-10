"""
Client service for managing client data and operations.
"""
import logging
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy.orm import Session

from database.models import Client, Location

logger = logging.getLogger(__name__)


class ClientService:
    """Service class for client-related operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_active_clients(self) -> List[Client]:
        """
        Retrieve all active clients.

        Returns:
            List of active Client objects
        """
        # TODO: Implement client retrieval
        logger.info("Fetching all active clients")
        pass

    def get_client_by_id(self, client_id: int) -> Optional[Client]:
        """
        Retrieve a client by ID.
        Args:
            client_id: Client ID
        Returns:
            Client object or None if not found
        """
        logger.info(f"Fetching client with ID: {client_id}")
        client = self.db.query(Client).filter(Client.id == client_id).first()
        return client

    def create_client(self, client_data: dict[str, Any]) -> Client:
        """
        Create a new client.
        Args:
            client_data: Dictionary containing client information
        Returns:
            Created Client object
        """
        logger.info("Creating new client")
        new_client: Client = Client(
            name=client_data["name"],
            square_access_token=client_data.get("square_access_token"),
            square_merchant_id=client_data.get("square_merchant_id"),
            square_refresh_token=client_data.get("square_refresh_token"),
            square_access_token_expiry_date=datetime.fromisoformat(client_data.get("square_access_token_expiry_date").replace("Z", "+00:00")),
            combo_api_key=client_data.get("combo_api_key")
        )
        self.db.add(new_client)
        self.db.commit()
        self.db.refresh(new_client)
        return new_client

    def update_client(self, client_id: int, updated_data: dict):
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return None

        for key, value in updated_data.items():
            if hasattr(client, key) and value is not None:
                setattr(client, key, value)

        self.db.commit()
        self.db.refresh(client)
        return client

    def get_client_locations(self, client_id: int) -> List[Location]:
        """
        Retrieve all locations for a client.

        Args:
            client_id: Client ID

        Returns:
            List of Location objects
        """
        # TODO: Implement location retrieval for client
        logger.info(f"Fetching locations for client {client_id}")
        pass

    def get_client_by_merchant_id(self, merchant_id: str) -> Optional[Client]:
        logger.info(f"Fetching client with merchant ID: {merchant_id}")
        client = self.db.query(Client).filter(Client.square_merchant_id == merchant_id).first()
        return client

