from services.orchestration_pipeline import make_pipeline

if __name__ == "__main__":
    connector_name = "Shopify"
    pipeline = make_pipeline(connector_name)
    pipeline.invoke(None)
