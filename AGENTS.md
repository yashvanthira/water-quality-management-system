# AGENTS.md — Development History, Architecture & Conversation Log
### NeerParvai (நீர் பார்வை) 💧: AI Agent-Based Water Quality Monitoring, Public Awareness & Smart Purification Assistant

---

## 📌 1. Project Overview & Objective

**NeerParvai (நீர் பார்வை)** is an AI Agent-based environmental monitoring, citizen awareness, and smart water purification recommendation platform powered by **Hybrid Retrieval-Augmented Generation (RAG)**. 

### Core Objectives:
1. **Public Health & Environmental Awareness**: Democratize official water quality monitoring data from the **Central Pollution Control Board (CPCB)** across 194 continuous stations in 17 Indian States and Union Territories.
2. **Deterministic Safety Evaluation**: Automatically calculate the **Water Quality Index (WQI)** and classify water bodies into official **CPCB Designated Best Use Classes (A–E)** and citizen safety verdicts (Safe, Caution, Unsafe).
3. **Citizen Science & Field Sample Ingestion**: Allow citizens, field volunteers, and local laboratories to manually input custom water quality parameters with immediate on-the-fly index calculation and dynamic RAG memory indexing.
4. **Smart Water Purification Protocols (English & தமிழ்)**: Diagnose chemical and microbial contamination and provide contaminant-specific multi-barrier household and community purification recipes with critical warnings (e.g., against boiling high-nitrate water for infants).
5. **Statutory Accountability**: Automatically draft formal citizen grievance petition letters under Section 24 of the *Water (Prevention and Control of Pollution) Act, 1974* to submit to State Pollution Control Boards (SPCBs).

---

## 💬 2. Chronological Conversation & Evolution Log

This section chronicles all iterations, user directives, technical challenges, and resolutions throughout the project:

### User Request 1: LLM Integration via `.env`
- **Request**: Uploaded `.env` containing `GEMINI_API_KEY` for LLM responses based on user queries.
- **Action Taken**: Configured automatic discovery of `GEMINI_API_KEY` via `python-dotenv`. Added fallback to Local Expert Agent (100% offline rule-based) if key is missing or network times out.

### User Request 2: Model Selection — Gemini 3.5 Flash Lite
- **Request**: Use `Gemini 3.5 Flash Lite` model.
- **Action Taken**: Configured `gemini-3.5-flash-lite` as the primary LLM model via `google-genai` SDK. Added 15-second ThreadPoolExecutor timeouts and graceful fallback to ensure the agent never hangs.

### User Request 3: Codebase Cleanliness
- **Request**: Remove unwanted files and unused functions.
- **Action Taken**: Cleaned up obsolete mock scripts, dead imports, and redundant test files. Consolidated testing into a unified end-to-end test suite (`test_prototype.py`).

### User Request 4: Focused & Direct Prompting
- **Request**: Change prompt so the agent answers only the specific question asked without dumping unrequested boilerplate.
- **Action Taken**: Updated system prompts in `water_agent.py` to enforce strict question-specific outputs:
  - If asked about bathing: Focus solely on outdoor bathing safety and coliform/BOD.
  - If asked about drinking: Focus strictly on potable safety and BIS 10500 limits.
  - If asked for a specific parameter: State the exact measured values and explain what it means in 2–3 concise sentences.

### User Request 5: Project Objective Clarification
- **Request**: What is the objective of this project?
- **Action Taken**: Documented the multifaceted mission: bridging the gap between complex chemical monitoring data and citizen safety, aiding environmental regulators, and empowering rural/urban communities with actionable health advice.

### User Request 6: Real-Time Data Exploration
- **Request**: Can we add real-time data in this project?
- **Action Taken**: Designed the real-time data integration roadmap, incorporating CPCB RTWQMS (Real-Time Water Quality Monitoring Stations) API webhooks, IoT sensor nodes (ESP32/Arduino with DO/pH/TDS probes), and MQTT/REST ingestion pipelines.

### User Request 7: Manual Data Ingestion Method
- **Request**: Add manual data method from the users.
- **Action Taken**:
  - Implemented `add_manual_sample()` in `data_processor.py`.
  - Added the **"➕ Submit Water Sample"** tab in `app.py` with presets (Sewage river, Agricultural runoff, High salinity groundwater, Clean mountain spring).
  - Added instant WQI calculation, CPCB classification, database insertion into SQLite, and live dynamic re-indexing into the RAG semantic memory.

### User Request 8: Bug Fix — `reload_agent` AttributeError
- **Request**: `AttributeError: 'WaterQualityAgent' object has no attribute 'reload_agent'` in `app.py`.
- **Root Cause**: Streamlit's `@st.cache_resource` held the prior in-memory agent instance from before the method was defined.
- **Action Taken**: Added `st.cache_resource.clear()` and `st.cache_data.clear()` before reload, and implemented defensive inspection (`hasattr(agent, "reload_agent")`).

### User Request 9: Feature Ideation
- **Request**: Any features can we add?
- **Action Taken**: Proposed high-value enhancements: Smart Water Purification Recommender, Seasonal Pollution Forecasting, and Regional Language Localization.

### User Request 10: Smart Water Purification & Tamil Localization
- **Request**: Add Smart Water Purification & Treatment Recommender and remove Hindi words, replacing them with Tamil words.
- **Action Taken**:
  - Replaced all Hindi branding (`JalDrishti / जल दृष्टि`) with **`NeerParvai (நீர் பார்வை)`** and greetings (`Namaste! 🙏`) with **`Vanakkam! (வணக்கம்) 🙏`**.
  - Built `purification_recommender.py` and `knowledge_base/water_purification_guide.md` supporting English and Tamil (தமிழ்).
  - Added `PURIFICATION` intent to `water_agent.py`.
  - Added dedicated `"🔬 Purification Recommender / நீர் சுத்திகரிப்பு"` tab to `app.py` along with language toggle and cards in Deep-Dive and Sample Submission tabs.
  - Verified 100% pass across all 7 test suite stages.

---

## 🤖 3. Agent Architecture & Sub-Specializations

```
+---------------------------------------------------------------------------------+
|                       Citizen / User Natural Language Query                     |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                   Intent Router (water_agent.py - classify_intent)               |
+---------------------------------------------------------------------------------+
       |               |               |              |             |            |
       v               v               v              v             v            v
 [STATION_SAFETY]  [HOTSPOTS]  [STATE_SUMMARY]  [STANDARDS]   [GRIEVANCE]  [PURIFICATION]
       |               |               |              |             |            |
+--------------------------------------+--------------+--------------------------+
|                     Hybrid Retrieval-Augmented Generation Engine                |
|  * SQLite Analytical Query Engine (Indexed 194 Stations across 17 States)      |
|  * TF-IDF & Cosine Vector Semantic Search (219 Domain Knowledge Chunks)        |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|                   Synthesis Backend (Dual-Execution Strategy)                   |
|  * Mode A: Google Gemini 3.5 Flash Lite via google-genai SDK (Low Latency)     |
|  * Mode B: Deterministic Local Expert Rule Engine (100% Offline Resilience)     |
+---------------------------------------------------------------------------------+
                                         |
                                         v
+---------------------------------------------------------------------------------+
|             Actionable Bilingual Output (English / தமிழ் - NeerParvai)           |
+---------------------------------------------------------------------------------+
```

### Agent Roles:
1. **Intent Router**: Directs incoming inquiries to the appropriate retrieval and tool pipeline.
2. **Data Analyst Agent**: Queries SQLite database (`water_quality.db`) for min/max/mean metrics, rankings, and state aggregations.
3. **Public Health & Safety Agent**: Cross-references water chemistry against BIS 10500:2012 potable limits and CPCB Best Use Criteria.
4. **Smart Purification Recommender Agent**: Generates tailored multi-stage purification steps (Household & Community scale) with critical health warnings.
5. **Grievance Drafting Agent**: Generates formal legal notice documents citing the *Water Act, 1974* for submission to SPCBs.

---

## 🧪 4. Standards, Parameters & Environmental Rules

### CPCB Designated Best Use Classes:
- **Class A**: Drinking water source without conventional treatment but after disinfection ($DO \ge 6\text{ mg/L}$, $BOD \le 2\text{ mg/L}$, $Coliform \le 50\text{ MPN/100ml}$).
- **Class B**: Outdoor bathing (organized) ($DO \ge 5\text{ mg/L}$, $BOD \le 3\text{ mg/L}$, $Coliform \le 500\text{ MPN/100ml}$).
- **Class C**: Drinking water source after conventional treatment and disinfection ($DO \ge 4\text{ mg/L}$, $BOD \le 3\text{ mg/L}$, $Coliform \le 5000\text{ MPN/100ml}$).
- **Class D**: Propagation of Wildlife and Fisheries ($DO \ge 4\text{ mg/L}$, $pH\text{ 6.5–8.5}$).
- **Class E**: Irrigation, Industrial cooling ($EC \le 2250\text{ }\mu\text{mho/cm}$).
- **Below Class E**: Severely Polluted / Non-Compliant.

### Critical Purification Rules & Health Warnings:
1. **Nitrate Infant Hazard**:
   - Limit: $\text{NO}_3\text{-N} \le 10\text{ mg/L}$ ($\text{NO}_3 \le 45\text{ mg/L}$).
   - **Crucial Warning**: NEVER boil water containing high nitrates for infants or pregnant women. Boiling evaporates water and concentrates nitrate ions, causing infant Methemoglobinemia ("Blue Baby Syndrome"). Requires **Reverse Osmosis (RO)** or **Strong Base Anion (SBA) ion-exchange resins**.
2. **Microbial Pathogens**:
   - Total Coliform $> 500\text{ MPN/100ml}$ requires rolling boil for $\ge 1-3$ minutes, germicidal UV irradiation (254 nm), or point-of-use chlorination ($0.2-0.5\text{ mg/L}$ residual).
3. **High Organic Load (BOD)**:
   - $BOD > 3\text{ mg/L}$ requires Granular Activated Carbon (GAC) filtration to adsorb dissolved organics and pesticides.

---

## 📁 5. Repository File Map

```
c:\project folder\RAG Indian Water Prototype\
├── AGENTS.md                    # Conversation log, agent architecture & history (this file)
├── README.md                    # Project overview, installation & feature documentation
├── .env                         # API credentials (GEMINI_API_KEY)
├── Indian_water_data.csv        # Raw dataset (194 stations, 17 states, 2021-2023)
├── clean_water_data.csv         # Cleaned dataset with WQI & CPCB classifications
├── water_quality.db             # Indexed SQLite database for fast analytical queries
├── data_processor.py            # Preprocessing, WQI calculator, BDL handler, manual ingestion
├── rag_engine.py                # Hybrid RAG engine (TF-IDF vector search + SQLite SQL tool)
├── water_agent.py               # Multi-agent orchestrator (Dual Mode: Gemini 3.5 / Local Expert)
├── purification_recommender.py  # Smart Water Purification Recommender (English & Tamil)
├── app.py                       # Streamlit web application & bilingual dashboard
├── test_prototype.py            # Automated 7-stage verification test suite
└── knowledge_base/              # Domain markdown documentation (219 knowledge chunks)
    ├── cpcb_water_standards.md  # Official CPCB Class A-E criteria
    ├── bis_10500_standards.md   # BIS 10500:2012 potable water benchmarks
    ├── health_risk_guidelines.md# Health risks of coliform, low DO, and nitrates
    ├── remediation_policy.md    # Statutory acts and NGT rejuvenation directives
    └── water_purification_guide.md # Multi-barrier purification recipes and warnings
```

---

## ✅ 6. Test Suite Verification Status

All 7 test stages in [`test_prototype.py`](file:///c:/project%20folder/RAG%20Indian%20Water%20Prototype/test_prototype.py) pass cleanly:

```text
==================================================
STARTING TEST SUITE: INDIAN WATER QUALITY RAG AGENT
==================================================
[1/5] Testing Data Processing Integrity...
  -> PASS: 194 records validated with WQI and CPCB classifications.
[2/5] Testing SQLite Database & Indexing...
  -> PASS: SQLite loaded successfully with 15 Class A stations.
[3/5] Testing Hybrid RAG Engine...
  -> PASS: Retrieved top chunk: 'health_risk_guidelines.md' (Score: 0.3987)
[4/5] Testing Multi-Agent Query Routing & Tools...
  -> PASS: All agent query intents and tool executions passed.
[5/6] Testing Citizen Grievance Petition Generator...
  -> PASS: Formal legal grievance letter generated successfully.
[6/6] Testing Manual User Data Submission & Ingestion Pipeline...
  -> PASS: Manual sample ingested as Station 90006 and verified by agent.
[7/7] Testing Smart Water Purification Recommender (English & தமிழ்)...
  -> PASS: Smart Water Purification Recommender passed all English and Tamil tests.
==================================================
ALL TESTS PASSED SUCCESSFULLY! Prototype is verified.
==================================================
```

---
*Created and maintained for NeerParvai (நீர் பார்வை) AI Water Quality Monitoring & Awareness Prototype.*

