import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

from tools.utils import get_serp_date_range, get_tavily_date_range

start_date_serpapi, end_date_serpapi = get_serp_date_range(int(os.getenv("DAYS_DELTA")))
start_date_tavily, end_date_tavily = get_tavily_date_range(int(os.getenv("DAYS_DELTA")))


def search_with_serpapi(query):
    print(f"Searching SerpAPI for: {query}")
    url = os.getenv("SERP_API_URL")
    params = {
        "q": query,
        "api_key": os.getenv("SERP_API_KEY"),
        "engine": "google",
        "tbs": f"cdr:1,cd_min:{start_date_serpapi},cd_max:{end_date_serpapi}",
        "device": "desktop",
        "num": 2,
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    results = response.json()
    print(results["search_metadata"]["google_url"])
    return results


def search_with_tavily(query):
    print(f"Searching Tavily for: {query}")
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
        "Content-Type": "application/json",
    }
    data = {
        "query": query,
        "search_depth": "advanced",
        "max_results": 20,
        "time_range": "month",
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    results = response.json().get("results", [])

    filtered = []
    for result in results:
        published = result.get("published_date")
        if published:
            pub_date = datetime.strptime(published[:10], "%Y-%m-%d")
            if (
                datetime.strptime(start_date_tavily, "%Y-%m-%d")
                <= pub_date
                <= datetime.strptime(end_date_tavily, "%Y-%m-%d")
            ):
                filtered.append(result)
    return filtered


def perform_search(query, provider="serpapi"):
    if provider == "serpapi":
        return search_with_serpapi(query)
    elif provider == "tavily":
        return search_with_tavily(query)
    else:
        raise ValueError("Unknown search provider!")
