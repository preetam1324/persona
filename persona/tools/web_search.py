"""Web search tool — uses httpx to query a search API."""

from __future__ import annotations

import os
from typing import Any

import httpx

from persona.core.tool import Tool, ToolResult


class WebSearchTool(Tool):
    """Search the web for current information."""

    name = "web_search"
    description = "Search the web for current information. Use when you need up-to-date facts."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        num_results = kwargs.get("num_results", 5)

        # Try Tavily API first, fall back to SerpAPI, then DuckDuckGo
        tavily_key = os.environ.get("TAVILY_API_KEY")
        if tavily_key:
            return await self._search_tavily(query, num_results, tavily_key)

        serp_key = os.environ.get("SERPAPI_API_KEY")
        if serp_key:
            return await self._search_serpapi(query, num_results, serp_key)

        # Fallback: DuckDuckGo instant answer (no key required)
        return await self._search_duckduckgo(query)

    async def _search_tavily(self, query: str, num: int, api_key: str) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": num,
                    "include_answer": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        if data.get("answer"):
            results.append(f"Answer: {data['answer']}")
        for r in data.get("results", [])[:num]:
            results.append(f"- [{r['title']}]({r['url']}): {r.get('content', '')[:200]}")

        return ToolResult(output="\n".join(results))

    async def _search_serpapi(self, query: str, num: int, api_key: str) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "num": num, "api_key": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for r in data.get("organic_results", [])[:num]:
            results.append(f"- [{r['title']}]({r['link']}): {r.get('snippet', '')}")

        return ToolResult(output="\n".join(results) if results else "No results found.")

    async def _search_duckduckgo(self, query: str) -> ToolResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_redirect": "1"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(f"- {topic['Text']}")

        return ToolResult(
            output="\n".join(results) if results else "No results found. Try a more specific query."
        )
