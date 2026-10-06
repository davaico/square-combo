"""Merchant identity and credential persistence; authorization lives in onboarding."""

from sqlalchemy.orm import Session

from database.models import Client
from utils.dates import utc_naive


class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_active_clients(self) -> list[Client]:
        return (
            self.db.query(Client)
            .filter(
                Client.is_active.is_(True),
                Client.square_access_token_revoked.is_(False),
                Client.combo_api_key.isnot(None),
                Client.combo_api_key != "",
            )
            .all()
        )

    def get_client_by_id(self, client_id: int) -> Client | None:
        return self.db.get(Client, client_id)

    def get_client_by_merchant_id(self, merchant_id: str) -> Client | None:
        return self.db.query(Client).filter_by(square_merchant_id=merchant_id).one_or_none()

    def save_square_authorization(self, token: dict, name: str) -> Client:
        client = self.get_client_by_merchant_id(token["merchant_id"])
        if client is None:
            client = Client(name=name, square_merchant_id=token["merchant_id"])
            self.db.add(client)
        client.name = name
        client.square_access_token = token["access_token"]
        client.square_refresh_token = token["refresh_token"]
        client.square_access_token_expiry_date = utc_naive(token["expires_at"])
        client.square_access_token_revoked = False
        # Reauthorization preserves the operator's is_active policy and Combo key.
        self.db.commit()
        self.db.refresh(client)
        return client

    def save_refreshed_token(self, client: Client, token: dict) -> None:
        client.square_access_token = token["access_token"]
        client.square_refresh_token = token.get("refresh_token", client.square_refresh_token)
        client.square_access_token_expiry_date = utc_naive(token["expires_at"])
        self.db.commit()
