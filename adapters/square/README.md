# Square Adapter

This adapter provides a client for interacting with the Square API. It is used to fetch data, such as locations and daily revenue, from a Square merchant account.

## Configuration

The `SquareClient` requires the following environment variables to be set in the `.env` file:

-   `SQUARE_ACCESS_TOKEN`: Your personal access token for the Square API.
-   `SQUARE_APPLICATION_ID`: The ID of your application in the Square Developer Dashboard.
-   `SQUARE_ENVIRONMENT`: The environment to use, either `sandbox` or `production`.

## Implemented Methods

### `get_locations()`

Fetches a list of all available locations for the merchant.

-   **Returns**: A list of location dictionaries.

### `search_orders_by_date(location_ids: List[str], target_date: date)`

Searches for all orders for a given list of location IDs on a specific date.

-   **Returns**: A list of order dictionaries.

### `get_daily_revenue(location_id: str, target_date: date)`

Calculates the total daily revenue for a single location by fetching and processing sales and refunds.

-   **Returns**: A dictionary containing a breakdown of the daily revenue.

## API Documentation

For more detailed information about the Square API, please refer to the [official Square API documentation](https://developer.squareup.com/reference/square).
