# Combo Adapter

This adapter provides a client for interacting with the Combo Partner API. It is used to synchronize data, such as daily revenue, from a source system into Combo.

## Configuration

The `ComboClient` requires the following environment variables to be set in the `.env` file:

-   `COMBO_API_KEY`: Your API token for the Combo Partner API.
-   `COMBO_BASE_URL`: The base URL for the API. Defaults to `https://partner.combohr.com`.

## Implemented Methods

### `get_locations()`

Fetches a list of all available locations from the Combo API.

-   **Returns**: A list of location dictionaries.

### `post_revenue(location_id: str, date: str, amount: float)`

Posts the actual revenue for a specific location and date.

-   **`location_id`**: The partner ID of the Combo location.
-   **`date`**: The date of the revenue in `YYYY-MM-DD` format.
-   **`amount`**: The revenue amount as a float.
-   **Returns**: The API response as a dictionary.

## API Documentation

For more detailed information about the Combo Partner API, please refer to the official documentation located at `docs/combo.pdf`.

## Usage Example

```python
import asyncio
from adapters.combo.client import ComboClient
from utils.config import settings

async def main():
    # Initialize the client with the API key from settings
    combo_client = ComboClient(api_key=settings.COMBO_API_KEY)

    try:
        # Get all locations
        locations = await combo_client.get_locations()
        if not locations:
            print("No locations found.")
            return

        # Post revenue to the first location
        first_location_id = locations[0]["id"]
        revenue_date = "2025-09-01"
        revenue_amount = 1234.56

        response = await combo_client.post_revenue(
            location_id=first_location_id,
            date=revenue_date,
            amount=revenue_amount
        )
        print("Successfully posted revenue:", response)

    finally:
        # Close the client connection
        await combo_client.close()

if __name__ == "__main__":
    asyncio.run(main())
