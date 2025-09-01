import asyncio
import logging
import uuid
from datetime import date
from adapters.square.client import SquareClient
from adapters.combo.client import ComboClient
from utils.config import settings

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


async def create_square_order(square_client: SquareClient, location_id: str):
    """Creates a simple test order in Square."""
    logging.info(f"Creating a test order in Square at location {location_id}...")
    line_items = [
        {
            "name": "Test Item",
            "quantity": "1",
            "base_price_money": {"amount": 1000, "currency": "EUR"},  # 10.00 in cents
        }
    ]

    order_data = {
        "order": {
            "location_id": location_id,
            "line_items": line_items,
        },
        "idempotency_key": str(uuid.uuid4()),
    }

    try:
        response = await square_client.client.post("/v2/orders", json=order_data)
        response.raise_for_status()
        created_order = response.json().get("order")
        logging.info(f"Successfully created test order with ID: {created_order['id']}")
        return created_order
    except Exception as e:
        logging.error(f"Failed to create test order: {e}", exc_info=True)
        raise


async def main():
    """Runs a full end-to-end revenue sync for one location."""
    logging.info("Initializing API clients...")
    square_client = SquareClient(
        access_token=settings.SQUARE_ACCESS_TOKEN,
        application_id=settings.SQUARE_APPLICATION_ID,
        environment=settings.SQUARE_ENVIRONMENT,
    )
    combo_client = ComboClient(api_key=settings.COMBO_API_KEY)

    try:
        # --- Step 1: Fetch Locations ---
        logging.info("Fetching locations from Square...")
        square_locations = await square_client.get_locations()
        if not square_locations:
            logging.error("No locations found in Square. Aborting.")
            return

        target_square_location = square_locations[0]  # Use the first available location
        logging.info(
            f"Selected Square location: '{target_square_location['name']}' (ID: {target_square_location['id']})"
        )

        # --- Step 2: Create Multiple Test Orders in Square ---
        # This requires ORDERS_WRITE permission.
        logging.info("Creating 3 test orders...")
        await create_square_order(square_client, target_square_location["id"])
        await asyncio.sleep(1)  # Small delay to ensure orders are processed
        await create_square_order(square_client, target_square_location["id"])
        await asyncio.sleep(1)
        await create_square_order(square_client, target_square_location["id"])

        # --- Step 3: Fetch Today's Revenue from Square ---
        target_date = date.today()
        logging.info(f"Fetching revenue from Square for {target_date}...")

        revenue_data = await square_client.get_daily_revenue(
            target_square_location["id"], target_date
        )

        if not revenue_data or revenue_data.get("net_sales_amount", 0) == 0:
            logging.error(
                f"No revenue data found for '{target_square_location['name']}' on {target_date} after creating an order. Aborting."
            )
            return

        net_sales = revenue_data["net_sales_amount"] / 100.0
        logging.info(f"Found revenue: {net_sales} {revenue_data.get('currency')}")

        # --- Step 4: List Combo Locations ---
        logging.info("Fetching locations from Combo...")
        combo_locations = await combo_client.get_locations()

        if combo_locations:
            logging.info(
                f"Successfully fetched {len(combo_locations)} locations from Combo:"
            )
            for loc in combo_locations:
                logging.info(f"  - ID: {loc.get('id')}, Name: {loc.get('name')}")
        else:
            logging.info(
                "API call successful, but no locations were found for this account."
            )

        # --- Step 5 - we need to name locations exactly the same in Combo Dashboard --> No API for creating or naming locations ---
        # combo_location_map = {loc["name"]: loc["id"] for loc in combo_locations}

        # target_combo_location_id = combo_location_map.get(target_square_location["name"])

        # if not target_combo_location_id:
        #     logging.error(f"Could not find a matching Combo location for '{target_square_location['name']}'. Aborting.")
        #     return

        # logging.info(f"Found matching Combo location. Posting revenue...")

        # post_response = await combo_client.post_revenue(
        #     location_id=target_combo_location_id,
        #     date=target_date.strftime("%Y-%m-%d"),
        #     amount=net_sales,
        # )

        # logging.info(f"Successfully posted revenue to Combo! API Response: {post_response}")

        # --- Step 6: Post Revenue to the first Combo Location ---
        if combo_locations:
            target_combo_location_id = combo_locations[0]["id"]
            logging.info(
                f"Posting revenue to the first Combo location: {target_combo_location_id}"
            )

            post_response = await combo_client.post_revenue(
                location_id=target_combo_location_id,
                date=target_date.strftime("%Y-%m-%d"),
                amount=net_sales,
            )

            logging.info(
                f"Successfully posted revenue to Combo! API Response: {post_response}"
            )

    except Exception as e:
        logging.error(f"An error occurred during the sync process: {e}", exc_info=True)
    finally:
        await square_client.close()
        await combo_client.close()
        logging.info("Clients closed.")


if __name__ == "__main__":
    asyncio.run(main())
