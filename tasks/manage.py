"""Local operator commands; never expose administrative writes over HTTP."""

import argparse

from database.database import SessionLocal
from database.models import Client, LocationMapping


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "clients", help="List client IDs, merchant names and activation status; no secrets"
    )
    mapping = sub.add_parser("map", help="Create/update an explicit unique location mapping")
    mapping.add_argument("--client-id", type=int, required=True)
    mapping.add_argument("--square", required=True)
    mapping.add_argument("--combo", required=True)
    active = sub.add_parser("active", help="Activate or deactivate an existing client")
    active.add_argument("--client-id", type=int, required=True)
    active.add_argument("--value", choices=("true", "false"), required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.command == "clients":
            for client in db.query(Client).order_by(Client.id):
                print(client.id, client.name, "active" if client.is_active else "inactive")
            return
        client = db.get(Client, args.client_id)
        if client is None:
            parser.error("Client does not exist")
        if args.command == "active":
            client.is_active = args.value == "true"
        else:
            existing = (
                db.query(LocationMapping)
                .filter_by(client_id=client.id, square_location_id=args.square)
                .one_or_none()
            )
            collision = (
                db.query(LocationMapping)
                .filter_by(client_id=client.id, combo_location_id=args.combo)
                .one_or_none()
            )
            if collision and collision != existing:
                parser.error("Combo location is already mapped to another Square location")
            if existing:
                existing.combo_location_id = args.combo
            else:
                db.add(
                    LocationMapping(
                        client_id=client.id,
                        square_location_id=args.square,
                        combo_location_id=args.combo,
                    )
                )
        db.commit()


if __name__ == "__main__":
    main()
