import os

from langchain.schema.runnable import RunnableLambda, RunnableSequence

from tools.analyzer import search_release_notes


def make_pipeline(connector_name: str):

    steps = [
        RunnableLambda(lambda _: search_release_notes(connector_name)),
        RunnableLambda(
            lambda data: print("Sending notification")
            or f"Notification sent for {connector_name}"
        ),
    ]

    return RunnableSequence(*steps)
