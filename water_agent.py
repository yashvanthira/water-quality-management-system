"""
Multi-Agent Water Quality & Public Awareness Assistant.
Orchestrates:
1. Intent Recognition & Routing
2. Data Retrieval Tools (SQL, Hotspot finder, Geo search)
3. Domain Knowledge Retrieval (CPCB standards, BIS 10500, Health risks)
4. Synthesis Agent: Dual-mode (Gemini API via google-genai or Local Expert System)
"""

import os
import re
import json
import concurrent.futures
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from rag_engine import HybridRAGEngine
from purification_recommender import recommend_purification, format_purification_markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env file automatically
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Try importing google.genai
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class WaterQualityAgent:
    def __init__(self, api_key: Optional[str] = None, mode_override: Optional[str] = None, model_name: str = "gemini-3.5-flash-lite"):
        self.rag = HybridRAGEngine()
        self.model_name = model_name
        raw_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.api_key = raw_key.strip("'\" ") if raw_key else None
        self.mode_override = mode_override or ("llm" if self.api_key else "expert")
        self.genai_client = None

        if self.mode_override == "llm" and HAS_GENAI and self.api_key:
            try:
                self.genai_client = genai.Client(api_key=self.api_key)
                print(f"Gemini GenAI client initialized with key ({self.api_key[:8]}...) using {self.model_name}.")
            except Exception as e:
                print(f"Warning: Could not initialize Gemini client: {e}. Falling back to Expert Engine.")

    def reload_agent(self):
        """Refresh RAG memory with latest database records and user submissions."""
        self.rag.reload_index()

    # -------------------------------------------------------------
    # AGENT TOOLS
    # -------------------------------------------------------------

    def tool_find_station(self, query: str) -> List[Dict[str, Any]]:
        """Search station by river, location, station code, or state using hybrid retrieval."""
        # Check if numeric station code is mentioned
        stn_match = re.search(r'\b\d{4,5}\b', query)
        if stn_match:
            code = stn_match.group(0)
            res = self.rag.query_stations_sql(f"SELECT * FROM water_monitoring WHERE stn_code = {code} LIMIT 3")
            if res.get("status") == "success" and res.get("data"):
                return res["data"]

        # Hybrid search handles token ranking and semantic matching
        return self.rag.find_station_by_keywords(query, limit=5)

    def tool_get_pollution_hotspots(self, metric: str = "bod", water_body_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Find highest/lowest pollution stations."""
        where = f"WHERE water_body_type = '{water_body_type.upper()}'" if water_body_type else ""
        if "bod" in metric.lower():
            sql = f"SELECT stn_code, monitoring_location, state_name, water_body_type, bod_max, do_min, total_coliform_max, cpcb_class, wqi_score FROM water_monitoring {where} ORDER BY bod_max DESC LIMIT {limit}"
        elif "coliform" in metric.lower():
            sql = f"SELECT stn_code, monitoring_location, state_name, water_body_type, total_coliform_max, fecal_coliform_max, bod_max, cpcb_class, wqi_score FROM water_monitoring {where} ORDER BY total_coliform_max DESC LIMIT {limit}"
        elif "oxygen" in metric.lower() or "do" in metric.lower():
            sql = f"SELECT stn_code, monitoring_location, state_name, water_body_type, do_min, do_max, bod_max, cpcb_class, wqi_score FROM water_monitoring {where} ORDER BY do_min ASC LIMIT {limit}"
        else:
            sql = f"SELECT stn_code, monitoring_location, state_name, water_body_type, wqi_score, cpcb_class, bod_max, do_min FROM water_monitoring {where} ORDER BY wqi_score ASC LIMIT {limit}"

        res = self.rag.query_stations_sql(sql)
        return res.get("data", [])

    def tool_get_state_statistics(self, state_name: str) -> Dict[str, Any]:
        """Aggregate data for a specific state."""
        return self.rag.get_water_body_summary(state=state_name)

    def tool_retrieve_standards(self, query: str) -> List[Dict[str, Any]]:
        """Semantic search over CPCB, BIS 10500, health risks, and policies."""
        return self.rag.semantic_search(query, top_k=3)

    def tool_draft_grievance_letter(self, station_data: Dict[str, Any]) -> str:
        """Generate a formal citizen grievance petition for State Pollution Control Boards."""
        loc = station_data.get('monitoring_location', 'Water Body')
        stn = station_data.get('stn_code', 'N/A')
        state = station_data.get('state_name', 'State')
        bod = station_data.get('bod_max', 'N/A')
        coliform = station_data.get('total_coliform_max', 'N/A')
        do = station_data.get('do_min', 'N/A')
        cpcb = station_data.get('cpcb_class', 'Non-Compliant')

        letter = f"""
================================================================================
FORMAL NOTICE / CITIZEN GRIEVANCE PETITION UNDER THE WATER ACT, 1974
================================================================================
To,
The Member Secretary / Chairman,
{state} State Pollution Control Board (SPCB)

Subject: Urgent Complaint Regarding Severe Water Pollution at {loc} (Station Code: {stn})

Respected Authority,

I am writing as a concerned citizen to bring to your immediate notice the alarming contamination levels recorded at the monitored water body:

- Location: {loc}
- State: {state}
- CPCB Station Code: {stn}
- Water Body Category: {station_data.get('water_body_type', 'Freshwater')}
- CPCB Status: {cpcb}
- Water Quality Index (WQI): {station_data.get('wqi_score', 'N/A')} ({station_data.get('wqi_status', 'Critical')})

CRITICAL PARAMETER EXCEEDANCES:
1. Biochemical Oxygen Demand (BOD): Recorded peak at {bod} mg/L (Permissible Bathing limit is <= 3 mg/L).
2. Dissolved Oxygen (DO): Recorded floor at {do} mg/L (Critical threshold >= 5 mg/L).
3. Total Coliform Count: Recorded peak at {coliform} MPN/100ml (Desirable Bathing limit is <= 500 MPN/100ml).

VIOLATIONS OF STATUTORY STANDARDS:
Under Section 24 and Section 25 of the Water (Prevention and Control of Pollution) Act, 1974, releasing untreated sewage or industrial effluents into inland waters without treatment is a punishable offence. The current parameters render this water body severely non-compliant and hazardous to public health, local residents, and riparian ecosystems.

REQUESTED REMEDIAL ACTIONS:
1. Immediate inspection and audit of all upstream municipal outfalls and industrial discharge points.
2. Installation of in-situ bio-remediation or interception & diversion (I&D) networks feeding into functional STPs.
3. Public health advisory signage installed at the ghats/banks warning citizens against direct contact.
4. An action-taken report (ATR) published on the SPCB official portal within 30 days.

Submitted by:
Concerned Citizens Collective / Environmental Action Taskforce
Date: 2026-11-07
================================================================================
"""
        return letter.strip()

    # -------------------------------------------------------------
    # ORCHESTRATION & REASONING
    # -------------------------------------------------------------

    def classify_intent(self, query: str) -> str:
        """Classify user query into specialized intent."""
        q = query.lower()
        if any(w in q for w in ["purify", "purification", "treatment", "how to treat", "how to clean", "filter", "boil", "சுத்திகரி", "சிகிச்சை", "வடிகட்டு", "கொதிக்க", "தூய்மை"]):
            return "PURIFICATION"
        if any(w in q for w in ["grievance", "complaint", "petition", "draft letter", "report pollution", "complain to spcb"]):
            return "GRIEVANCE"
        if any(w in q for w in ["worst", "most polluted", "top polluted", "highest bod", "hotspot", "lowest oxygen", "cleanest", "safest"]):
            return "HOTSPOTS"
        if any(w in q for w in ["cpcb class", "bis 10500", "drinking standard", "bathing standard", "threshold", "criteria", "what is bod", "what is coliform", "meaning of"]):
            return "STANDARDS_EDUCATION"
        if any(w in q for w in ["state", "jharkhand", "himachal", "delhi", "punjab", "madhya pradesh", "rajasthan", "andhra", "odisha", "gujarat", "maharashtra"]) and any(w in q for w in ["average", "summary", "how many", "overview", "overall"]):
            return "STATE_SUMMARY"
        return "STATION_SAFETY"

    def answer_query(self, user_query: str) -> Dict[str, Any]:
        """Main agent entrypoint coordinating intent, tools, RAG context, and synthesis."""
        intent = self.classify_intent(user_query)
        evidence = {}
        rag_context = []

        # 1. Execute specialized tools based on intent
        if intent == "GRIEVANCE":
            stations = self.tool_find_station(user_query)
            if not stations:
                # Default to Agra Canal or high-BOD station if none specified
                stations = self.tool_get_pollution_hotspots("bod", limit=1)
            target = stations[0]
            letter = self.tool_draft_grievance_letter(target)
            evidence["target_station"] = target
            evidence["grievance_letter"] = letter
            rag_docs = self.tool_retrieve_standards("Water Act 1974 Section 24 SPCB remediation")
            rag_context.extend(rag_docs)

        elif intent == "HOTSPOTS":
            wtype = None
            for wt in ["RIVER", "DRAIN", "CANAL", "LAKE", "POND", "BEACH"]:
                if wt.lower() in user_query.lower():
                    wtype = wt
                    break
            metric = "coliform" if "coliform" in user_query.lower() else ("do" if "oxygen" in user_query.lower() else "bod")
            hotspots = self.tool_get_pollution_hotspots(metric=metric, water_body_type=wtype, limit=5)
            evidence["hotspots"] = hotspots
            evidence["metric"] = metric
            rag_docs = self.tool_retrieve_standards(f"Impact of extreme {metric} and organic pollution")
            rag_context.extend(rag_docs)

        elif intent == "STATE_SUMMARY":
            # Extract state name
            states = ['JHARKHAND', 'HIMACHAL PRADESH', 'UTTARAKHAND', 'MADHYA PRADESH', 'RAJASTHAN',
                      'ANDHRA PRADESH', 'GOA', 'DELHI', 'GUJARAT', 'ASSAM', 'PUNJAB', 'HARYANA',
                      'MAHARASHTRA', 'ODISHA', 'TAMIL NADU', 'TELANGANA', 'UTTAR PRADESH']
            found_state = None
            for s in states:
                if s.lower() in user_query.lower():
                    found_state = s
                    break
            state_to_query = found_state or "MADHYA PRADESH"
            stats = self.tool_get_state_statistics(state_to_query)
            evidence["state"] = state_to_query
            evidence["stats"] = stats
            rag_docs = self.tool_retrieve_standards("CPCB river stretch pollution classification")
            rag_context.extend(rag_docs)

        elif intent == "PURIFICATION":
            q_low = user_query.lower()
            is_tamil = any(w in q_low for w in ["tamil", "தமிழ்", "சுத்திகரி", "சிகிச்சை", "முறை", "எப்படி", "நீரை", "பாக்டீரியா", "நைட்ரேட்"])
            stations = self.tool_find_station(user_query)
            target = None
            common_words = {"water", "works", "river", "lake", "pond", "canal", "drain", "beach", "station", "sample", "near", "d/s", "u/s", "at", "the", "and"}
            if stations:
                loc_words = [t.lower() for t in stations[0].get('monitoring_location', '').replace('-', ' ').replace(',', ' ').split() if len(t) > 2 and t.lower() not in common_words]
                if any(t in q_low for t in loc_words):
                    target = stations[0]

            if not target:
                if any(kw in q_low for kw in ["nitrate", "coliform", "bacteria", "bod", "salinity", "salt", "acid", "நைட்ரேட்", "பாக்டீரியா", "கிருமி", "அமில", "உப்பு"]):
                    # Parameter-specific inquiry
                    target = {
                        "monitoring_location": "குடிநீர் மாதிரி (பயனர் வினவல்)" if is_tamil else "Water Sample (User Inquiry)",
                        "do_min": 2.0 if ("oxygen" in q_low or "do" in q_low) else 6.0,
                        "bod_max": 25.0 if ("bod" in q_low or "organic" in q_low or "sewage" in q_low) else 2.0,
                        "nitrate_max": 24.5 if ("nitrate" in q_low or "நைட்ரேட்" in q_low) else 1.0,
                        "total_coliform_max": 5000 if ("coliform" in q_low or "bacteria" in q_low or "pathogen" in q_low or "பாக்டீரியா" in q_low or "கிருமி" in q_low) else 50,
                        "conductivity_max": 2500 if ("salt" in q_low or "salin" in q_low or "tds" in q_low or "உப்பு" in q_low) else 350,
                        "ph_max": 5.2 if ("acid" in q_low or "அமில" in q_low) else (9.1 if "alkal" in q_low else 7.4)
                    }
                elif stations:
                    target = stations[0]
                else:
                    target = {
                        "monitoring_location": "குடிநீர் மாதிரி" if is_tamil else "General Drinking Water",
                        "do_min": 6.0,
                        "bod_max": 2.0,
                        "nitrate_max": 1.0,
                        "total_coliform_max": 100,
                        "conductivity_max": 300,
                        "ph_max": 7.4
                    }
            evidence["target_station"] = target
            rec = recommend_purification(target, lang="ta" if is_tamil else "en")
            evidence["purification_recipe"] = rec
            rag_docs = self.tool_retrieve_standards("water purification guidelines BIS 10500 chlorination RO UV boiling nitrate hazard")
            rag_context.extend(rag_docs)

        elif intent == "STANDARDS_EDUCATION":
            rag_docs = self.tool_retrieve_standards(user_query)
            rag_context.extend(rag_docs)

        else:  # STATION_SAFETY (default)
            stations = self.tool_find_station(user_query)
            evidence["matched_stations"] = stations
            if stations:
                top_stn = stations[0]
                rag_query = f"Water safety CPCB class {top_stn.get('cpcb_class')} BOD {top_stn.get('bod_max')} Coliform health risks"
            else:
                rag_query = user_query
            rag_docs = self.tool_retrieve_standards(rag_query)
            rag_context.extend(rag_docs)

        # 2. Synthesize response using LLM or Local Expert Engine
        if self.mode_override != "expert" and self.genai_client:
            answer = self._generate_with_gemini(user_query, intent, evidence, rag_context)
            mode = "Gemini LLM Agent"
        else:
            answer = self._generate_with_expert_engine(user_query, intent, evidence, rag_context)
            mode = "Local Deterministic Expert Agent"

        return {
            "query": user_query,
            "intent": intent,
            "mode": mode,
            "response": answer,
            "evidence": evidence,
            "retrieved_context": rag_context
        }

    # -------------------------------------------------------------
    # GENERATION BACKENDS
    # -------------------------------------------------------------

    def _generate_with_gemini(self, query: str, intent: str, evidence: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """Call Gemini model via google-genai client with focused, question-specific generation."""
        prompt = f"""
You are the AI Water Quality Monitoring, Public Awareness & Purification Recommender Assistant for India (NeerParvai / நீர் பார்வை).
Your objective is to answer the user's specific question directly, concisely, and accurately based on the factual data provided.

USER QUESTION: {query}
INTENT CATEGORY: {intent}

RETRIEVED DOMAIN STANDARDS & HEALTH GUIDANCE:
{json.dumps(context, indent=2)}

FACTUAL EVIDENCE & DATA RETRIEVED FROM DATABASE:
{json.dumps(evidence, indent=2)}

CRITICAL INSTRUCTIONS:
1. ANSWER ONLY THE SPECIFIC QUESTION ASKED:
   - Do NOT output an exhaustive multi-section template, unnecessary tables, or unprompted boilerplate.
   - If the user asks about bathing / holy dipping safety: Focus exclusively on outdoor bathing suitability, relevant parameters (BOD, Total Coliform, DO), and practical citizen safety precautions. Do NOT discuss drinking suitability, aquatic ecosystem, or municipal sewerage policy unless asked.
   - If the user asks about drinking water: Focus strictly on potable safety and BIS 10500 standards.
   - If the user asks for a specific parameter (e.g., "What is the BOD of Agra Canal?"): State the exact recorded values/range, compare them with CPCB/BIS limits, and explain what it means in 2-3 concise sentences.
   - If the user asks for hotspots or rankings: List only the requested ranked water bodies with the pertinent metric.
   - If the user asks for a grievance letter: Present the formal complaint letter with the specific station's exceedances.
   - If the user explicitly asks for an overall report or complete scorecard: Only then provide a comprehensive summary.
2. ACCURACY & EVIDENCE: Ground all numbers, stations, and standards strictly in the provided database evidence and CPCB rules. Never invent values.
3. CONCISE & READABLE: Format the answer with clean Markdown, clear badges (🟢 Safe, 🟡 Caution, 🔴 Unsafe), and bold highlights. Keep it focused and directly useful to the user.
4. LANGUAGE: If the user queries in Tamil (தமிழ்) or requests Tamil output, provide the response in clear, natural Tamil.
"""
        models_to_try = [self.model_name, "gemini-3.5-flash", "gemini-flash-latest"]
        for mod in models_to_try:
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.genai_client.models.generate_content,
                        model=mod,
                        contents=prompt
                    )
                    response = future.result(timeout=15.0)
                    if response and response.text:
                        return response.text
            except concurrent.futures.TimeoutError:
                print(f"Gemini {mod} request timed out after 15 seconds.")
            except Exception as e:
                print(f"Gemini {mod} call error: {e}. Trying next option...")
        
        print("Falling back to Deterministic Expert Engine.")
        return self._generate_with_expert_engine(query, intent, evidence, context)

    def _generate_with_expert_engine(self, query: str, intent: str, evidence: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """Deterministic local expert synthesis with domain logic."""
        if intent == "PURIFICATION":
            rec = evidence.get("purification_recipe", {})
            is_tamil = any(w in query.lower() for w in ["tamil", "தமிழ்", "சுத்திகரிப்பு"])
            return format_purification_markdown(rec, is_tamil=is_tamil)

        if intent == "GRIEVANCE":
            letter = evidence.get("grievance_letter", "")
            stn = evidence.get("target_station", {})
            return f"""### 📑 Formal Citizen Grievance Petition Generated

Based on monitored exceedances at **{stn.get('monitoring_location', 'Selected Water Body')}** (Station Code `{stn.get('stn_code')}`), here is the formal petition ready to be filed with the **{stn.get('state_name')} State Pollution Control Board**:

```text
{letter}
```

#### ⚖️ Legal & Procedural Guidance:
- **Statutory Authority**: Under Section 24 of the *Water (Prevention and Control of Pollution) Act, 1974*, direct discharge of polluting waste is unlawful.
- **Where to Submit**: File this petition via the SPCB grievance portal, submit a copy to the District Magistrate (Chairperson, District Environment Committee), and log it on the Central CPCB *Parivesh* / *Sameer* portal.
"""

        if intent == "HOTSPOTS":
            hotspots = evidence.get("hotspots", [])
            metric = evidence.get("metric", "bod")
            rows_md = ""
            for i, h in enumerate(hotspots, 1):
                val = h.get('bod_max') if metric == 'bod' else (h.get('total_coliform_max') if metric == 'coliform' else h.get('do_min'))
                unit = "mg/L" if metric in ['bod', 'do'] else "MPN/100ml"
                rows_md += f"| {i} | **{h.get('monitoring_location')}** | {h.get('state_name')} | {h.get('water_body_type')} | `{val} {unit}` | {h.get('cpcb_class')} | **{h.get('wqi_score')}** |\n"

            return f"""### 🚨 Water Pollution Hotspots Identified ({metric.upper()})

The assistant queried the monitoring database across 194 stations and identified the following critical locations:

| Rank | Location | State | Type | Peak {metric.upper()} | CPCB Class | WQI Score |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: |
{rows_md}

#### 🔬 Key Environmental Observations:
- **Severe Degradation**: Locations with BOD exceeding **10 mg/L** or Coliform reaching the tens of thousands represent raw sewage outfalls or un-intercepted industrial nallahs.
- **Public Danger**: These stretches are **Below Class E (Non-Compliant)**. Direct contact can cause severe gastrointestinal and dermatological infections.
- **Urgent Need**: Demands immediate sewage diversion and bio-remediation under NGT river rejuvenation mandates.
"""

        if intent == "STATE_SUMMARY":
            state = evidence.get("state", "Selected State")
            s = evidence.get("stats", {})
            return f"""### 📊 State Water Quality Profile: **{state}**

Summary of monitored surface waters in **{state}**:
- **Total Monitoring Stations**: `{s.get('total_stations', 0)}`
- **State Average Water Quality Index (WQI)**: **`{s.get('avg_wqi', 'N/A')}/100`**
- **Average Dissolved Oxygen**: `{s.get('avg_do', 'N/A')} mg/L` (Healthy standard $\ge 5.0$ mg/L)
- **Average BOD (Organic Load)**: `{s.get('avg_bod', 'N/A')} mg/L` (Standard $\le 3.0$ mg/L)
- **Worst-Case Peak BOD**: `{s.get('max_bod', 'N/A')} mg/L`
- **Lowest Dissolved Oxygen Recorded**: `{s.get('min_do', 'N/A')} mg/L`

#### 📋 CPCB Classification Breakdown:
- **Class A (Pristine / Drinking without treatment)**: `{s.get('class_a_count', 0)}` stations
- **Class B (Outdoor Bathing Safe)**: `{s.get('class_b_count', 0)}` stations
- **Class C (Conventional Treatment Required)**: `{s.get('class_c_count', 0)}` stations
- **Below Class E (Severely Polluted / Non-Compliant)**: `{s.get('non_compliant_count', 0)}` stations
"""

        if intent == "STANDARDS_EDUCATION":
            ctx_summary = "\n\n".join([f"**{c['title']}**\n{c['content']}" for c in context[:2]])
            return f"""### 📚 CPCB & BIS Water Quality Standards

Here is the regulatory criteria retrieved from official guidelines:

{ctx_summary}

#### 💡 Citizen Quick Takeaway:
1. **Raw Water Is Never Tap Potable**: Even Class A water requires mandatory disinfection before human drinking.
2. **Safe Bathing Threshold**: A water body is only safe for bathing if **BOD $\le 3$ mg/L**, **DO $\ge 5$ mg/L**, and **Total Coliform $\le 500$ MPN/100ml**.
3. **Danger Signals**: Water with a septic stench, blackish tint, or BOD $> 5$ mg/L indicates heavy raw sewage contamination.
"""

        # Default: STATION_SAFETY
        stns = evidence.get("matched_stations", [])
        if not stns:
            return f"""### ℹ️ Water Quality Inquiry
I searched the database for **"{query}"**, but could not find an exact matching station. 

**Tips for searching:**
- Try searching by river name (e.g., *Betwa, Jumar, Tons, Damodar, Giri, Chambal, Ajay*).
- Try searching by city/district (e.g., *Vidisha, Ranchi, Kakinada, Jaipur, Bokaro, Kota*).
- Try searching by station code (e.g., *2124, 4085, 134, 4357*).
- Or ask for **"pollution hotspots"** or **"state summary for Madhya Pradesh"**.
"""

        s = stns[0]
        status_emoji = "🟢" if s.get('wqi_score', 0) >= 70 else ("🟡" if s.get('wqi_score', 0) >= 50 else "🔴")
        q_lower = query.lower()

        # Specific Query 1: Bathing / Dipping / Swimming
        if any(w in q_lower for w in ["bath", "dip", "swim", "immersion"]):
            is_safe = "SAFE" in str(s.get('bathing_safety', '')).upper()
            status_tag = "🟢 SAFE" if is_safe else ("🟡 CAUTION" if "CAUTION" in str(s.get('bathing_safety', '')).upper() else "🔴 UNSAFE")
            return f"""### 🏊 Bathing & Dipping Assessment: **{s.get('monitoring_location')}**
- **Location**: {s.get('monitoring_location')} ({s.get('state_name')}) | Station Code: `{s.get('stn_code')}`
- **Bathing Verdict**: **{status_tag}** — {s.get('bathing_safety')}
- **Relevant Monitored Parameters**:
  - **Biochemical Oxygen Demand (BOD)**: `{s.get('bod_min')} - {s.get('bod_max')} mg/L` *(CPCB Bathing Limit: $\le 3.0$ mg/L)*
  - **Total Coliform**: `{s.get('total_coliform_min')} - {s.get('total_coliform_max')} MPN/100ml` *(CPCB Bathing Limit: $\le 500$ MPN/100ml)*
  - **Dissolved Oxygen (DO)**: `{s.get('do_min')} - {s.get('do_max')} mg/L` *(CPCB Bathing Limit: $\ge 5.0$ mg/L)*
- **Advisory for Citizens**: {'Avoid ritual dipping or facial immersion due to elevated organic waste and bacterial count.' if not is_safe else 'Water meets CPCB outdoor bathing criteria. Maintain basic hygiene.'}
"""

        # Specific Query 2: Drinking / Potable
        if any(w in q_lower for w in ["drink", "potable", "consumption"]):
            return f"""### 🚰 Drinking Suitability: **{s.get('monitoring_location')}**
- **Location**: {s.get('monitoring_location')} ({s.get('state_name')}) | Station Code: `{s.get('stn_code')}`
- **Drinking Verdict**: **{s.get('drinking_suitability')}**
- **CPCB Source Classification**: **{s.get('cpcb_class')}**
- **BIS 10500 Potable Standard**: Raw surface water is not directly drinkable. It requires conventional treatment and disinfection to ensure zero coliform before municipal supply.
"""

        # Specific Query 3: Specific Parameter (BOD)
        if "bod" in q_lower:
            bod_exceeds = (s.get('bod_max', 0) or 0) > 3.0
            return f"""### 🧪 Biochemical Oxygen Demand (BOD): **{s.get('monitoring_location')}**
- **Recorded Range**: **`{s.get('bod_min')} to {s.get('bod_max')} mg/L`** (Mean: `{s.get('bod_mean')} mg/L`)
- **CPCB Thresholds**: Bathing limit $\le 3.0$ mg/L | Drinking source limit $\le 2.0$ mg/L
- **Status**: {'🔴 Exceeds permissible limits due to organic and sewage pollution.' if bod_exceeds else '🟢 Within acceptable baseline limits.'}
"""

        # Specific Query 4: Specific Parameter (Dissolved Oxygen)
        if any(w in q_lower for w in ["oxygen", " do "]):
            do_low = (s.get('do_min', 0) or 0) < 5.0
            return f"""### 🧪 Dissolved Oxygen (DO): **{s.get('monitoring_location')}**
- **Recorded Range**: **`{s.get('do_min')} to {s.get('do_max')} mg/L`** (Mean: `{s.get('do_mean')} mg/L`)
- **CPCB Threshold**: Bathing requirement $\ge 5.0$ mg/L | Aquatic life floor $\ge 4.0$ mg/L
- **Status**: {'🔴 Oxygen depletion observed at low water levels.' if do_low else '🟢 Sufficient oxygenation for aquatic fauna.'}
"""

        # Specific Query 5: Specific Parameter (Coliform / Bacteria)
        if any(w in q_lower for w in ["coliform", "bacteria", "fecal"]):
            col_high = (s.get('total_coliform_max', 0) or 0) > 500
            return f"""### 🧪 Bacterial Coliform Levels: **{s.get('monitoring_location')}**
- **Total Coliform Range**: **`{s.get('total_coliform_min')} to {s.get('total_coliform_max')} MPN/100ml`**
- **Fecal Coliform Range**: **`{s.get('fecal_coliform_min')} to {s.get('fecal_coliform_max')} MPN/100ml`**
- **CPCB Threshold**: Outdoor bathing limit $\le 500$ MPN/100ml | Drinking source $\le 50$ MPN/100ml
- **Status**: {'🔴 Severe microbial contamination; risk of waterborne gastroenteritis.' if col_high else '🟢 Within safe microbial parameters.'}
"""

        # Default: Full Scorecard for general queries
        return f"""### 🌊 Water Quality Assessment: **{s.get('monitoring_location')}**
- **Station Code**: `{s.get('stn_code')}` | **State**: {s.get('state_name')} | **Water Body**: {s.get('water_body_type')}
- **Water Quality Index (WQI)**: {status_emoji} **`{s.get('wqi_score')}/100` ({s.get('wqi_status')})**
- **CPCB Designated Best Use Class**: **{s.get('cpcb_class')}**

---

### 🛡️ Public Safety & Citizen Health Verdict
| Activity | Verdict | Explanation |
| :--- | :--- | :--- |
| **Outdoor Bathing / Dipping** | **{s.get('bathing_safety')}** | Monitored Coliform is `{s.get('total_coliform_min')}-{s.get('total_coliform_max')} MPN/100ml` and BOD is `{s.get('bod_min')}-{s.get('bod_max')} mg/L`. |
| **Drinking Water Suitability** | **{s.get('drinking_suitability')}** | Direct consumption from raw source is strictly unsafe under BIS 10500 standards. |
| **Aquatic Fauna Viability** | **{s.get('aquatic_health')}** | Dissolved oxygen fluctuates between `{s.get('do_min')} to {s.get('do_max')} mg/L`. |

---

### 🧪 Key Monitored Parameters vs Standards
- **Dissolved Oxygen (DO)**: `{s.get('do_min')} - {s.get('do_max')} mg/L` *(CPCB Bathing Norm: $\ge 5.0$ mg/L)*
- **Biochemical Oxygen Demand (BOD)**: `{s.get('bod_min')} - {s.get('bod_max')} mg/L` *(CPCB Bathing Norm: $\le 3.0$ mg/L)*
- **pH**: `{s.get('ph_min')} - {s.get('ph_max')}` *(Acceptable Range: 6.5 - 8.5)*
- **Total Coliform**: `{s.get('total_coliform_min')} - {s.get('total_coliform_max')} MPN/100ml` *(Bathing Desirable: $\le 500$ MPN/100ml)*
- **Primary Environmental Concern**: `{s.get('primary_concerns')}`

---

### 📢 Recommended Actions for Citizens & Authorities
1. **For Citizens**: {'Avoid direct immersion, facial contact, or swallowing water.' if 'UNSAFE' in str(s.get('bathing_safety')) else 'Water is suitable for bathing, but observe standard hygiene and avoid drinking raw water.'}
2. **For Municipal Authorities**: {'Intercept upstream domestic drains and monitor sewage treatment plant (STP) effluent outfalls.' if s.get('wqi_score', 100) < 70 else 'Maintain watershed conservation and prevent solid waste dumping along banks.'}
"""


if __name__ == "__main__":
    agent = WaterQualityAgent()
    print("\n--- Testing Agent on River Betwa Query ---")
    res = agent.answer_query("Is River Betwa at Charantirghat safe for bathing?")
    print(res["response"])

    print("\n--- Testing Hotspots Query ---")
    res2 = agent.answer_query("Show top 3 polluted water bodies with highest BOD")
    print(res2["response"])
