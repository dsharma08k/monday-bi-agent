"""
AI Agent Layer
Two-stage query processing using Groq (LLaMA 3.3 70B):
  Stage 1: Query understanding — produces a structured JSON plan
  Stage 2: Response generation — produces a founder-level briefing
Supports follow-up questions via conversation history.
"""

import json
import logging
from datetime import datetime

from groq import Groq

from config import GROQ_API_KEY, MONDAY_DEALS_BOARD_ID, MONDAY_WORKORDERS_BOARD_ID
from monday_client import get_board_schema, get_all_items
from data_cleaner import clean_board_data

logger = logging.getLogger(__name__)

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

QUERY_UNDERSTANDING_PROMPT = """You are a query planner for a business intelligence system connected to Monday.com boards.

You have access to two boards:

DEALS BOARD (board_id: {deals_board_id}):
{deals_schema}

WORK ORDERS BOARD (board_id: {workorders_board_id}):
{workorders_schema}

AVAILABLE DATA VALUES:
{available_values}

Given a user question, return a JSON plan specifying how to answer it.

RULES:
1. Return ONLY valid JSON — no markdown, no extra text, no code fences.
2. If you can answer the question, return a query plan with this structure:
{{
  "boards_to_query": ["deals", "workorders"],
  "filters": {{
    "sector": null,
    "status": null,
    "date_range": {{
      "start": null,
      "end": null
    }}
  }},
  "metrics": ["total_value", "count", "average_value"],
  "analysis_type": "summary|comparison|trend|detail|risk",
  "explanation": "Brief explanation of what data is needed and why"
}}
3. If the question is too vague or ambiguous to create a good plan, return:
{{
  "needs_clarification": true,
  "clarification_question": "Your specific question to the user to clarify their intent"
}}
   Use this ONLY when the query is genuinely ambiguous — for example, "tell me something" or "help me". Do NOT ask for clarification on normal business questions like "how is our pipeline?" — just answer those.
4. For "boards_to_query", include only boards relevant to the question.
5. For "filters", set values only if the user mentions specific sectors, statuses, or date ranges. Use null for unspecified filters.
6. IMPORTANT: For sector filters, you MUST use the EXACT sector names from the AVAILABLE DATA VALUES listed above. Map user terms to the closest matching sector (e.g. "energy" maps to "Renewables" or "Powerline").
7. For "metrics", list what calculations are needed. Options: "total_value", "count", "average_value", "list_items", "group_by", "overdue_check", "pipeline_summary".
8. For "analysis_type": use "summary" for overview questions, "comparison" for comparing segments, "trend" for time-based analysis, "detail" for specific item lists, "risk" for stalling/overdue analysis.
9. Today's date is {today}. Use this for any relative date calculations (e.g., "this quarter", "overdue").
10. "This quarter" means Q1 2026: January 1 to March 31, 2026.
"""

RESPONSE_GENERATION_PROMPT = """You are a sharp business analyst giving a founder a concise briefing. You work at Skylark Drones, a drone services company.

INSTRUCTIONS:
1. Answer the question directly, like you're briefing a CEO.
2. Lead with the key insight or number.
3. Include supporting data points and percentages where relevant.
4. If there are data quality issues, mention them briefly at the end as a caveat.
5. Use bullet points for clarity when listing multiple data points.
6. Keep it conversational but data-driven — no filler, no hedging.
7. Format numbers nicely (e.g., "₹12.5L" instead of "1250000").
8. If comparing segments, use clear comparisons.
9. Do NOT dump raw data. Synthesize insights.
10. Keep responses concise — ideally 3-8 sentences with key numbers.

DATA QUALITY NOTES:
{quality_notes}

TODAY'S DATE: {today}
"""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _format_schema(schema: dict) -> str:
    """Format a board schema for inclusion in prompts."""
    lines = [f"Board: {schema['board_name']}"]
    lines.append("Columns:")
    for col in schema["columns"]:
        lines.append(f"  - {col['title']} (type: {col['type']}, id: {col['id']})")
    return "\n".join(lines)


def _get_unique_values(items: list[dict], columns: list[str]) -> dict:
    """Extract unique non-null values for specified columns from raw items."""
    result = {}
    for col in columns:
        values = set()
        for item in items:
            v = item.get("columns", {}).get(col)
            if v and str(v).strip():
                values.add(str(v).strip())
        if values:
            result[col] = sorted(values)
    return result


def _format_number(value: float | None) -> str:
    """Format a number in Indian business style."""
    if value is None:
        return "N/A"
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:.1f}Cr"
    elif abs(value) >= 100_000:
        return f"₹{value / 100_000:.1f}L"
    elif abs(value) >= 1_000:
        return f"₹{value / 1_000:.1f}K"
    else:
        return f"₹{value:,.0f}"


def _apply_filters(items: list[dict], filters: dict, board_type: str) -> list[dict]:
    """Apply filters from the query plan to the cleaned data."""
    filtered = items

    sector = filters.get("sector")
    if sector:
        # Handle both string and list values
        if isinstance(sector, list):
            sector_list = [s.lower() for s in sector]
        else:
            sector_list = [sector.lower()]
        sector_col = "Sector/service" if board_type == "deals" else "Sector"
        filtered = [
            item for item in filtered
            if item["columns"].get(sector_col)
            and any(s in str(item["columns"][sector_col]).lower() for s in sector_list)
        ]

    status = filters.get("status")
    if status:
        if isinstance(status, list):
            status_list = [s.lower() for s in status]
        else:
            status_list = [status.lower()]
        status_col = "Deal Status" if board_type == "deals" else "Execution Status"
        filtered = [
            item for item in filtered
            if item["columns"].get(status_col)
            and any(s in str(item["columns"][status_col]).lower() for s in status_list)
        ]

    date_range = filters.get("date_range", {})
    start_date = date_range.get("start") if date_range else None
    end_date = date_range.get("end") if date_range else None

    if start_date or end_date:
        date_col = "Tentative Close Date" if board_type == "deals" else "Probable End Date"
        date_filtered = []
        for item in filtered:
            item_date = item["columns"].get(date_col)
            if not item_date:
                continue
            try:
                d = datetime.strptime(item_date, "%Y-%m-%d")
                if start_date and d < datetime.strptime(start_date, "%Y-%m-%d"):
                    continue
                if end_date and d > datetime.strptime(end_date, "%Y-%m-%d"):
                    continue
                date_filtered.append(item)
            except ValueError:
                continue
        filtered = date_filtered

    return filtered


def _compute_metrics(items: list[dict], metrics: list[str], board_type: str) -> dict:
    """Compute requested metrics on filtered data."""
    results = {}

    value_col = "Masked Deal value" if board_type == "deals" else "Amount in Rupees (Excl of GST) (Masked)"

    values = []
    for item in items:
        v = item["columns"].get(value_col)
        if v is not None:
            try:
                values.append(float(v))
            except (ValueError, TypeError):
                pass

    if "total_value" in metrics:
        results["total_value"] = sum(values) if values else 0
        results["total_value_formatted"] = _format_number(results["total_value"])

    if "count" in metrics:
        results["count"] = len(items)

    if "average_value" in metrics:
        results["average_value"] = sum(values) / len(values) if values else 0
        results["average_value_formatted"] = _format_number(results["average_value"])

    if "group_by" in metrics:
        groups = {}
        sector_col = "Sector/service" if board_type == "deals" else "Sector"
        for item in items:
            key = item["columns"].get(sector_col) or "Unknown"
            if key not in groups:
                groups[key] = {"count": 0, "total_value": 0}
            groups[key]["count"] += 1
            v = item["columns"].get(value_col)
            if v is not None:
                try:
                    groups[key]["total_value"] += float(v)
                except (ValueError, TypeError):
                    pass
        for k, v in groups.items():
            v["total_value_formatted"] = _format_number(v["total_value"])
        results["groups"] = groups

    if "pipeline_summary" in metrics:
        stage_col = "Deal Stage" if board_type == "deals" else "Execution Status"
        stages = {}
        for item in items:
            stage = item["columns"].get(stage_col) or "Unknown"
            if stage not in stages:
                stages[stage] = {"count": 0, "total_value": 0}
            stages[stage]["count"] += 1
            v = item["columns"].get(value_col)
            if v is not None:
                try:
                    stages[stage]["total_value"] += float(v)
                except (ValueError, TypeError):
                    pass
        for k, v in stages.items():
            v["total_value_formatted"] = _format_number(v["total_value"])
        results["pipeline"] = stages

    if "overdue_check" in metrics:
        today = datetime.now()
        overdue_items = []
        end_col = "Tentative Close Date" if board_type == "deals" else "Probable End Date"
        status_col = "Deal Status" if board_type == "deals" else "Execution Status"
        for item in items:
            end_date = item["columns"].get(end_col)
            status = item["columns"].get(status_col, "")
            if end_date:
                try:
                    d = datetime.strptime(end_date, "%Y-%m-%d")
                    if d < today and status and status.lower() not in ["closed", "closed won", "closed lost", "completed"]:
                        overdue_items.append({
                            "name": item["name"],
                            "end_date": end_date,
                            "status": status,
                            "value": _format_number(
                                float(item["columns"].get(value_col, 0) or 0)
                            ),
                        })
                except (ValueError, TypeError):
                    pass
        results["overdue_items"] = overdue_items
        results["overdue_count"] = len(overdue_items)

    if "list_items" in metrics:
        item_summaries = []
        for item in items[:50]:
            summary = {"name": item["name"]}
            for col, val in item["columns"].items():
                if val is not None:
                    summary[col] = val
            item_summaries.append(summary)
        results["items"] = item_summaries

    return results


def _call_groq(system_prompt: str, messages: list[dict], max_tokens: int = 1024) -> str:
    """Make a call to Groq API and return the response text."""
    groq_messages = [{"role": "system", "content": system_prompt}]
    groq_messages.extend(messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=groq_messages,
        max_tokens=max_tokens,
        temperature=0.1,
    )

    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------

def process_query(message: str, history: list[dict] = None) -> dict:
    """
    Process a user's business intelligence query.

    Args:
        message: The user's question
        history: Conversation history list of {"role": str, "content": str}

    Returns:
        {
            "answer": str,
            "action_trace": [str, ...],
            "data_quality_report": dict
        }
    """
    if history is None:
        history = []

    action_trace = []
    combined_quality_report = {
        "total_items": 0,
        "missing_values": 0,
        "unparseable_dates": 0,
        "unparseable_numbers": 0,
        "summary": "",
        "issues": [],
    }

    try:
        # ----- Step 1: Fetch board schemas -----
        action_trace.append("Fetching board schemas from Monday.com...")
        deals_schema = get_board_schema(MONDAY_DEALS_BOARD_ID)
        workorders_schema = get_board_schema(MONDAY_WORKORDERS_BOARD_ID)
        action_trace.append(f"Retrieved schemas: Deals ({len(deals_schema['columns'])} columns), Work Orders ({len(workorders_schema['columns'])} columns)")

        # Fetch a quick sample to get unique values for key columns
        action_trace.append("Fetching available filter values...")
        deals_items_raw = get_all_items(MONDAY_DEALS_BOARD_ID)
        deals_unique = _get_unique_values(deals_items_raw, ["Sector/service", "Deal Status", "Deal Stage", "Closure Probability", "Product deal"])
        wo_items_raw = get_all_items(MONDAY_WORKORDERS_BOARD_ID)
        wo_unique = _get_unique_values(wo_items_raw, ["Sector", "Execution Status", "Nature of Work", "Type of Work", "Billing Status"])

        available_values = "Deals Board Available Values:\n"
        for col, vals in deals_unique.items():
            available_values += f"  {col}: {', '.join(vals)}\n"
        available_values += "\nWork Orders Board Available Values:\n"
        for col, vals in wo_unique.items():
            available_values += f"  {col}: {', '.join(vals)}\n"

        # ----- Step 2: Query Understanding (LLM Stage 1) -----
        action_trace.append("Analyzing query with AI to create execution plan...")

        today = datetime.now().strftime("%Y-%m-%d")
        system_prompt = QUERY_UNDERSTANDING_PROMPT.format(
            deals_board_id=MONDAY_DEALS_BOARD_ID,
            workorders_board_id=MONDAY_WORKORDERS_BOARD_ID,
            deals_schema=_format_schema(deals_schema),
            workorders_schema=_format_schema(workorders_schema),
            available_values=available_values,
            today=today,
        )

        # Build messages including history for context
        messages = []
        for h in history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        plan_text = _call_groq(system_prompt, messages, max_tokens=1024)

        # Try to parse JSON from the response (handle markdown code fences)
        if plan_text.startswith("```"):
            plan_text = plan_text.split("```")[1]
            if plan_text.startswith("json"):
                plan_text = plan_text[4:]
            plan_text = plan_text.strip()

        try:
            query_plan = json.loads(plan_text)
        except json.JSONDecodeError:
            json_match = plan_text[plan_text.find("{"):plan_text.rfind("}") + 1]
            query_plan = json.loads(json_match)

        # Check if the LLM needs clarification
        if query_plan.get("needs_clarification"):
            clarification = query_plan.get("clarification_question", "Could you be more specific about what you'd like to know?")
            action_trace.append(f"Need more info: {clarification}")
            return {
                "answer": clarification,
                "action_trace": action_trace,
                "data_quality_report": combined_quality_report,
            }

        action_trace.append(f"Query plan: query {', '.join(query_plan.get('boards_to_query', []))} board(s), analysis type: {query_plan.get('analysis_type', 'unknown')}")

        # ----- Step 3: Fetch and clean data -----
        all_data = {}
        boards_to_query = query_plan.get("boards_to_query", ["deals"])
        filters = query_plan.get("filters", {})
        metrics = query_plan.get("metrics", ["count", "total_value"])

        for board in boards_to_query:
            if board == "deals":
                action_trace.append("Processing deals data...")
                raw_items = deals_items_raw  # Already fetched above
                action_trace.append(f"Using {len(raw_items)} deals from Monday.com")

                action_trace.append("Cleaning and normalizing deals data...")
                cleaned_items, quality_report = clean_board_data(raw_items)
                combined_quality_report["total_items"] += quality_report["total_items"]
                combined_quality_report["missing_values"] += quality_report["missing_values"]
                combined_quality_report["unparseable_dates"] += quality_report["unparseable_dates"]
                combined_quality_report["unparseable_numbers"] += quality_report["unparseable_numbers"]
                combined_quality_report["issues"].extend(quality_report.get("issues", []))

                filtered_items = _apply_filters(cleaned_items, filters, "deals")
                action_trace.append(f"After filtering: {len(filtered_items)} deals match criteria")

                computed = _compute_metrics(filtered_items, metrics, "deals")
                all_data["deals"] = {
                    "items": filtered_items,
                    "metrics": computed,
                    "quality": quality_report,
                }

            elif board == "workorders":
                action_trace.append("Processing work orders data...")
                raw_items = wo_items_raw  # Already fetched above
                action_trace.append(f"Using {len(raw_items)} work orders from Monday.com")

                action_trace.append("Cleaning and normalizing work order data...")
                cleaned_items, quality_report = clean_board_data(raw_items)
                combined_quality_report["total_items"] += quality_report["total_items"]
                combined_quality_report["missing_values"] += quality_report["missing_values"]
                combined_quality_report["unparseable_dates"] += quality_report["unparseable_dates"]
                combined_quality_report["unparseable_numbers"] += quality_report["unparseable_numbers"]
                combined_quality_report["issues"].extend(quality_report.get("issues", []))

                filtered_items = _apply_filters(cleaned_items, filters, "workorders")
                action_trace.append(f"After filtering: {len(filtered_items)} work orders match criteria")

                computed = _compute_metrics(filtered_items, metrics, "workorders")
                all_data["workorders"] = {
                    "items": filtered_items,
                    "metrics": computed,
                    "quality": quality_report,
                }

        # Update combined summary
        combined_quality_report["summary"] = (
            f"{combined_quality_report['missing_values']} missing values, "
            f"{combined_quality_report['unparseable_dates']} unparseable dates, "
            f"{combined_quality_report['unparseable_numbers']} unparseable numbers "
            f"across {combined_quality_report['total_items']} total items."
        )

        # ----- Step 4: Response Generation (LLM Stage 2) -----
        action_trace.append("Generating business insight response...")

        data_summary = {}
        for board_name, board_data in all_data.items():
            data_summary[board_name] = {
                "metrics": board_data["metrics"],
                "total_items_queried": len(board_data["items"]),
                "sample_items": [
                    {"name": item["name"], **{k: v for k, v in item["columns"].items() if v is not None}}
                    for item in board_data["items"][:15]
                ],
            }

        response_system = RESPONSE_GENERATION_PROMPT.format(
            quality_notes=combined_quality_report["summary"],
            today=today,
        )

        response_messages = []
        for h in history[-10:]:
            response_messages.append({"role": h["role"], "content": h["content"]})

        response_messages.append({
            "role": "user",
            "content": f"""User Question: {message}

Query Plan: {json.dumps(query_plan, indent=2)}

Data Retrieved: {json.dumps(data_summary, indent=2, default=str)}

Please provide a concise, insight-driven answer based on this data.""",
        })

        answer = _call_groq(response_system, response_messages, max_tokens=2048)
        action_trace.append("Response generated successfully")

        return {
            "answer": answer,
            "action_trace": action_trace,
            "data_quality_report": combined_quality_report,
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse query plan JSON: {e}")
        action_trace.append(f"Error parsing AI query plan: {e}")
        return {
            "answer": "I had trouble understanding your question. Could you rephrase it? I need to create a clear plan to query the right data.",
            "action_trace": action_trace,
            "data_quality_report": combined_quality_report,
        }
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        error_str = str(e)
        # Handle Groq rate limit errors gracefully
        if "429" in error_str or "rate_limit" in error_str.lower() or "Rate limit" in error_str:
            action_trace.append("Rate limit reached — waiting for API quota to reset")
            return {
                "answer": "Our AI service is temporarily at capacity. This usually resets within a few minutes. Please try again shortly.",
                "action_trace": action_trace,
                "data_quality_report": combined_quality_report,
            }
        action_trace.append(f"Error: {error_str}")
        return {
            "answer": f"Something went wrong while processing your query. Please try again.",
            "action_trace": action_trace,
            "data_quality_report": combined_quality_report,
        }
