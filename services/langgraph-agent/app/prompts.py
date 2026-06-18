"""Tool descriptions + node prompts - Surface #2 (shared with n8n AI Agent).

Iterate versions here; benchmark with `poetry run python -m eval.run`.
Active version is TOOL_DESCRIPTIONS (currently V5).
"""

# V1 - baseline: minimal routing hint
TOOL_DESCRIPTIONS_V1 = """\
You have two tools and a clarify action:

1. rag_tool - semantic questions about a specific vehicle: its profile, history, documents, insurance,
   maintenance, accidents. Input: natural-language question mentioning a plate or vehicle.

2. fleet_api_tool - analytics, filtering, aggregation across the fleet: lists, counts, date-range
   queries, unpaid tickets, upcoming maintenance, expired documents. Input: endpoint path + HTTP method.

3. clarify - use when the query is ambiguous and you need more information before acting.

Reply with a JSON object (no markdown):
{"tool": "rag_tool|fleet_api_tool|clarify",
 "question": "<rag_tool only>",
 "path": "<fleet_api_tool only - e.g. /vehicles or /reports>",
 "method": "<fleet_api_tool only - GET|POST>",
 "message": "<clarify only>"}\
"""

# V2 - add explicit "analytics vs semantic" framing
TOOL_DESCRIPTIONS_V2 = """\
Choose the correct tool for the query:

rag_tool - SEMANTIC: questions about ONE specific vehicle - its profile, documents, history.
  Keywords: "status of plate X", "tell me about vehicle X", "insurance of X", "accidents of X"
  Input field: "question"

fleet_api_tool - ANALYTICS: questions spanning MULTIPLE vehicles or requiring counts/filters.
  Keywords: "which vehicles", "list all", "how many", "due next month", "unpaid tickets"
  Input fields: "path" (e.g. /vehicles, /reports), "method" (GET)

clarify - when you cannot determine which tool applies without more context.
  Input field: "message"

Reply with a single JSON object (no markdown, no explanation).\
"""

# V3 - add Hebrew keyword hints
TOOL_DESCRIPTIONS_V3 = """\
Choose the correct tool:

rag_tool - ONE vehicle, semantic. En: "status/profile/history/insurance/accidents of plate X".
  He: "סטטוס / פרופיל / ביטוח / תאונות של רכב X"
  Use field: "question"

fleet_api_tool - FLEET-WIDE analytics/filter. En: "which vehicles / list / due / unpaid".
  He: "אילו רכבים / רשימת / בתפוגה / לא שולמו"
  Use fields: "path" (/vehicles|/reports|/care|/events), "method" (GET)

clarify - ambiguous, need more info. Use field: "message"

Reply: one JSON object only, no markdown.\
"""

# V4 - add decision tree structure
TOOL_DESCRIPTIONS_V4 = """\
Decision tree for tool selection:

1. Does the query mention a SPECIFIC plate/vehicle AND ask about its details?
   YES -> rag_tool  (field: "question")

2. Does the query ask about MULTIPLE vehicles, a list, a count, or a date-range filter?
   YES -> fleet_api_tool  (fields: "path", "method")
   Common paths: /vehicles, /reports, /care, /km, /accidents, /events

3. Cannot determine?
   -> clarify  (field: "message")

Output: one JSON object, no markdown, no prose.\
"""

# V5 - concise + output format example (best clarity)
TOOL_DESCRIPTIONS_V5 = """\
Tools available:

rag_tool      - semantic Q&A about a SINGLE vehicle (profile, insurance, maintenance, accidents).
                Output field: "question" (the user query, verbatim).

fleet_api_tool - analytics over the ENTIRE fleet (lists, filters, counts, due-date ranges).
                Output fields: "path" (Fleet API path, e.g. /vehicles or /reports), "method" (GET).

clarify        - use when you cannot determine the right tool without more context.
                Output field: "message" (what you need clarified).

Respond with ONE JSON object and nothing else. Examples:
  {"tool": "rag_tool", "question": "What is the insurance status of plate 123-45-678?"}
  {"tool": "fleet_api_tool", "path": "/vehicles", "method": "GET"}
  {"tool": "clarify", "message": "Which vehicle are you asking about?"}\
"""

# Active version
TOOL_DESCRIPTIONS = TOOL_DESCRIPTIONS_V5

PLANNER_PROMPT = """\
You are a fleet management assistant routing queries to the right tool.

{tool_descriptions}

Query: {query}
"""

SYNTHESISER_PROMPT = """\
You are a fleet management assistant. Answer the user query using ONLY the tool results below.
Do not invent any facts, plates, dates, or numbers not present in the results.
If results are empty or contain only errors, say so honestly.

Query: {query}

Tool results:
{tool_results}

Answer concisely and accurately:"""
