# Services

This directory contains the core business logic of the application. Services are responsible for orchestrating the flow of data between the adapters and the database.

## `SyncService`

The `SyncService` is the brain of the revenue synchronization process. It contains all the core business logic and acts as the orchestrator between the external APIs (via the `adapters`) and the internal database.

### Architecture and Design

The service is designed with two layers of abstraction:

1.  **Client-Level Sync (`sync_client_revenue`)**: This is the main, high-level method called by the daily sync task. It's responsible for managing the sync process for an entire client, which may have multiple locations.
2.  **Location-Level Sync (`sync_location_revenue`)**: This is a more granular method designed to handle the sync for a single, specific location. This separation of concerns makes the code cleaner and easier to test and maintain.

### Methods

#### `sync_client_revenue(client, target_date)`

This is the main, high-level method that is called by the daily sync task. It is responsible for syncing all revenue for a single client.

### Core Logic (`sync_client_revenue`)

The main method, `sync_client_revenue`, performs the following steps:

1.  Initializes the `SquareClient` and `ComboClient` with the appropriate API credentials for a given client.
2.  Fetches all available locations from both the Square and Combo APIs.
3.  **Matches locations based on their names.** It assumes that a location in Square (e.g., "Main Street Cafe") will have a corresponding location in Combo with the exact same name.
4.  For each pair of matched locations, it:
    *   Calls the `SquareClient` to get the total daily revenue for the Square location.
    *   If revenue exists, it calls the `ComboClient` to post that total revenue to the corresponding Combo location.
5.  Logs the results of the sync operation.

#### `sync_location_revenue(client, location, ...)`

This is a more granular, lower-level method designed to sync revenue for a single, specific location. The `sync_client_revenue` method will eventually call this method for each mapped location. (Currently a placeholder).

#### `create_sync_log(...)`

This is a utility method for writing the results of a sync operation (whether successful or failed) to the `sync_logs` table in the database. (Currently a placeholder).

---

## TODO List & Future Improvements

-   **Implement Database-Driven Location Mapping**: The current logic of matching locations by name is simple but brittle. The `sync_client_revenue` method should be updated to use the `Location` table in the database. This will allow for a more robust and flexible mapping of locations between the two systems.
-   **Implement Database Logging**: The `sync_location_revenue` and `create_sync_log` methods are currently placeholders. They should be implemented to record the results of each sync operation in the `sync_logs` table in the database.
-   **Implement Client Management**: The `tasks/sync_revenue.py` script currently uses a temporary `Client` object. This should be updated to fetch all active clients from the `clients` table in the database.
-   **Implement Cron Job Setup**: The `setup_cron_job` function in `tasks/sync_revenue.py` is currently a placeholder. It should be implemented to automatically schedule the daily sync task.

### Potential Future Improvements

-   **Configuration Management**: Move hardcoded settings (like API versions) to the `.env` file to make the application more configurable.
-   **Rate Limiting and Retries**: Implement logic in the API clients to handle API rate limits and to automatically retry failed requests with exponential backoff.
-   **Rate Limiting and Retries**: Implement logic in the API clients to handle API rate limits and to automatically retry failed requests with exponential backoff.
