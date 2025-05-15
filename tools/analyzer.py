import json
import os
import time
from datetime import datetime, timedelta

from openai import OpenAI

from tools.scraper_tool import (
    click_element_in_browser,
    extract_links_from_browser,
    extract_text_from_browser,
    get_current_url,
    get_elements,
    go_back,
    navigate_and_extract_text,
    navigate_to_url,
)
from tools.search_tool import perform_search
from tools.utils import get_serp_date_range

client = OpenAI()
gptverse_assistant_id = os.getenv("ASSISTANT_ID")
from typing import List

from pydantic import BaseModel


class ChangelogEntry(BaseModel):
    summary: str
    type: str  # breaking | non-breaking | security
    severity: str  # low | medium | high | critical
    source_url: str
    published_date: str  # ISO date string


class ChangelogOutput(BaseModel):
    changes: List[ChangelogEntry]


# Step 1: Get the current assistant details (including current tools)
assistants = client.beta.assistants.list()
assistant = None
for a in assistants.data:
    if a.id == gptverse_assistant_id:
        assistant = a
        break
if not assistant:
    raise Exception("Assistant not found")

# Step 2: Extract the existing tools list
# Remove any tool with function name "extract_changelog"
filtered_tools = [
    tool
    for tool in getattr(assistant, "tools", []) or []
    if not (tool.type == "function" and tool.function.name == "extract_changelog")
]

# Step 3: Define your new tool
new_tool = {
    "type": "function",
    "function": {
        "name": "extract_changelog",
        "description": "Extract changelog entries in structured JSON",
        "parameters": ChangelogOutput.model_json_schema(),
    },
}

# Step 4: Append the new tool
updated_tools = filtered_tools + [new_tool]

# Step 5: Update the assistant with the combined list
client.beta.assistants.update(
    assistant_id=gptverse_assistant_id,
    tools=updated_tools,
)


def search_release_notes(connector_name: str):

    start_date_serpapi, end_date_serpapi = get_serp_date_range(
        int(os.getenv("DAYS_DELTA"))
    )
    print(
        f"Searching for {connector_name} updates between {start_date_serpapi} and {end_date_serpapi}"
    )

    thread = client.beta.threads.create()
    print(f"🧵 Created thread: {thread.id}")

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=(
            f"You are an assistant analyzing API changelogs. You must perform the following exact Google search query **without rephrasing**: {connector_name} updates changelog. \n\n. "
            f"Then visit all relevant links found in search and analyze each page. "
            f"From the content on the page, please identify: - \n\n The date when each changelog entry or update was posted (e.g., published date or last updated date visible on the page content). \n - The source URL of the page (this will be provided)\n. "
            f"Only consider updates or changes **posted between {start_date_serpapi} and {end_date_serpapi}**. Ignore any entries outside this date range.\n\n"
            f"If you cannot find a clear date for an entry, mark the date as 'unknown'."
            f"For each change, include:\n"
            f"- A summary\n"
            f"- Type: breaking | non-breaking | security\n"
            f"- Severity: low | medium | high | critical\n"
            f"- The source URL for the entry, as specified or linked in the page content (e.g., permalinks, anchor tags, or canonical URLs inside the entry). If a source URL for the entry is not explicitly mentioned, use the URL of the current page\n"
            f"- The published date (2025-05-10) for the entry (based on dates mentioned near the entry or in the content)\n"
            f"After extracting changes, call the `extract_changelog` function tool.\n"
            f"Ensure your output is not free text — use the tool to return structured data.\n"
            f"Only respond with the tool call.\n"
        ),
    )

    search_links_queue = []
    visited_links = set()
    full_chunks = []
    all_changes = []

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=gptverse_assistant_id
    )

    # Main loop
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        if run.status == "completed":
            print("✅ Run completed.")
            print("All changes:")
            print(all_changes)
            break

        elif run.status == "requires_action":
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            outputs = []

            for call in tool_calls:
                fn = call.function.name
                args = json.loads(call.function.arguments)
                tool_id = call.id

                print(f"\n🔧 Tool: {fn} | Args: {args}")

                if fn == "navigate_browser":
                    url = args["url"]
                    navigate_to_url(url)
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"status": "navigated"}),
                        }
                    )

                elif fn == "extract_text":
                    current_url = get_current_url()
                    if current_url in visited_links:
                        print(
                            f"⛔ Already extracted from URL: {current_url}, skipping."
                        )
                        outputs.append(
                            {
                                "tool_call_id": tool_id,
                                "output": json.dumps(
                                    {"text": "", "note": "Already extracted this URL"}
                                ),  # Return blank or dummy response
                            }
                        )
                        continue  # Skip re-processing
                    visited_links.add(current_url)
                    result = extract_text_from_browser()
                    chunk = result["text_chunks"].pop(0)
                    full_chunks.append(chunk)

                    if result["chunked"] and result["text_chunks"]:
                        print("📚 Assistant may request more chunks.")
                        for remaining in result["text_chunks"]:
                            full_chunks.append(remaining)

                    outputs.append(
                        {"tool_call_id": tool_id, "output": json.dumps({"text": chunk})}
                    )

                elif fn == "navigate_and_extract_text":
                    url = args["url"]
                    if url in visited_links:
                        print(f"⛔ Already visited: {url}, skipping.")
                        outputs.append(
                            {
                                "tool_call_id": tool_id,
                                "output": json.dumps({"text": ""}),
                            }
                        )
                        continue
                    visited_links.add(url)

                    result = navigate_and_extract_text(url)
                    chunk = result["text_chunks"].pop(0)
                    full_chunks.append(chunk)

                    for remaining in result["text_chunks"]:
                        full_chunks.append(remaining)

                    outputs.append(
                        {"tool_call_id": tool_id, "output": json.dumps({"text": chunk})}
                    )

                elif fn == "extract_hyperlinks":
                    links = extract_links_from_browser()
                    print(f"🔗 Found {len(links)} links")
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"links": links}),
                        }
                    )

                elif fn == "click_element":
                    result = click_element_in_browser(args["selector"])
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"clicked": result}),
                        }
                    )

                elif fn == "get_elements":
                    elements = get_elements(
                        args["selector"], args.get("attributes", [])
                    )
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"elements": elements}),
                        }
                    )

                elif fn == "current_webpage":
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"url": get_current_url()}),
                        }
                    )

                elif fn == "previous_webpage":
                    go_back()
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps({"status": "done"}),
                        }
                    )

                elif fn == "google_search_results_json":
                    # You can plug in SerpAPI or any provider here
                    query = args["__arg1"]
                    print(f"🔍 Performing search: {query}")
                    # Choose search provider here
                    search_results = perform_search(
                        query, provider="serpapi"
                    )  # or "tavily"

                    organic_links = []
                    link_to_date = {}

                    for result in search_results["organic_results"]:
                        link = result.get("link")
                        date = result.get("date") or result.get("snippet_date")
                        if link:
                            organic_links.append(link)
                            if date:
                                link_to_date[link] = date

                    search_results = {"results": organic_links}

                    for link in organic_links:
                        if link not in visited_links and link not in search_links_queue:
                            search_links_queue.append(link)
                    print(f"🔍 Search results: {search_results}")
                    outputs.append(
                        {"tool_call_id": tool_id, "output": json.dumps(search_results)}
                    )

                elif fn == "extract_changelog":
                    print("🔍 Extracting changelog")
                    # This is a no-op function used to validate structured output
                    # We simply echo back the received data as tool output
                    all_changes.extend(args["changes"])
                    outputs.append(
                        {
                            "tool_call_id": tool_id,
                            "output": json.dumps(
                                {"status": "received", "changes": args["changes"]}
                            ),
                        }
                    )

            # Submit tool outputs back to the assistant
            client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=outputs,
            )

        else:
            print(f"⏳ Waiting... current status: {run.status}")
            time.sleep(2)
