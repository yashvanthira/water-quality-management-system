"""
Automated Test Suite for Indian Water Quality Monitoring RAG & AI Agent.
Validates:
1. Data cleaning and enrichment integrity
2. SQLite database indices and queries
3. Semantic retrieval from knowledge base
4. Multi-agent intent routing and tool execution
5. Plain-language safety verdict accuracy
"""

import os
import sqlite3
import pandas as pd
from rag_engine import HybridRAGEngine
from water_agent import WaterQualityAgent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLEAN_CSV = os.path.join(BASE_DIR, "clean_water_data.csv")
DB_PATH = os.path.join(BASE_DIR, "water_quality.db")


def test_data_integrity():
    print("[1/5] Testing Data Processing Integrity...")
    assert os.path.exists(CLEAN_CSV), "clean_water_data.csv does not exist"
    assert os.path.exists(DB_PATH), "water_quality.db does not exist"

    df = pd.read_csv(CLEAN_CSV)
    assert len(df) >= 194, f"Expected at least 194 records, found {len(df)}"

    required_cols = [
        'stn_code', 'monitoring_location', 'state_name', 'water_body_type',
        'wqi_score', 'wqi_status', 'cpcb_class', 'bathing_safety', 'drinking_suitability'
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"

    # Verify WQI scores are bounded 0-100
    valid_wqi = df['wqi_score'].dropna()
    assert (valid_wqi >= 0).all() and (valid_wqi <= 100).all(), "WQI score out of 0-100 bounds"

    print("  -> PASS: 194 records validated with WQI and CPCB classifications.")


def test_sqlite_database():
    print("[2/5] Testing SQLite Database & Indexing...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM water_monitoring")
    count = cursor.fetchone()[0]
    assert count >= 194, f"Expected at least 194 rows in SQLite, found {count}"

    # Test indexing and search
    cursor.execute("SELECT stn_code, monitoring_location, cpcb_class FROM water_monitoring WHERE cpcb_class LIKE 'Class A%'")
    class_a = cursor.fetchall()
    assert len(class_a) > 0, "No Class A stations found"

    conn.close()
    print(f"  -> PASS: SQLite loaded successfully with {len(class_a)} Class A stations.")


def test_rag_semantic_search():
    print("[3/5] Testing Hybrid RAG Engine...")
    rag = HybridRAGEngine()
    assert len(rag.chunks) >= 200, f"Expected at least 200 chunks, found {len(rag.chunks)}"

    results = rag.semantic_search("What are the health risks of high fecal coliform in bathing water?", top_k=2)
    assert len(results) > 0, "Semantic search returned empty results"
    assert "health" in results[0]["category"] or "regulatory" in results[0]["category"], "Irrelevant chunk category retrieved"

    print(f"  -> PASS: Retrieved top chunk: '{results[0]['title']}' (Score: {results[0]['similarity_score']})")


def test_agent_intent_and_queries():
    print("[4/5] Testing Multi-Agent Query Routing & Tools...")
    agent = WaterQualityAgent(mode_override="expert")

    # Query 1: Station safety check
    res1 = agent.answer_query("Is River Betwa at Charantirghat safe for holy dipping?")
    assert res1["intent"] == "STATION_SAFETY"
    assert "BETWA" in res1["response"].upper()
    assert "UNSAFE" in res1["response"] or "CAUTION" in res1["response"]

    # Query 2: Marine / Coastal station
    res2 = agent.answer_query("Rushikonda Beach Visakhapatnam water quality")
    assert "RUSHIKONDA" in res2["response"].upper()

    # Query 3: Hotspots query
    res3 = agent.answer_query("Show top 5 water pollution hotspots with highest BOD")
    assert res3["intent"] == "HOTSPOTS"
    assert "BHATIAN NALLAH" in res3["response"] or "AGRA CANAL" in res3["response"]

    # Query 4: State summary
    res4 = agent.answer_query("Give state summary for Jharkhand water quality")
    assert res4["intent"] == "STATE_SUMMARY"
    assert "JHARKHAND" in res4["response"].upper()

    print("  -> PASS: All agent query intents and tool executions passed.")


def test_grievance_generator():
    print("[5/6] Testing Citizen Grievance Petition Generator...")
    agent = WaterQualityAgent(mode_override="expert")
    res = agent.answer_query("Draft a formal grievance petition for Agra Canal")
    assert res["intent"] == "GRIEVANCE"
    assert "WATER (PREVENTION AND CONTROL OF POLLUTION) ACT, 1974" in res["response"].upper()
    assert "AGRA CANAL" in res["response"].upper()

    print("  -> PASS: Formal legal grievance letter generated successfully.")


def test_manual_data_submission():
    print("[6/6] Testing Manual User Data Submission & Ingestion Pipeline...")
    from data_processor import add_manual_sample

    sample = add_manual_sample(
        monitoring_location="COMMUNITY RIVER GHAT AT PRAYAGRAJ",
        state_name="UTTAR PRADESH",
        water_body_type="RIVER",
        do=7.0,
        bod=2.1,
        ph=7.5,
        conductivity=320,
        nitrate=0.9,
        total_coliform=380,
        fecal_coliform=120,
        year=2026
    )
    assert sample["stn_code"] >= 90000, "Expected manual station code >= 90000"
    assert sample["wqi_score"] > 80, "Expected high WQI score for clean sample"
    assert "Class B" in sample["cpcb_class"] or "Class A" in sample["cpcb_class"]

    # Verify agent retrieves newly added manual station
    agent = WaterQualityAgent(mode_override="expert")
    agent.reload_agent()
    ans = agent.answer_query("Is Community River Ghat at Prayagraj safe for bathing?")
    assert "PRAYAGRAJ" in ans["response"].upper()
    assert "SAFE" in ans["response"].upper()

    print(f"  -> PASS: Manual sample ingested as Station {sample['stn_code']} and verified by agent.")


def test_purification_recommender():
    print("[7/7] Testing Smart Water Purification Recommender (English & தமிழ்)...")
    from purification_recommender import recommend_purification, format_purification_markdown

    # Case 1: High Nitrate Water (Must warn against boiling for infants)
    sample_nitrate = {
        "monitoring_location": "Borewell Sample with Agricultural Runoff",
        "nitrate_max": 22.0,
        "total_coliform_max": 200,
        "bod_max": 1.5,
        "ph_mean": 7.2,
        "conductivity_max": 650
    }
    rec_en = recommend_purification(sample_nitrate, lang="en")
    assert rec_en["boiling_safe"] is False, "Expected boiling_safe to be False for high nitrate"
    assert any("INFANT" in w.upper() or "BLUE BABY" in w.upper() for w in rec_en["critical_warnings"]), "Missing nitrate infant warning"
    assert any("RO" in s["instruction"] or "REVERSE OSMOSIS" in s["instruction"].upper() for s in rec_en["household_recipe"]), "RO missing from recipe"

    # Case 2: Tamil Generation
    rec_ta = recommend_purification(sample_nitrate, lang="ta")
    assert any("குழந்தை" in w for w in rec_ta["critical_warnings"]), "Missing Tamil infant nitrate warning"
    assert any("RO" in s["instruction"] or "சவ்வூடுபரவல்" in s["instruction"] for s in rec_ta["household_recipe"]), "Missing Tamil RO instruction"

    # Case 3: Markdown Formatting
    md_en = format_purification_markdown(rec_en, is_tamil=False)
    assert "Smart Water Purification Protocol" in md_en
    md_ta = format_purification_markdown(rec_ta, is_tamil=True)
    assert "ஸ்மார்ட் நீர் சுத்திகரிப்பு வழிகாட்டி" in md_ta

    # Case 4: Agent Agentic Routing for English & Tamil Purification Queries
    agent = WaterQualityAgent(mode_override="expert")
    q1 = agent.answer_query("How to purify water with high nitrate concentration?")
    assert q1["intent"] == "PURIFICATION"
    assert "BLUE BABY" in q1["response"].upper() or "METHEMOGLOBINEMIA" in q1["response"].upper()

    q2 = agent.answer_query("அதிக பாக்டீரியா உள்ள நீரை சுத்திகரிப்பது எப்படி?")
    assert q2["intent"] == "PURIFICATION"
    assert "சுத்திகரிப்பு" in q2["response"] or "கிருமி" in q2["response"]

    print("  -> PASS: Smart Water Purification Recommender passed all English and Tamil tests.")


if __name__ == "__main__":
    print("\n==================================================")
    print("STARTING TEST SUITE: INDIAN WATER QUALITY RAG AGENT")
    print("==================================================")
    test_data_integrity()
    test_sqlite_database()
    test_rag_semantic_search()
    test_agent_intent_and_queries()
    test_grievance_generator()
    test_manual_data_submission()
    test_purification_recommender()
    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY! Prototype is verified.")
    print("==================================================\n")

