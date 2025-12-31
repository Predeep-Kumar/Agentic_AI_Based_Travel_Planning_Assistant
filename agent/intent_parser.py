import json
import re
from datetime import date


GENERIC_PHRASES = {
    "plan a trip",
    "plan trip",
    "trip",
    "travel",
    "vacation",
    "holiday",
    "tour",
    "family trip",
    "business trip",
}



# SAFE JSON EXTRACTION

def _extract_json(text: str) -> dict:
    matches = re.findall(r"\{[\s\S]*?\}", text)
    for m in matches:
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue
    return {}


# RULE-BASED EXTRACTION (PRIMARY)

def _rule_based_extract(user_query: str) -> dict:
    """
    Deterministic extraction (FAST).
    Covers common human language patterns.
    """
    text = user_query.lower()
    extracted = {}

    # FROM → TO 
  
    m = re.search(r"from\s+([a-z\s]+?)\s+to\s+([a-z\s]+)", text)
    if m:
        extracted["source"] = m.group(1).title().strip()
        extracted["destination"] = m.group(2).title().strip()
        return extracted  # 🚨 stop early – this is authoritative


 
    # X FROM Y (WEAK SIGNAL)
  
    m = re.search(r"([a-z\s]+?)\s+from\s+([a-z\s]+)", text)
    if m:
        possible_dest = m.group(1).strip()
        source = m.group(2).title().strip()

        extracted["source"] = source

        if possible_dest not in GENERIC_PHRASES:
            extracted["destination"] = possible_dest.title()

 
    # destination only
    m = re.search(r"\bto\s+([a-z\s]{2,20})$", text)
    if m and "from" not in text:
        candidate = m.group(1).strip()
        if candidate not in GENERIC_PHRASES:
            extracted.setdefault("destination", candidate.title())
 
    # TRIP TYPE 
 
    if any(k in text for k in [
        "round trip", "roundtrip", "return trip", "two way", "2 way", "both ways", "return"
    ]):
        extracted["trip_type"] = "round_trip"

    elif any(k in text for k in [
        "one way", "one-way", "single trip", "no return"
    ]):
        extracted["trip_type"] = "one_way"

 
    # TRAVELERS
  
    if "me and my wife" in text or "me and my husband" in text:
        extracted["travelers"] = 2

    m = re.search(r"(\d+)\s*(people|person|persons|travellers|travelers|pax)", text)
    if m:
        extracted["travelers"] = int(m.group(1))


    # DAYS

    m = re.search(r"for\s+(\d+)\s*day", text)
    if m:
        extracted["days"] = int(m.group(1))

    if "one week" in text:
        extracted["days"] = 7


    # DATE

    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if m:
        d = date.fromisoformat(m.group(1))
        if d > date.today():
            extracted["travel_date"] = m.group(1)


    # BUDGET

    if any(k in text for k in ["budget", "budget friendly", "low cost", "cheap"]):
        extracted.setdefault("preferences", {})["budget"] = "budget"
    elif "luxury" in text:
        extracted.setdefault("preferences", {})["budget"] = "luxury"
    elif "mid" in text:
        extracted.setdefault("preferences", {})["budget"] = "mid-range"

    return extracted



# MAIN PARSER (RULES → LLM → MERGE)

def parse_travel_intent(llm, user_query: str, temp_state: dict) -> dict:
    """
    Bullet-proof intent parser:
    - Rule-based FIRST
    - LLM fills gaps ONLY
    - Never overwrites
    """

    final = {}


    #  RULE-BASED FIRST

    rule_data = _rule_based_extract(user_query)

    for k, v in rule_data.items():
        if k not in temp_state:
            continue
        if temp_state.get(k) is not None:
            continue

        if k == "preferences":
            final.setdefault("preferences", {})
            for pk, pv in v.items():
                if temp_state["preferences"].get(pk) is None:
                    final["preferences"][pk] = pv
        else:
            final[k] = v

    #  LLM (ONLY IF SOMETHING IS STILL MISSING)

    missing_keys = [
        k for k in temp_state
        if k not in ("preferences", "trip_type")
        and temp_state.get(k) is None
        and k not in final
    ]

    if missing_keys:
        prompt = f"""
        You are a travel intent extractor for a travel planning assistant.

        Your task is to extract travel-related information from the user's message and fill ONLY the fields that are currently null in the provided JSON state.
        ⚠️ Do NOT change, overwrite, or re-derive any fields that already have values.

        ━━━━━━━━━━━━━━━━━━━━
        AVAILABLE FIELDS
        ━━━━━━━━━━━━━━━━━━━━
        - source: Departure city or location (e.g., "Delhi", "Mumbai")
        - destination: Arrival city or location (e.g., "Goa", "Bangalore")
        - travel_date: Travel date in YYYY-MM-DD format (must be a future date)
        - trip_type: One of ["one_way", "round_trip"]
        - days: Total number of days for the trip (integer)
        - travelers: Number of people traveling (integer)
        - preferences:
            - budget: One of ["budget", "mid-range", "luxury"]
        - interests: Optional list of strings

        ━━━━━━━━━━━━━━━━━━━━
        STRICT RULES
        ━━━━━━━━━━━━━━━━━━━━
        - Extract information ONLY if it is explicitly mentioned or clearly implied.
        - If a field already has a value in the JSON state, DO NOT modify it.
        - If the user message is conversational, vague, or non-informational, return an empty JSON object {{}}.
        - NEVER guess dates, days, travelers, budget, or locations.
        - If no new information can be extracted, return {{}}.
        - Return ONLY valid JSON. No explanations. No markdown.
        - trip_type: One of ["one_way", "round_trip"]

        ━━━━━━━━━━━━━━━━━━━━
        CURRENT STATE
        ━━━━━━━━━━━━━━━━━━━━
        {json.dumps(temp_state, indent=2)}

        ━━━━━━━━━━━━━━━━━━━━
        EXAMPLES (IMPORTANT)
        ━━━━━━━━━━━━━━━━━━━━
        
        

        User: "Plan a trip to Goa from Delhi for 5 days starting June 15, 2025 with 2 people on a budget"
        Return:
        {{"source":"Delhi","destination":"Goa","travel_date":"2025-06-15","days":5,"travelers":2,"preferences":{{"budget":"budget"}}}}

        User: "trip from mumbai to goa"
        Return: {{"source":"Mumbai","destination":"Goa"}}

        User: "from delhi"
        Return: {{"source":"Delhi"}}

        User: "we are 3 people"
        Return: {{"travelers":3}}

        User: "5 days"
        Return: {{"days":5}}

        User: "budget trip"
        Return: {{"preferences":{{"budget":"budget"}}}}

        User: "luxury"
        Return: {{"preferences":{{"budget":"luxury"}}}}

        User: "mid range"
        Return: {{"preferences":{{"budget":"mid-range"}}}}

        ━━━━━━━━━━━━━━━━━━━━
        DATE HANDLING
        ━━━━━━━━━━━━━━━━━━━━

        User: "starting July 1"
        Return: {{"travel_date":"2025-07-01"}}

        User: "next friday"
        Return: {{"travel_date":"<future YYYY-MM-DD>"}}

        User: "last monday"
        Return: {{}}

        ━━━━━━━━━━━━━━━━━━━━
        NATURAL LANGUAGE
        ━━━━━━━━━━━━━━━━━━━━

        User: "plan a trip to goa"
        Return: {{"destination":"Goa"}}

        User: "thinking of traveling to bangalore"
        Return: {{"destination":"Bangalore"}}

        User: "i want to go on a trip"
        Return: {{}}

        User: "family trip"
        Return: {{}}

        ━━━━━━━━━━━━━━━━━━━━
        CONFIRMATIONS (DO NOTHING)
        ━━━━━━━━━━━━━━━━━━━━

        User: "yes" | "ok" | "sounds good" | "correct" | "thanks"
        Return: {{}}

        ━━━━━━━━━━━━━━━━━━━━
        CHANGE REQUESTS
        ━━━━━━━━━━━━━━━━━━━━

        User: "change destination to goa"
        If destination is NULL → {{"destination":"Goa"}}
        Else → {{}}

        

        1) User: "Plan a trip to Goa from Delhi for 5 days starting June 15, 2025 with 2 people on a budget"
        Extract:
        {{
        "source": "Delhi",
        "destination": "Goa",
        "travel_date": "2025-06-15",
        "days": 5,
        "travelers": 2,
        "preferences": {{"budget": "budget"}}
        }}

        2) User: "I want to go to Mumbai"
        Extract:
        {{"destination": "Mumbai"}}

        3) User: "from Delhi"
        Extract:
        {{"source": "Delhi"}}

        4) User: "for 3 people"
        Extract:
        {{"travelers": 3}}

        5) User: "5 days"
        Extract:
        {{"days": 5}}

        6) User: "starting July 1"
        Extract:
        {{"travel_date": "2025-07-01"}}

        7) User: "budget trip"
        Extract:
        {{"preferences": {{"budget": "budget"}}}}

        8) User: "luxury"
        Extract:
        {{"preferences": {{"budget": "luxury"}}}}

        9) User: "mid range"
        Extract:
        {{"preferences": {{"budget": "mid-range"}}}}

        10) User: "me and my wife"
        Extract:
        {{"travelers": 2}}

        ━━━━━━━━━━━━━━━━━━━━
        NATURAL / CASUAL PHRASES (IMPORTANT)
        ━━━━━━━━━━━━━━━━━━━━

        11) User: "plan a trip to goa"
        Extract:
        {{"destination": "Goa"}}

        12) User: "i want to go on a trip"
        Extract:
        {{}}

        13) User: "we are planning a vacation"
        Extract:
        {{}}

        14) User: "thinking of traveling to bangalore"
        Extract:
        {{"destination": "Bangalore"}}

        15) User: "trip from mumbai to goa"
        Extract:
        {{"source": "Mumbai", "destination": "Goa"}}

        16) User: "mumbai to goa round trip"
        Extract:
        {{"source": "Mumbai", "destination": "Goa"}}

        17) User: "goa from delhi"
        Extract:
        {{"source": "Delhi", "destination": "Goa"}}

        18) User: "next friday"
        Extract:
        {{"travel_date": "<resolve to future YYYY-MM-DD>"}}

        19) User: "one week trip"
        Extract:
        {{"days": 7}}

        20) User: "family trip"
        Extract:
        {{}}

        ━━━━━━━━━━━━━━━━━━━━
        CONVERSATIONAL / NON-INFORMATIONAL
        ━━━━━━━━━━━━━━━━━━━━

        21) User: "hi"
        Extract:
        {{}}

        22) User: "hello"
        Extract:
        {{}}

        23) User: "how are you"
        Extract:
        {{}}

        24) User: "ok"
        Extract:
        {{}}

        25) User: "yes"
        Extract:
        {{}}

        26) User: "sounds good"
        Extract:
        {{}}

        27) User: "thanks"
        Extract:
        {{}}

        ━━━━━━━━━━━━━━━━━━━━
        USER MESSAGE
        ━━━━━━━━━━━━━━━━━━━━
        {user_query}
        """
        def _sanitize_llm_output(data: dict) -> dict:
            clean = {}

            for k, v in data.items():
                if isinstance(v, str):
                    if v.lower() in GENERIC_PHRASES:
                        continue
                clean[k] = v

            return clean
        
        try:
            response = llm.invoke(prompt)
            raw = response.content if hasattr(response, "content") else str(response)
            llm_data = _sanitize_llm_output(_extract_json(raw))
        except Exception:
            llm_data = {}

        for k, v in llm_data.items():
            if k not in temp_state:
                continue
            if temp_state.get(k) is not None:
                continue
            if k in final:
                continue

            if k == "preferences":
                final.setdefault("preferences", {})
                for pk, pv in v.items():
                    if temp_state["preferences"].get(pk) is None:
                        final["preferences"][pk] = pv
            else:
                final[k] = v

    return final
