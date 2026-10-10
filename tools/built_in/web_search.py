from ddgs import DDGS
from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolResult


class WebSearchParams(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(
        10, ge=1, le=20, description="Maximum number of search results to return"
    )


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web for information. Returns search results with titles, URLs and snippets."
    kind = ToolKind.NETWORK

    schema = WebSearchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = WebSearchParams(**invocation.params)

        try:
            results = DDGS().text(
                query=params.query,
                max_results=params.max_results,
                safesearch="off",
                timelimit="y",
                page=1,
                background="auto",
            )
        except Exception as e:
            return ToolResult.error_result(f"Search failed: {e}")

        if not results:
            return ToolResult.success_result(
                f"No results found for: {params.query}",
                metadata={"query": params.query, "results_returned": 0},
            )

        output_lines = [f"Search results for: {params.query}"]
        for i, result in enumerate(results, start=1):
            output_lines.append(f"{i}. {result['title']}")
            output_lines.append(f"   URL: {result['href']}")
            if result.get("body"):
                output_lines.append(f"   Snippet: {result['body']}")

            output_lines.append("")

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={"query": params.query, "results_returned": len(results)},
        )
