from concurrent.futures import ThreadPoolExecutor

from services.orchestration_pipeline import make_pipeline
from services.connectors_metadata_service import ConnectorMetadataService


def run_pipeline(connector_name: str) -> None:
    """Create and invoke the pipeline for a single connector."""
    pipeline = make_pipeline(connector_name)
    pipeline.invoke(None)

if __name__ == "__main__":
    service = ConnectorMetadataService()
    connectors = service.get_all_connectors()
    connector_names = [c.get("name") for c in connectors if c.get("name")]

    # Run pipelines in parallel for all connectors
    with ThreadPoolExecutor() as executor:
        executor.map(run_pipeline, connector_names)
