"""
Hybrid RAG Engine for Indian Water Quality Monitoring.
Combines:
1. Semantic Search across CPCB standards, BIS 10500 potable limits, health hazard guidelines, and remediation policies.
2. Structured SQL / Relational Query Engine for precise parameter lookups, threshold filtering, and spatial aggregations.
"""

import os
import glob
import sqlite3
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
DB_PATH = os.path.join(BASE_DIR, "water_quality.db")


class DocumentChunk:
    def __init__(self, doc_id, title, content, source_file, category="standard"):
        self.doc_id = doc_id
        self.title = title
        self.content = content
        self.source_file = source_file
        self.category = category

    def __repr__(self):
        return f"<DocChunk {self.doc_id}: {self.title} ({self.category})>"


class HybridRAGEngine:
    def __init__(self):
        self.chunks = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self._load_knowledge_base()
        self._build_index()

    def reload_index(self):
        """Reload knowledge base and rebuild vector index after new data submissions."""
        self._load_knowledge_base()
        self._build_index()

    def _load_knowledge_base(self):
        """Loads and chunks knowledge base markdown files and station summaries."""
        self.chunks = []
        doc_counter = 0

        # 1. Load domain knowledge markdown files
        md_files = glob.glob(os.path.join(KB_DIR, "*.md"))
        for filepath in md_files:
            filename = os.path.basename(filepath)
            category = "regulatory" if "standard" in filename else ("health" if "health" in filename else "policy")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    text = f.read()

                # Split by markdown headers
                sections = text.split("\n## ")
                for i, sec in enumerate(sections):
                    if not sec.strip():
                        continue
                    lines = sec.strip().split("\n")
                    header = lines[0].replace("#", "").strip()
                    body = "\n".join(lines[1:]).strip() if len(lines) > 1 else header

                    chunk = DocumentChunk(
                        doc_id=f"kb_{filename}_{i}",
                        title=f"{filename}: {header}",
                        content=f"## {header}\n{body}",
                        source_file=filename,
                        category=category
                    )
                    self.chunks.append(chunk)
                    doc_counter += 1
            except Exception as e:
                print(f"Error loading {filepath}: {e}")

        # 2. Ingest station summaries for semantic station matching
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stn_code, monitoring_location, state_name, water_body_type, 
                       cpcb_class, wqi_score, wqi_status, bathing_safety, search_context
                FROM water_monitoring
            """)
            stations = cursor.fetchall()
            conn.close()

            for stn in stations:
                stn_code, loc, state, wtype, cpcb, wqi, status, safety, context = stn
                chunk = DocumentChunk(
                    doc_id=f"stn_{stn_code}",
                    title=f"Station {stn_code}: {loc} ({state})",
                    content=context,
                    source_file="water_quality.db",
                    category="station_profile"
                )
                self.chunks.append(chunk)
                doc_counter += 1

        print(f"Hybrid RAG Engine initialized with {len(self.chunks)} knowledge chunks.")

    def _build_index(self):
        """Builds TF-IDF semantic vector space over all knowledge chunks."""
        corpus = [f"{c.title}\n{c.content}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words='english',
            max_features=5000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def semantic_search(self, query: str, top_k: int = 4, category_filter: str = None):
        """Retrieve top-k semantically relevant chunks for a natural language query."""
        if not self.chunks or self.vectorizer is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Rank indices
        ranked_indices = np.argsort(similarities)[::-1]

        results = []
        for idx in ranked_indices:
            score = float(similarities[idx])
            if score < 0.05:  # Relevance threshold
                continue
            chunk = self.chunks[idx]
            if category_filter and chunk.category != category_filter:
                continue

            results.append({
                "doc_id": chunk.doc_id,
                "title": chunk.title,
                "content": chunk.content,
                "source": chunk.source_file,
                "category": chunk.category,
                "similarity_score": round(score, 4)
            })
            if len(results) >= top_k:
                break

        return results

    def query_stations_sql(self, sql_query: str):
        """Execute a read-only SQL query on the water quality database."""
        # Security sanity check for read-only execution
        cleaned_sql = sql_query.strip().lower()
        if not cleaned_sql.startswith("select"):
            return {"error": "Only SELECT queries are permitted on water_monitoring."}

        for forbidden in ["delete", "drop", "update", "insert", "alter", "create"]:
            if f" {forbidden} " in f" {cleaned_sql} ":
                return {"error": f"Operation '{forbidden}' is prohibited."}

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query(sql_query, conn)
            conn.close()
            return {"status": "success", "row_count": len(df), "data": df.to_dict(orient="records")}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def find_station_by_keywords(self, keywords: str, limit: int = 5):
        """Find stations using hybrid semantic vector search + SQL token matching."""
        # 1. Semantic station search using indexed station profiles
        semantic_matches = self.semantic_search(keywords, top_k=limit, category_filter="station_profile")
        stn_codes = []
        for match in semantic_matches:
            if match["doc_id"].startswith("stn_"):
                try:
                    code = int(match["doc_id"].replace("stn_", ""))
                    stn_codes.append(code)
                except ValueError:
                    pass

        conn = sqlite3.connect(DB_PATH)
        if stn_codes:
            placeholders = ",".join("?" for _ in stn_codes)
            query = f"SELECT * FROM water_monitoring WHERE stn_code IN ({placeholders})"
            df = pd.read_sql_query(query, conn, params=stn_codes)
            conn.close()
            # Preserve semantic ranking order
            df['sort_order'] = df['stn_code'].map(lambda x: stn_codes.index(x) if x in stn_codes else 999)
            df = df.sort_values('sort_order')
            return df.to_dict(orient="records")

        # 2. Token-based fallback with score ranking
        stopwords = {
            'water', 'quality', 'river', 'lake', 'pond', 'canal', 'drain', 'state',
            'is', 'safe', 'in', 'at', 'the', 'for', 'drinking', 'bathing', 'holy',
            'dipping', 'check', 'show', 'tell', 'about', 'what', 'where', 'how',
            'purify', 'purification', 'treatment', 'clean', 'filter', 'boil',
            'சுத்திகரிப்பு', 'முறை', 'எப்படி', 'சிகிச்சை', 'நீரை'
        }
        words = [w.strip() for w in keywords.split() if len(w.strip()) > 2 and w.lower() not in stopwords]
        if not words:
            query = "SELECT * FROM water_monitoring LIMIT ?"
            params = (limit,)
        else:
            score_terms = []
            where_terms = []
            params = []
            for w in words:
                p = f"%{w}%"
                score_terms.append("(CASE WHEN monitoring_location LIKE ? THEN 2 WHEN state_name LIKE ? THEN 1 ELSE 0 END)")
                where_terms.append("(monitoring_location LIKE ? OR state_name LIKE ? OR water_body_type LIKE ?)")
                params.extend([p, p, p, p, p])

            query = f"""
                SELECT *, ({' + '.join(score_terms)}) as match_score 
                FROM water_monitoring 
                WHERE {' OR '.join(where_terms)} 
                ORDER BY match_score DESC 
                LIMIT ?
            """
            params.append(limit)

        try:
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df.to_dict(orient="records")
        except Exception as e:
            conn.close()
            return []

    def get_water_body_summary(self, state: str = None, water_body_type: str = None):
        """Fetch statistical aggregates for a given state or water body type."""
        conn = sqlite3.connect(DB_PATH)
        where_clauses = []
        params = []
        if state:
            where_clauses.append("state_name = ?")
            params.append(state.upper().strip())
        if water_body_type:
            where_clauses.append("water_body_type = ?")
            params.append(water_body_type.upper().strip())

        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT 
                COUNT(*) as total_stations,
                ROUND(AVG(wqi_score), 1) as avg_wqi,
                ROUND(AVG(do_mean), 2) as avg_do,
                ROUND(AVG(bod_mean), 2) as avg_bod,
                ROUND(AVG(total_coliform_mean), 1) as avg_coliform,
                MAX(bod_max) as max_bod,
                MIN(do_min) as min_do,
                COUNT(CASE WHEN cpcb_class LIKE 'Class A%' THEN 1 END) as class_a_count,
                COUNT(CASE WHEN cpcb_class LIKE 'Class B%' THEN 1 END) as class_b_count,
                COUNT(CASE WHEN cpcb_class LIKE 'Class C%' THEN 1 END) as class_c_count,
                COUNT(CASE WHEN cpcb_class LIKE 'Below Class E%' THEN 1 END) as non_compliant_count
            FROM water_monitoring
            {where_str}
        """
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df.to_dict(orient="records")[0] if not df.empty else {}


if __name__ == "__main__":
    engine = HybridRAGEngine()
    print("\n--- Testing Semantic Search ---")
    results = engine.semantic_search("What are the health risks of bathing in water with high fecal coliform?")
    for r in results:
        print(f"[{r['category']}] {r['title']} (Score: {r['similarity_score']})")

    print("\n--- Testing Station Keyword Search ---")
    stns = engine.find_station_by_keywords("Betwa Vidisha")
    for s in stns:
        print(f"STN {s['stn_code']}: {s['monitoring_location']} - Class: {s['cpcb_class']}, WQI: {s['wqi_score']}")
