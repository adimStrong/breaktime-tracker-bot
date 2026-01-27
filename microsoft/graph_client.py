"""
Microsoft Graph API Client
Handles HTTP requests to Microsoft Graph API for Excel operations.
"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any, List
from .auth import get_access_token, refresh_access_token

# Microsoft Graph API base URL
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


class GraphClient:
    """Async client for Microsoft Graph API."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self, token: str) -> Dict[str, str]:
        """Get headers with authorization token."""
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to Graph API with retry logic.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint (appended to base URL)
            data: JSON data for request body
            retry_count: Current retry attempt

        Returns:
            Response JSON or error dict
        """
        token = get_access_token()
        if not token:
            return {'error': 'No valid access token'}

        url = f"{GRAPH_BASE_URL}{endpoint}"
        session = await self._get_session()

        try:
            async with session.request(
                method,
                url,
                headers=self._get_headers(token),
                json=data if data else None
            ) as response:

                # Handle 401 Unauthorized - try refreshing token
                if response.status == 401 and retry_count == 0:
                    print("[Graph] Token expired, refreshing...")
                    new_token = refresh_access_token()
                    if new_token:
                        return await self._request(method, endpoint, data, retry_count + 1)
                    return {'error': 'Token refresh failed'}

                # Handle 429 Rate Limited - exponential backoff
                if response.status == 429:
                    if retry_count < MAX_RETRIES:
                        delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
                        print(f"[Graph] Rate limited, waiting {delay}s...")
                        await asyncio.sleep(delay)
                        return await self._request(method, endpoint, data, retry_count + 1)
                    return {'error': 'Rate limit exceeded after retries'}

                # Handle 5xx Server Errors - retry
                if response.status >= 500:
                    if retry_count < MAX_RETRIES:
                        delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
                        print(f"[Graph] Server error {response.status}, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        return await self._request(method, endpoint, data, retry_count + 1)
                    return {'error': f'Server error {response.status} after retries'}

                # Handle 204 No Content
                if response.status == 204:
                    return {'success': True}

                # Handle successful responses
                if response.status in [200, 201]:
                    return await response.json()

                # Handle other errors
                try:
                    error_data = await response.json()
                    error_msg = error_data.get('error', {}).get('message', str(error_data))
                except:
                    error_msg = await response.text()

                return {'error': f'HTTP {response.status}: {error_msg}'}

        except aiohttp.ClientError as e:
            print(f"[Graph] Request error: {e}")
            if retry_count < MAX_RETRIES:
                delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
                await asyncio.sleep(delay)
                return await self._request(method, endpoint, data, retry_count + 1)
            return {'error': str(e)}

    async def get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request."""
        return await self._request('GET', endpoint)

    async def post(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make POST request."""
        return await self._request('POST', endpoint, data)

    async def patch(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make PATCH request."""
        return await self._request('PATCH', endpoint, data)

    # Excel-specific methods

    async def add_table_row(
        self,
        file_id: str,
        table_name: str,
        values: List[List[Any]]
    ) -> Dict[str, Any]:
        """
        Add a row to an Excel table.

        Args:
            file_id: OneDrive file ID
            table_name: Name of the Excel table
            values: 2D array of values [[col1, col2, ...]]

        Returns:
            Response from Graph API
        """
        endpoint = f"/me/drive/items/{file_id}/workbook/tables/{table_name}/rows/add"
        data = {"values": values}
        return await self._request('POST', endpoint, data)

    async def get_table_info(self, file_id: str, table_name: str) -> Dict[str, Any]:
        """Get information about an Excel table."""
        endpoint = f"/me/drive/items/{file_id}/workbook/tables/{table_name}"
        return await self._request('GET', endpoint)

    async def list_tables(self, file_id: str) -> Dict[str, Any]:
        """List all tables in an Excel workbook."""
        endpoint = f"/me/drive/items/{file_id}/workbook/tables"
        return await self._request('GET', endpoint)

    async def create_table(
        self,
        file_id: str,
        address: str,
        has_headers: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new table in an Excel workbook.

        Args:
            file_id: OneDrive file ID
            address: Cell range for the table (e.g., "A1:H1")
            has_headers: Whether the first row contains headers
        """
        endpoint = f"/me/drive/items/{file_id}/workbook/tables/add"
        data = {
            "address": address,
            "hasHeaders": has_headers
        }
        return await self._request('POST', endpoint, data)


# Global client instance
_client: Optional[GraphClient] = None


def get_client() -> GraphClient:
    """Get or create the global Graph client."""
    global _client
    if _client is None:
        _client = GraphClient()
    return _client


async def close_client():
    """Close the global Graph client."""
    global _client
    if _client:
        await _client.close()
        _client = None
