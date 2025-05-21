import os
from typing import List, Dict, Any

import requests


class ConnectorMetadataService:
    """Client for Celigo Integrator API connector metadata."""

    def __init__(self) -> None:
        self.base_url = os.getenv("INTEGRATOR_API_BASE_URL", "https://api.integrator.io/v1")
        self.api_key = os.getenv("INTEGRATOR_API_KEY")
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": self.api_key})

    def get_all_connectors(self) -> List[Dict[str, Any]]:
        """Return metadata for all available connectors."""
        url = f"{self.base_url}/httpconnectors"
        resp = self.session.get(url)
        resp.raise_for_status()
        data = resp.json()
        # Integrator API returns items under 'items' when paginated
        return data.get("items", data)

    def get_connector_by_id(self, connector_id: str) -> Dict[str, Any]:
        """Return metadata for a connector by id."""
        url = f"{self.base_url}/httpconnectors/{connector_id}"
        resp = self.session.get(url, params={"returnEverything": "true"})
        resp.raise_for_status()
        return resp.json()
