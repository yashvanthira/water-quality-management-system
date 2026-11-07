# NeerParvai (நீர் பார்வை) 💧
### AI Agent-Based Intelligent Water Quality Monitoring, Public Awareness & Purification Recommender Assistant Using RAG

**NeerParvai (நீர் பார்வை)** is an intelligent environmental monitoring, citizen advisory, and smart purification recommendation assistant built on top of official Indian water quality monitoring data from the **Central Pollution Control Board (CPCB)**. It combines **Retrieval-Augmented Generation (RAG)**, a **Multi-Agent Orchestrator**, deterministic environmental calculations (WQI, CPCB Classifications), and bilingual (English / தமிழ்) public health and purification protocols.

---

## 🌟 Key Features

1. **Dual-Retrieval RAG Engine**:
   - **Structured Query Engine (SQLite)**: Sub-second analytical queries across 194 continuous monitoring stations across 17 States and 11 water body types (Rivers, Canals, Drains, Lakes, Ponds, Beaches, Marine outfalls, STPs).
   - **Semantic Vector Engine (TF-IDF + Cosine Ranking)**: Semantic search over official regulatory guidelines, including CPCB Designated Best Use standards, Bureau of Indian Standards (BIS 10500:2012) potable water limits, waterborne pathogen risks, and remediation policies.

2. **Environmental & Public Health Intelligence**:
   - **CPCB Designated Best Use Classification**: Automatically categorizes water into Class A, B, C, D, E, or Non-Compliant / Below Class E.
   - **Water Quality Index (WQI)**: Weighted arithmetic scoring (0 to 100) assessing DO, BOD, pH, Electrical Conductivity, Nitrates, and Coliform organisms.
   - **Citizen Safety Verdicts**: Translates complex chemical readings into clear advice:
     - 🟢 *Safe for organized outdoor bathing*
     - 🟡 *Caution: moderate microbial load*
     - 🔴 *Hazardous: severe raw sewage / industrial contamination*

3. **Multi-Agent Workflow**:
   - **Intent Router**: Automatically classifies user queries into *Station Safety*, *Pollution Hotspots*, *State Overview*, *Standards Education*, or *Grievance Petitioning*.
   - **Data Analyst Agent**: Executes SQL queries, aggregates state metrics, and detects extreme exceedances.
   - **Public Health & Awareness Agent**: Generates plain-language advisories tailored to citizens, pilgrims, farmers, and local communities.
   - **Grievance Drafting Agent**: Automatically generates formal legal petition letters citing the *Water (Prevention and Control of Pollution) Act, 1974* for filing with State Pollution Control Boards (SPCBs).

4. **Dual Execution Mode**:
   - **Local Expert Engine**: Works 100% offline out-of-the-box with zero API keys or external dependencies.
   - **LLM Agent Mode**: Seamlessly switches to Google Gemini (`gemini-3.5-flash-lite` via `google-genai`) using credentials from `.env` for low-latency, high-accuracy RAG synthesis.

5. **Citizen Science & Manual Data Ingestion**:
   - Allows users, field volunteers, and local laboratories to manually input custom water quality readings (DO, BOD, pH, Coliforms, Conductivity, etc.).
   - Instantly computes WQI and CPCB Best Use classifications on the fly.
   - Automatically saves and dynamically indexes the new sample into SQLite and the RAG semantic memory so the AI assistant can immediately answer inquiries about the newly added location.

6. **Smart Water Purification & Treatment Recommender (English & தமிழ்)**:
   - Diagnoses chemical and microbiological contaminants (Turbidity, Total/Fecal Coliform, High BOD, Excess Nitrates, High Salinity/Conductivity, Acidity/Alkalinity).
   - Generates multi-stage household protocols (Sedimentation/Coagulation, Disinfection via Boiling/UV/Chlorination, Activated Carbon Adsorption, RO Demineralization).
   - Provides community-scale multi-barrier treatment recommendations (Rapid Sand Filtration, Pressure Sand Filter, Industrial Dual-Bed Ion Exchange, Activated Sludge/MBBR).
   - Features **Critical Health Warnings**, including strict contraindication against boiling high-nitrate water for infants (preventing Methemoglobinemia / "Blue Baby Syndrome").
   - Full bilingual support in English and Tamil (தமிழ்).

---

## 📁 Repository Structure

```
c:\project folder\RAG Indian Water Prototype\
├── Indian_water_data.csv        # Raw dataset (194 stations, 17 states, 2021-2023)
├── clean_water_data.csv         # Cleaned & enriched dataset with WQI & CPCB tags
├── water_quality.db             # Indexed SQLite database for fast analytical queries
├── data_processor.py            # Preprocessing pipeline, BDL handler, WQI calculator
├── rag_engine.py                # Hybrid RAG retrieval engine (Semantic + Relational)
├── water_agent.py               # Multi-agent orchestrator & advisory synthesis
├── purification_recommender.py  # Smart Water Purification & Treatment Recommender (En & Ta)
├── app.py                       # Streamlit web dashboard & chat assistant
├── test_prototype.py            # End-to-end automated verification test suite
└── knowledge_base/              # Regulatory & health markdown documents
    ├── cpcb_water_standards.md  # CPCB Designated Best Use Classes A-E
    ├── bis_10500_standards.md   # BIS 10500 potable water benchmarks
    ├── health_risk_guidelines.md# Health risks of coliform, nitrates, and low DO
    ├── remediation_policy.md    # Statutory acts & remediation guidelines
    └── water_purification_guide.md # Multi-barrier purification protocols & warnings
```

---

## 🚀 Getting Started

### 1. Run Automated Test Suite
Verify that all data pipelines, RAG indexing, database queries, and agents are functioning correctly:
```powershell
python test_prototype.py
```

### 2. Launch the Interactive Web Dashboard
Run the Streamlit web application:
```powershell
streamlit run app.py
```
This opens the web interface in your default browser at `http://localhost:8501`.

---

## 💡 Example Queries You Can Ask the Assistant

- **Station Safety**:
  - *"Is River Betwa at Charantirghat safe for holy dipping?"*
  - *"Check water quality at Rushikonda Beach, Visakhapatnam."*
- **Pollution Hotspots**:
  - *"Show the top 5 most polluted water bodies with the highest BOD."*
  - *"Which drains in Delhi or Punjab have critical bacterial levels?"*
- **State Overviews**:
  - *"Give a state summary and CPCB class distribution for Jharkhand."*
- **Citizen Action & Legal Grievance**:
  - *"Draft a formal SPCB grievance petition for Agra Canal under the Water Act 1974."*
- **Public Health & Education**:
  - *"Explain what Biochemical Oxygen Demand (BOD) means and why high coliform count is dangerous."*

