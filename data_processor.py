"""
Data Processor and Enrichment Pipeline for Indian Water Quality Monitoring.
Cleans raw data, handles 'BDL' (Below Detection Limit) and non-numeric entries,
calculates Water Quality Index (WQI), assigns CPCB Designated Best Use Classes,
evaluates public health safety indicators, and populates SQLite database.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV_PATH = os.path.join(BASE_DIR, "Indian_water_data.csv")
CLEAN_CSV_PATH = os.path.join(BASE_DIR, "clean_water_data.csv")
DB_PATH = os.path.join(BASE_DIR, "water_quality.db")


def parse_measurement(val, default_bdl=0.5):
    """Clean individual cell string, translating BDL to detection floor."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s.upper() in ["BDL", "<BDL", "B.D.L.", "NIL", "ND"]:
        return default_bdl
    if s in ["-", "", "NA", "N/A", "--", "null"]:
        return np.nan
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return np.nan


def compute_wqi(do, bod, ph, cond, nitrate, coliform, is_marine=False):
    """
    Compute Weighted Arithmetic Water Quality Index (0 - 100 scale, higher is better).
    Parameters:
    - do: Dissolved Oxygen (mg/L) - Ideal: 10.0, Min acceptable: 4.0
    - bod: Biochemical Oxygen Demand (mg/L) - Ideal: 0, Max standard: 3.0
    - ph: pH - Ideal: 7.0, Permissible: 6.5 - 8.5
    - cond: Conductivity (µmho/cm) - Ideal: 250, Permissible: 1000 (ignored in marine)
    - nitrate: Nitrate-N (mg/L) - Ideal: 0, Permissible: 10.0
    - coliform: Total Coliform (MPN/100ml) - Ideal: 0, Permissible: 500
    """
    weights = {}
    sub_indices = {}

    # 1. Dissolved Oxygen (Weight: 4)
    if not np.isnan(do):
        weights['do'] = 4.0
        # DO: 8-10 mg/L -> 100, 5 mg/L -> 60, < 2 mg/L -> 10
        q_do = np.clip((do / 8.0) * 100, 0, 100)
        sub_indices['do'] = q_do

    # 2. BOD (Weight: 4)
    if not np.isnan(bod):
        weights['bod'] = 4.0
        # BOD <= 1 -> 100, 3 -> 70, 6 -> 40, >= 20 -> 0
        if bod <= 1.0:
            q_bod = 100.0
        elif bod <= 3.0:
            q_bod = 100.0 - ((bod - 1.0) / 2.0) * 30.0
        elif bod <= 10.0:
            q_bod = 70.0 - ((bod - 3.0) / 7.0) * 45.0
        else:
            q_bod = max(0.0, 25.0 - ((bod - 10.0) / 20.0) * 25.0)
        sub_indices['bod'] = q_bod

    # 3. pH (Weight: 2)
    if not np.isnan(ph):
        weights['ph'] = 2.0
        dev = abs(ph - 7.0)
        if dev <= 0.5:
            q_ph = 100.0
        elif dev <= 1.5:
            q_ph = 80.0
        elif dev <= 2.0:
            q_ph = 50.0
        else:
            q_ph = max(0.0, 30.0 - (dev - 2.0) * 20.0)
        sub_indices['ph'] = q_ph

    # 4. Conductivity (Weight: 2, only for non-marine freshwater)
    if not is_marine and not np.isnan(cond):
        weights['cond'] = 2.0
        if cond <= 500:
            q_cond = 100.0
        elif cond <= 1500:
            q_cond = 100.0 - ((cond - 500) / 1000.0) * 40.0
        elif cond <= 2250:
            q_cond = 60.0 - ((cond - 1500) / 750.0) * 30.0
        else:
            q_cond = max(0.0, 30.0 - ((cond - 2250) / 2000.0) * 30.0)
        sub_indices['cond'] = q_cond

    # 5. Nitrate-N (Weight: 2)
    if not np.isnan(nitrate):
        weights['nitrate'] = 2.0
        if nitrate <= 2.0:
            q_nitrate = 100.0
        elif nitrate <= 10.0:
            q_nitrate = 100.0 - ((nitrate - 2.0) / 8.0) * 40.0
        elif nitrate <= 20.0:
            q_nitrate = 60.0 - ((nitrate - 10.0) / 10.0) * 35.0
        else:
            q_nitrate = max(0.0, 25.0 - ((nitrate - 20.0) / 30.0) * 25.0)
        sub_indices['nitrate'] = q_nitrate

    # 6. Total Coliform (Weight: 3)
    if not np.isnan(coliform):
        weights['coliform'] = 3.0
        if coliform <= 50:
            q_coliform = 100.0
        elif coliform <= 500:
            q_coliform = 85.0
        elif coliform <= 5000:
            q_coliform = 60.0
        elif coliform <= 50000:
            q_coliform = 35.0
        else:
            q_coliform = max(0.0, 15.0 - np.log10(coliform / 50000.0 + 1) * 5.0)
        sub_indices['coliform'] = q_coliform

    if not weights:
        return np.nan

    total_weight = sum(weights.values())
    wqi = sum(sub_indices[k] * weights[k] for k in weights) / total_weight
    return round(float(wqi), 1)


def evaluate_cpcb_class(row):
    """
    Assign CPCB Designated Best Use Class based on CPCB criteria.
    Class A: DO >= 6, BOD <= 2, pH 6.5-8.5, Coliform <= 50
    Class B: DO >= 5, BOD <= 3, pH 6.5-8.5, Coliform <= 500
    Class C: DO >= 4, BOD <= 3, pH 6.0-9.0, Coliform <= 5000
    Class D: DO >= 4, pH 6.5-8.5
    Class E: pH 6.0-8.5, Cond <= 2250
    Below Class E / Non-Compliant
    """
    wbody = str(row.get('water_body_type', '')).upper()
    is_marine = wbody in ['MARINE', 'BEACH', 'SEA', 'CREEK']

    do = row.get('do_max') if not np.isnan(row.get('do_max', np.nan)) else row.get('do_min', np.nan)
    bod = row.get('bod_max') if not np.isnan(row.get('bod_max', np.nan)) else row.get('bod_min', np.nan)
    ph_min = row.get('ph_min', np.nan)
    ph_max = row.get('ph_max', np.nan)
    coliform = row.get('total_coliform_max') if not np.isnan(row.get('total_coliform_max', np.nan)) else row.get('total_coliform_min', np.nan)
    cond = row.get('conductivity_max', np.nan)

    if is_marine:
        # Coastal water classification
        if (np.isnan(bod) or bod <= 3.0) and (np.isnan(do) or do >= 5.0) and (np.isnan(coliform) or coliform <= 500):
            return "Class SW-II (Recreational / Bathing Safe)"
        elif (np.isnan(do) or do >= 4.0) and (np.isnan(bod) or bod <= 5.0):
            return "Class SW-III (Commercial Fishing / Marine Life)"
        else:
            return "Class SW-IV / SW-V (Controlled Industrial / Harbor)"

    # Inland Freshwater Classifications
    # Class A
    if (np.isnan(do) or do >= 6.0) and (np.isnan(bod) or bod <= 2.0) and \
       (np.isnan(ph_min) or ph_min >= 6.5) and (np.isnan(ph_max) or ph_max <= 8.5) and \
       (np.isnan(coliform) or coliform <= 50):
        return "Class A (Drinking without treatment)"

    # Class B
    if (np.isnan(do) or do >= 5.0) and (np.isnan(bod) or bod <= 3.0) and \
       (np.isnan(ph_min) or ph_min >= 6.5) and (np.isnan(ph_max) or ph_max <= 8.5) and \
       (np.isnan(coliform) or coliform <= 500):
        return "Class B (Outdoor Bathing)"

    # Class C
    if (np.isnan(do) or do >= 4.0) and (np.isnan(bod) or bod <= 3.0) and \
       (np.isnan(ph_min) or ph_min >= 6.0) and (np.isnan(ph_max) or ph_max <= 9.0) and \
       (np.isnan(coliform) or coliform <= 5000):
        return "Class C (Drinking after conventional treatment)"

    # Class D
    if (np.isnan(do) or do >= 4.0) and (np.isnan(ph_min) or ph_min >= 6.5) and (np.isnan(ph_max) or ph_max <= 8.5):
        if not np.isnan(bod) and bod > 6.0:
            return "Below Class E (Severely Polluted / Non-Compliant)"
        return "Class D (Wildlife & Fisheries Propagation)"

    # Class E
    if (np.isnan(ph_min) or ph_min >= 6.0) and (np.isnan(ph_max) or ph_max <= 8.5) and \
       (np.isnan(cond) or cond <= 2250):
        if not np.isnan(bod) and bod > 8.0:
            return "Below Class E (Severely Polluted / Non-Compliant)"
        return "Class E (Irrigation & Industrial Cooling)"

    return "Below Class E (Severely Polluted / Non-Compliant)"


def evaluate_advisories(row):
    """Generate plain-language citizen safety verdicts."""
    bod = row.get('bod_max', np.nan)
    do = row.get('do_min', np.nan)
    coliform = row.get('total_coliform_max', np.nan)
    fecal = row.get('fecal_coliform_max', np.nan)
    wbody = str(row.get('water_body_type', '')).upper()

    # Bathing safety
    if wbody in ['DRAIN', 'STP']:
        bathing = "PROHIBITED: Industrial/Sewage Drain"
    elif (not np.isnan(coliform) and coliform > 2500) or (not np.isnan(bod) and bod > 5.0) or (not np.isnan(do) and do < 3.0):
        bathing = "UNSAFE: High Pathogen / Organic Load"
    elif (not np.isnan(coliform) and coliform > 500) or (not np.isnan(bod) and bod > 3.0):
        bathing = "CAUTION: Moderate Bacterial Contamination"
    else:
        bathing = "SAFE: Compliant for Outdoor Bathing"

    # Drinking safety
    if wbody in ['DRAIN', 'STP']:
        drinking = "STRICTLY UNFIT: Untreated Waste Discharge"
    elif not np.isnan(coliform) and coliform > 5000:
        drinking = "UNFIT: Severe Microbial Contamination"
    elif not np.isnan(bod) and bod > 3.0:
        drinking = "UNFIT: High Organic Pollution"
    else:
        drinking = "SAFE ONLY WITH FULL CONVENTIONAL TREATMENT & DISINFECTION"

    # Aquatic life health
    if not np.isnan(do) and do < 2.0:
        aquatic = "CRITICAL HYPOXIA: Fish Kills Likely"
    elif not np.isnan(do) and do < 4.0:
        aquatic = "STRESSED: Only hardy species survive"
    else:
        aquatic = "HEALTHY: Sufficient oxygenation for aquatic life"

    # Primary concern parameter
    concerns = []
    if not np.isnan(coliform) and coliform > 500:
        concerns.append(f"Coliform ({int(coliform):,} MPN)")
    if not np.isnan(bod) and bod > 3.0:
        concerns.append(f"BOD ({bod} mg/L)")
    if not np.isnan(do) and do < 4.0:
        concerns.append(f"Low DO ({do} mg/L)")
    if not np.isnan(fecal) and fecal > 500:
        concerns.append(f"Fecal Coliform ({fecal} MPN)")

    primary_concern = ", ".join(concerns) if concerns else "None (Within Baseline Norms)"

    return bathing, drinking, aquatic, primary_concern


def process_dataset():
    """Main data processing, cleaning, index calculation, and database loading."""
    print("Reading raw water quality dataset...")
    df = pd.read_csv(RAW_CSV_PATH)

    # Column mapping dictionary
    clean_cols = {
        'STN code': 'stn_code',
        'Monitoring Location': 'monitoring_location',
        'Year': 'year',
        'Type Water Body': 'water_body_type',
        'State Name': 'state_name',
        'Temperature (C) - Min': 'temp_min',
        'Temperature (C) - Max': 'temp_max',
        'Dissolved - Min': 'do_min',
        'Dissolved - Max': 'do_max',
        'pH - Min': 'ph_min',
        'pH - Max': 'ph_max',
        'Conductivity (¬µmho/cm) - Min': 'conductivity_min',
        'Conductivity (¬µmho/cm) - Max': 'conductivity_max',
        'BOD (mg/L) - Min': 'bod_min',
        'BOD (mg/L) - Max': 'bod_max',
        'NitrateN (mg/L) - Min': 'nitrate_min',
        'NitrateN (mg/L) - Max': 'nitrate_max',
        'Fecal Coliform (MPN/100ml) - Min': 'fecal_coliform_min',
        'Fecal Coliform (MPN/100ml) - Max': 'fecal_coliform_max',
        'Total Coliform (MPN/100ml) - Min': 'total_coliform_min',
        'Total Coliform (MPN/100ml) - Max': 'total_coliform_max',
        'Fecal - Min': 'fecal_streptococci_min',
        'Fecal - Max': 'fecal_streptococci_max'
    }

    # Rename columns that exist in the dataframe
    rename_map = {k: v for k, v in clean_cols.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # Clean text columns
    df['monitoring_location'] = df['monitoring_location'].astype(str).str.strip()
    df['water_body_type'] = df['water_body_type'].astype(str).str.strip().str.upper()
    df['state_name'] = df['state_name'].astype(str).str.strip().str.upper()
    df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(2022).astype(int)

    # Clean numeric columns with measurement parser
    numeric_fields = [
        'temp_min', 'temp_max', 'do_min', 'do_max', 'ph_min', 'ph_max',
        'conductivity_min', 'conductivity_max', 'bod_min', 'bod_max',
        'nitrate_min', 'nitrate_max', 'fecal_coliform_min', 'fecal_coliform_max',
        'total_coliform_min', 'total_coliform_max',
        'fecal_streptococci_min', 'fecal_streptococci_max'
    ]

    for col in numeric_fields:
        if col in df.columns:
            # For trace pollutants BDL is healthy/trace
            default_bdl = 0.5 if 'bod' in col or 'nitrate' in col else (1.0 if 'coliform' in col or 'strep' in col else 0.5)
            df[col] = df[col].apply(lambda v: parse_measurement(v, default_bdl))

    # Calculate derived average columns
    df['do_mean'] = df[['do_min', 'do_max']].mean(axis=1)
    df['bod_mean'] = df[['bod_min', 'bod_max']].mean(axis=1)
    df['ph_mean'] = df[['ph_min', 'ph_max']].mean(axis=1)
    df['conductivity_mean'] = df[['conductivity_min', 'conductivity_max']].mean(axis=1)
    df['nitrate_mean'] = df[['nitrate_min', 'nitrate_max']].mean(axis=1)
    df['total_coliform_mean'] = df[['total_coliform_min', 'total_coliform_max']].mean(axis=1)

    # Calculate WQI for each row
    wqi_scores = []
    wqi_statuses = []
    for idx, row in df.iterrows():
        is_marine = row['water_body_type'] in ['BEACH', 'MARINE', 'SEA', 'CREEK']
        score = compute_wqi(
            do=row['do_mean'],
            bod=row['bod_mean'],
            ph=row['ph_mean'],
            cond=row['conductivity_mean'],
            nitrate=row['nitrate_mean'],
            coliform=row['total_coliform_mean'],
            is_marine=is_marine
        )
        wqi_scores.append(score)

        if np.isnan(score):
            status = "Insufficient Data"
        elif score >= 85:
            status = "Excellent"
        elif score >= 70:
            status = "Good"
        elif score >= 50:
            status = "Fair / Moderate"
        elif score >= 35:
            status = "Poor"
        else:
            status = "Very Poor / Critical"
        wqi_statuses.append(status)

    df['wqi_score'] = wqi_scores
    df['wqi_status'] = wqi_statuses

    # Assign CPCB Classification
    df['cpcb_class'] = df.apply(evaluate_cpcb_class, axis=1)

    # Assign Plain-Language Citizen Advisories
    bathing_list, drinking_list, aquatic_list, concerns_list = [], [], [], []
    for _, row in df.iterrows():
        b, d, a, c = evaluate_advisories(row)
        bathing_list.append(b)
        drinking_list.append(d)
        aquatic_list.append(a)
        concerns_list.append(c)

    df['bathing_safety'] = bathing_list
    df['drinking_suitability'] = drinking_list
    df['aquatic_health'] = aquatic_list
    df['primary_concerns'] = concerns_list

    # Generate rich descriptive text for semantic search and RAG indexing
    search_texts = []
    for _, row in df.iterrows():
        desc = (
            f"Station {row['stn_code']}: {row['monitoring_location']} ({row['water_body_type']}) "
            f"in {row['state_name']} (Year {row['year']}). "
            f"CPCB Class: {row['cpcb_class']}. Water Quality Index (WQI): {row['wqi_score']} ({row['wqi_status']}). "
            f"DO Range: {row['do_min']}-{row['do_max']} mg/L, BOD Range: {row['bod_min']}-{row['bod_max']} mg/L, "
            f"pH Range: {row['ph_min']}-{row['ph_max']}, "
            f"Total Coliform: {row['total_coliform_min']}-{row['total_coliform_max']} MPN/100ml. "
            f"Bathing Safety: {row['bathing_safety']}. Primary Environmental Concerns: {row['primary_concerns']}."
        )
        search_texts.append(desc)
    df['search_context'] = search_texts

    # Save cleaned CSV
    print(f"Writing cleaned dataset to {CLEAN_CSV_PATH}...")
    df.to_csv(CLEAN_CSV_PATH, index=False)

    # Save to SQLite Database
    print(f"Writing to SQLite database {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing table if exists
    cursor.execute("DROP TABLE IF EXISTS water_monitoring")

    df.to_sql("water_monitoring", conn, index=False)

    # Create search indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stn ON water_monitoring (stn_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_state ON water_monitoring (state_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON water_monitoring (water_body_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cpcb ON water_monitoring (cpcb_class)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wqi ON water_monitoring (wqi_status)")

    conn.commit()
    conn.close()

    print("Data processing and DB creation complete!")
    print(f"Total records processed: {len(df)}")
    print("WQI Status breakdown:")
    print(df['wqi_status'].value_counts())
    print("\nCPCB Class breakdown:")
    print(df['cpcb_class'].value_counts())
    return df


def add_manual_sample(
    monitoring_location: str,
    state_name: str,
    water_body_type: str = "RIVER",
    do: float = np.nan,
    bod: float = np.nan,
    ph: float = np.nan,
    conductivity: float = np.nan,
    nitrate: float = np.nan,
    total_coliform: float = np.nan,
    fecal_coliform: float = np.nan,
    temp: float = 25.0,
    year: int = 2026
) -> dict:
    """
    Ingest a manual water quality sample submitted by a citizen, field volunteer, or lab inspector.
    Calculates WQI, CPCB class, and citizen advisories, then persists to SQLite and CSV.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Determine unique station code for manual submissions (starts at 90001)
    cursor.execute("SELECT MAX(stn_code) FROM water_monitoring WHERE stn_code >= 90000")
    max_manual = cursor.fetchone()[0]
    stn_code = (max_manual + 1) if max_manual else 90001

    # Standardize string fields
    loc_clean = str(monitoring_location).strip()
    state_clean = str(state_name).strip().upper()
    type_clean = str(water_body_type).strip().upper()

    is_marine = type_clean in ['BEACH', 'MARINE', 'SEA', 'CREEK']

    # Safe float conversions
    def safe_float(v):
        try:
            return float(v) if v is not None and not np.isnan(float(v)) else np.nan
        except (ValueError, TypeError):
            return np.nan

    f_do = safe_float(do)
    f_bod = safe_float(bod)
    f_ph = safe_float(ph)
    f_cond = safe_float(conductivity)
    f_nitrate = safe_float(nitrate)
    f_coliform = safe_float(total_coliform)
    f_fecal = safe_float(fecal_coliform)
    f_temp = safe_float(temp) if safe_float(temp) is not np.nan else 25.0

    # Calculate WQI
    wqi_score = compute_wqi(
        do=f_do, bod=f_bod, ph=f_ph, cond=f_cond,
        nitrate=f_nitrate, coliform=f_coliform, is_marine=is_marine
    )

    if np.isnan(wqi_score):
        wqi_status = "Insufficient Data"
    elif wqi_score >= 85:
        wqi_status = "Excellent"
    elif wqi_score >= 70:
        wqi_status = "Good"
    elif wqi_score >= 50:
        wqi_status = "Fair / Moderate"
    elif wqi_score >= 35:
        wqi_status = "Poor"
    else:
        wqi_status = "Very Poor / Critical"

    # Assemble row dictionary for rule evaluations
    row_data = {
        'stn_code': stn_code,
        'monitoring_location': loc_clean,
        'year': int(year),
        'water_body_type': type_clean,
        'state_name': state_clean,
        'temp_min': f_temp,
        'temp_max': f_temp,
        'do_min': f_do,
        'do_max': f_do,
        'ph_min': f_ph,
        'ph_max': f_ph,
        'conductivity_min': f_cond,
        'conductivity_max': f_cond,
        'bod_min': f_bod,
        'bod_max': f_bod,
        'nitrate_min': f_nitrate,
        'nitrate_max': f_nitrate,
        'fecal_coliform_min': f_fecal,
        'fecal_coliform_max': f_fecal,
        'total_coliform_min': f_coliform,
        'total_coliform_max': f_coliform,
        'fecal_streptococci_min': np.nan,
        'fecal_streptococci_max': np.nan,
        'do_mean': f_do,
        'bod_mean': f_bod,
        'ph_mean': f_ph,
        'conductivity_mean': f_cond,
        'nitrate_mean': f_nitrate,
        'total_coliform_mean': f_coliform,
        'wqi_score': wqi_score,
        'wqi_status': wqi_status
    }

    # Evaluate CPCB classification & advisories
    cpcb_class = evaluate_cpcb_class(row_data)
    bathing, drinking, aquatic, concerns = evaluate_advisories(row_data)

    row_data['cpcb_class'] = cpcb_class
    row_data['bathing_safety'] = bathing
    row_data['drinking_suitability'] = drinking
    row_data['aquatic_health'] = aquatic
    row_data['primary_concerns'] = concerns

    # Build semantic search context
    search_context = (
        f"Station {stn_code}: {loc_clean} ({type_clean}) in {state_clean} (Year {year}, Manual Submission). "
        f"CPCB Class: {cpcb_class}. Water Quality Index (WQI): {wqi_score} ({wqi_status}). "
        f"DO: {f_do} mg/L, BOD: {f_bod} mg/L, pH: {f_ph}, "
        f"Total Coliform: {f_coliform} MPN/100ml. "
        f"Bathing Safety: {bathing}. Primary Concerns: {concerns}."
    )
    row_data['search_context'] = search_context

    # Insert into SQLite
    cols = list(row_data.keys())
    placeholders = ",".join("?" for _ in cols)
    sql = f"INSERT INTO water_monitoring ({','.join(cols)}) VALUES ({placeholders})"
    cursor.execute(sql, [row_data[c] for c in cols])
    conn.commit()
    conn.close()

    # Append to clean_water_data.csv
    if os.path.exists(CLEAN_CSV_PATH):
        df_new = pd.DataFrame([row_data])
        df_new.to_csv(CLEAN_CSV_PATH, mode='a', header=False, index=False)

    return row_data


if __name__ == "__main__":
    process_dataset()

