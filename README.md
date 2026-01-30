# Kobo PowerBI Proxy (Python/Flask)

This application proxies requests from PowerBI (or any HTTP client) to KoboToolbox, allowing you to secure your main API key while granting granular access to specific exports via revocable tokens.

## Architecture

- **Backend**: Python Flask
- **Database**: SQLite (Persisted in Docker volume)
- **Encryption**: User Kobo Keys are encrypted using Fernet (symmetric encryption).
- **Hosting**: Docker / Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose installed.

### Installation

1.  Clone the repository.
2.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
3.  Generate a secure Encryption Key and Secret Key, and update `.env`:
    ```bash
    python3 -c "from cryptography.fernet import Fernet; print(f'ENCRYPTION_KEY={Fernet.generate_key().decode()}'); print('SECRET_KEY=change-me-to-random-string')"
    ```
    *Update `ENCRYPTION_KEY` and `SECRET_KEY` in your new `.env` file.*
4.  Build and run:
    ```bash
    docker-compose up --build -d
    ```

### Running the App

```bash
docker-compose up --build -d
```

The application will be available at `http://localhost:8003`.

### Usage

1.  **Register**: Create an account via the web UI. You will need your **KoboToolbox API Key** (found in Kobo Account Settings -> Account -> API Token).
2.  **Create Proxy**:
    *   Enter a Friendly Name (e.g., "Main Survey PBI").
    *   Enter the **Asset UID** (Form ID) from Kobo.
    *   Enter the **Export Setting UID** (created in Kobo's "Downloads" section -> "New Export" -> Save Settings, then copy the UID from the URL or API).
3.  **Connect PowerBI**:
    *   On the Dashboard, click **Copy Link**.
    *   In PowerBI, select **Get Data -> Web**.
    *   Paste the URL.
    *   The link format is: `http://<your-server>:8003/exports/<asset>/<setting>/xlsx?token=<proxy_token>`
    *   This link embeds the authentication token, so no headers are required in PowerBI.

## Development

The source code is located in the `src/` directory:
- `src/routes.py`: Main application logic and routing.
- `src/models.py`: Database schema (User, ProxyConfig).
- `src/templates/`: HTML templates using the style guide.
- `src/crypto_utils.py`: Encryption helpers.

## Security Note

The Kobo API Key is stored encrypted in the database. When a request is made to the proxy endpoint, the key is decrypted in memory solely to authenticate the request to KoboToolbox, and then discarded.
