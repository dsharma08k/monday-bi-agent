"""
Monday.com API Client
Makes live REST API calls to Monday.com using GraphQL.
Every function makes a fresh HTTP request — no caching, no preloading.
"""

import logging
import requests
from config import MONDAY_API_TOKEN, MONDAY_API_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "Authorization": MONDAY_API_TOKEN,
    "Content-Type": "application/json",
    "API-Version": "2024-10",
}


def _make_request(query: str, variables: dict = None) -> dict:
    """
    Execute a GraphQL query against the Monday.com API.
    Returns the parsed JSON response or raises an exception on error.
    """
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    try:
        response = requests.post(MONDAY_API_URL, json=payload, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            error_msgs = [e.get("message", str(e)) for e in data["errors"]]
            logger.error(f"Monday.com API errors: {error_msgs}")
            raise Exception(f"Monday.com API errors: {'; '.join(error_msgs)}")

        return data.get("data", {})

    except requests.exceptions.Timeout:
        logger.error("Monday.com API request timed out")
        raise Exception("Monday.com API request timed out. Please try again.")
    except requests.exceptions.HTTPError as e:
        logger.error(f"Monday.com API HTTP error: {e}")
        raise Exception(f"Monday.com API HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Monday.com API request failed: {e}")
        raise Exception(f"Monday.com API request failed: {e}")


def get_board_schema(board_id: str) -> dict:
    """
    Fetch the column names and types for a board so the agent
    understands the data structure before querying.

    Returns: {
        "board_name": str,
        "columns": [{"id": str, "title": str, "type": str}, ...]
    }
    """
    query = """
    query ($boardId: [ID!]!) {
        boards(ids: $boardId) {
            name
            columns {
                id
                title
                type
                settings_str
            }
        }
    }
    """
    data = _make_request(query, {"boardId": [board_id]})
    boards = data.get("boards", [])

    if not boards:
        raise Exception(f"Board with ID {board_id} not found")

    board = boards[0]
    return {
        "board_name": board["name"],
        "columns": [
            {
                "id": col["id"],
                "title": col["title"],
                "type": col["type"],
            }
            for col in board["columns"]
        ],
    }


def get_all_items(board_id: str) -> list[dict]:
    """
    Fetch all items and their column values from a board.
    Handles pagination for boards with more than 500 items.

    Returns a list of dicts, each representing one item:
    [
        {
            "id": str,
            "name": str,
            "group": {"id": str, "title": str},
            "columns": {column_title: value, ...}
        },
        ...
    ]
    """
    all_items = []
    cursor = None

    # First page query (uses items_page at the board level)
    first_page_query = """
    query ($boardId: [ID!]!) {
        boards(ids: $boardId) {
            items_page(limit: 500) {
                cursor
                items {
                    id
                    name
                    group {
                        id
                        title
                    }
                    column_values {
                        id
                        column {
                            title
                        }
                        text
                        value
                    }
                }
            }
        }
    }
    """

    # Subsequent pages query (uses next_items_page)
    next_page_query = """
    query ($cursor: String!) {
        next_items_page(cursor: $cursor, limit: 500) {
            cursor
            items {
                id
                name
                group {
                    id
                    title
                }
                column_values {
                    id
                    column {
                        title
                    }
                    text
                    value
                }
            }
        }
    }
    """

    # Fetch first page
    data = _make_request(first_page_query, {"boardId": [board_id]})
    boards = data.get("boards", [])

    if not boards:
        raise Exception(f"Board with ID {board_id} not found")

    items_page = boards[0].get("items_page", {})
    items = items_page.get("items", [])
    cursor = items_page.get("cursor")
    all_items.extend(items)

    # Fetch subsequent pages
    while cursor:
        data = _make_request(next_page_query, {"cursor": cursor})
        next_page = data.get("next_items_page", {})
        items = next_page.get("items", [])
        cursor = next_page.get("cursor")
        all_items.extend(items)

    # Transform items into a cleaner format
    return [_transform_item(item) for item in all_items]


def get_items_by_column_value(board_id: str, column_id: str, value: str) -> list[dict]:
    """
    Fetch items from a board that match a specific column value.

    Args:
        board_id: The board to search in
        column_id: The column ID to filter on
        value: The value to match

    Returns: same format as get_all_items
    """
    all_items = []
    cursor = None

    first_page_query = """
    query ($boardId: ID!, $columnId: String!, $value: CompareValue!) {
        items_page_by_column_values(
            board_id: $boardId,
            limit: 500,
            columns: [{column_id: $columnId, column_values: [$value]}]
        ) {
            cursor
            items {
                id
                name
                group {
                    id
                    title
                }
                column_values {
                    id
                    column {
                        title
                    }
                    text
                    value
                }
            }
        }
    }
    """

    next_page_query = """
    query ($cursor: String!) {
        next_items_page(cursor: $cursor, limit: 500) {
            cursor
            items {
                id
                name
                group {
                    id
                    title
                }
                column_values {
                    id
                    column {
                        title
                    }
                    text
                    value
                }
            }
        }
    }
    """

    data = _make_request(first_page_query, {
        "boardId": board_id,
        "columnId": column_id,
        "value": value,
    })

    items_page = data.get("items_page_by_column_values", {})
    items = items_page.get("items", [])
    cursor = items_page.get("cursor")
    all_items.extend(items)

    while cursor:
        data = _make_request(next_page_query, {"cursor": cursor})
        next_page = data.get("next_items_page", {})
        items = next_page.get("items", [])
        cursor = next_page.get("cursor")
        all_items.extend(items)

    return [_transform_item(item) for item in all_items]


def get_board_groups(board_id: str) -> list[dict]:
    """
    Fetch the groups within a board (e.g. pipeline stages or categories).

    Returns: [{"id": str, "title": str, "color": str}, ...]
    """
    query = """
    query ($boardId: [ID!]!) {
        boards(ids: $boardId) {
            groups {
                id
                title
                color
            }
        }
    }
    """
    data = _make_request(query, {"boardId": [board_id]})
    boards = data.get("boards", [])

    if not boards:
        raise Exception(f"Board with ID {board_id} not found")

    return boards[0].get("groups", [])


def _transform_item(item: dict) -> dict:
    """
    Transform a raw Monday.com item into a clean dictionary.
    Maps column titles to their text values for easy consumption.
    """
    columns = {}
    for col_val in item.get("column_values", []):
        title = col_val.get("column", {}).get("title", col_val.get("id", "unknown"))
        text = col_val.get("text", "")
        columns[title] = text if text else None

    group = item.get("group", {})
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "group": {
            "id": group.get("id", ""),
            "title": group.get("title", ""),
        },
        "columns": columns,
    }
