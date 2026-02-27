# Decision Log -- Monday.com BI Agent

**Author:** Divyanshu Sharma | **Date:** February 2026

---

## Tech Stack Choices and Justification

The backend uses **Python with FastAPI** because FastAPI provides automatic OpenAPI documentation, built-in request validation via Pydantic, and async support -- all critical for a rapid prototype that still needs to be production-quality. The LLM layer uses **Groq's inference API** with the LLaMA 3.3 70B Versatile model, chosen for its extremely fast inference speed (hundreds of tokens per second), strong instruction-following ability, and reliable structured JSON output. Since each query involves two LLM calls, Groq's speed significantly improves user experience.

The frontend uses **React with Vite** rather than Streamlit. While Streamlit would have been faster to scaffold, it imposes a rigid top-to-bottom layout that makes it difficult to implement the required side-by-side action trace panel alongside the chat interface. React gives full control over the two-column layout (chat on left, trace and quality report on right) and allows for a polished, professional UI using **Tailwind CSS v4**. Deployment uses **HuggingFace Spaces with Docker** for the backend (free tier, supports secrets management) and **Vercel** for the React frontend.

Monday.com is integrated using **direct GraphQL REST API calls** via the `requests` library. While MCP (Model Context Protocol) integration was considered and is listed as a bonus, direct REST calls provide more predictable behavior within the 6-hour time constraint and avoid the complexity of maintaining a persistent MCP connection.

## Data Cleaning Strategy

The assignment explicitly states that the data is intentionally messy. The cleaning layer handles four categories of inconsistency:

**Dates** are normalized from multiple formats (DD/MM/YYYY, MM-DD-YYYY, written text like "26th Feb 2026") to ISO format using a cascading parser with `python-dateutil` as fallback. **Currency/numbers** strip symbols, handle K/M/Cr suffixes, and convert to float. **Text** fields are trimmed, whitespace-collapsed, and title-cased for consistency. **Status** values are mapped to canonical labels via a lookup dictionary (e.g., "in progress", "IN PROGRESS", "inprogress" all map to "In Progress"). Every cleaning operation contributes to a **data quality report** that counts missing values, unparseable fields, and normalization events. This report is displayed to the user alongside every agent response for full transparency.

## Agent Architecture and Data Flow

The agent operates in two stages with full action tracing.

**Stage 1 (Query Understanding):** The user's natural language question is sent to the LLM along with live board schemas and the actual unique values present in key columns (sectors, statuses, deal stages). The LLM returns a structured JSON plan specifying which boards to query, what filters to apply, what metrics to compute, and the analysis type. Providing actual column values prevents filter mismatches (e.g., user says "energy" but the data uses "Renewables").

**Stage 2 (Response Generation):** The backend executes the plan by fetching live data via GraphQL, cleaning it, applying filters, and computing metrics. The results are passed back to the LLM with a prompt instructing it to respond like a business analyst briefing a CEO: lead with the key insight, include supporting numbers, and note any data quality caveats.

Full data flow: User > React Frontend > FastAPI `/query` > LLM (query plan) > Monday.com GraphQL API (live fetch) > Data Cleaner > Metric Computation > LLM (response) > Frontend (answer + action trace + quality report).

## Assumptions

- Column names and types in Monday.com boards remain consistent with the imported CSV structure.
- Monday.com API rate limits (default ~5000 requests/10 minutes) are sufficient for the expected query volume.
- Board data fits within pagination limits (handled via cursor-based pagination).
- The masked/anonymized values in the data are treated as-is for aggregation and comparison.
- "This quarter" in queries refers to the current calendar quarter based on today's date.

## Improvements Given More Time

With additional time, I would implement: **MCP integration** for a more native Monday.com connection with real-time updates; **semantic caching with TTL** to avoid redundant API calls for repeated queries while still maintaining the live data requirement; a **multi-step query planner using tool calling** that allows the LLM to iteratively refine its data retrieval strategy for complex multi-board correlations; **streaming responses** via Server-Sent Events so the user sees the answer being generated in real-time; and **automated testing** with mock Monday.com responses to ensure data cleaning edge cases are covered.
