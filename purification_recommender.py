"""
Smart Water Purification & Treatment Recommender (நீர் சுத்திகரிப்பு மற்றும் சிகிச்சை பரிந்துரையாளர்).
Generates contaminant-specific household, agricultural, and community purification recipes
based on measured chemical and biological water parameters (DO, BOD, pH, Nitrate, Coliform, EC).
Supports English and Tamil (தமிழ்) output.
"""

from typing import Dict, Any, List


def recommend_purification(sample_data: Any = None, lang: str = "en", **kwargs) -> Dict[str, Any]:
    """
    Generate tailored purification protocols based on exact water metrics.
    Parameters:
    - sample_data: dict containing water parameter keys, or pass metrics as kwargs.
    - lang: 'en' for English, 'ta' for Tamil (தமிழ்).
    """
    if sample_data is None:
        data = {}
    elif isinstance(sample_data, dict):
        data = dict(sample_data)
    else:
        data = {}
    data.update(kwargs)

    is_tamil = str(lang).lower().startswith("ta")

    # Extract metrics safely (checking direct names, max, mean, min)
    do = data.get('do') if data.get('do') is not None else (data.get('do_mean') or data.get('do_min') or 6.0)
    bod = data.get('bod') if data.get('bod') is not None else (data.get('bod_max') or data.get('bod_mean') or 2.0)
    ph = data.get('ph') if data.get('ph') is not None else (data.get('ph_mean') or data.get('ph_max') or 7.5)
    cond = data.get('conductivity') if data.get('conductivity') is not None else (data.get('conductivity_max') or data.get('conductivity_mean') or 300.0)
    nitrate = data.get('nitrate') if data.get('nitrate') is not None else (data.get('nitrate_max') or data.get('nitrate_mean') or 1.0)
    coliform = data.get('total_coliform') if data.get('total_coliform') is not None else (data.get('total_coliform_max') or data.get('total_coliform_mean') or 100.0)
    fecal = data.get('fecal_coliform') if data.get('fecal_coliform') is not None else (data.get('fecal_coliform_max') or data.get('fecal_coliform_mean') or 0.0)
    wtype = str(data.get('water_body_type', 'RIVER')).upper()
    loc = data.get('monitoring_location', 'Selected Water Body')

    if fecal > 0 and fecal > coliform:
        coliform = fecal

    identified_contaminants = []
    household_steps = []
    community_steps = []
    warnings = []
    suitable_uses = []

    # -------------------------------------------------------------
    # CONTAMINANT EVALUATION
    # -------------------------------------------------------------
    high_microbial = coliform > 500 or (coliform > 50 and wtype != 'DRAIN')
    high_organic = bod > 3.0
    severe_organic = bod > 10.0
    high_nitrate = nitrate > 10.0
    high_salinity = cond > 1500 and wtype not in ['BEACH', 'MARINE', 'SEA']
    acidic_ph = ph < 6.5
    alkaline_ph = ph > 8.5
    depleted_oxygen = do < 4.0

    # 1. Microbiological Contamination
    if high_microbial:
        identified_contaminants.append({
            "en": f"High Microbial Pathogen Load (Coliform: {int(coliform):,} MPN/100ml vs limit <= 500)",
            "ta": f"அதிக நுண்ணுயிர் பாக்டீரியா தொற்று (கோலிபார்ம்: {int(coliform):,} MPN/100ml; வரம்பு <= 500)"
        })
        household_steps.append({
            "stage": "Disinfection / கிருமி நீக்கம்",
            "en": "Vigorous boiling for at least 1–3 minutes, or multi-stage UV purification (min. 254 nm wavelength) to neutralize pathogens.",
            "ta": "குறைந்தது 1 முதல் 3 நிமிடங்கள் வரை நன்கு கொதிக்க வைக்கவும், அல்லது புற ஊதா (UV) கிருமி நீக்கக் கருவியைப் பயன்படுத்தவும்."
        })
        community_steps.append({
            "stage": "Chlorination / குளோரினேஷன்",
            "en": "Dose sodium hypochlorite or chlorine gas to maintain 0.5–2.0 mg/L residual free chlorine at distribution points.",
            "ta": "பொது விநியோகத்தில் 0.5–2.0 mg/L குளோரின் இருப்பு இருக்குமாறு சோடியம் ஹைபோகுளோரைட் சேர்க்கவும்."
        })

    # 2. Organic Load & BOD
    if high_organic:
        identified_contaminants.append({
            "en": f"Elevated Organic Pollution (BOD: {bod} mg/L vs limit <= 3.0 mg/L)",
            "ta": f"அதிக கரிமக் கழிவு மாசு (BOD: {bod} mg/L; அனுமதிக்கப்பட்ட வரம்பு <= 3.0 mg/L)"
        })
        household_steps.append({
            "stage": "Activated Carbon / நிலக்கரி வடிகட்டுதல்",
            "en": "Pass through Granular Activated Carbon (GAC) filter to adsorb dissolved organic pollutants, pesticides, and unpleasant odors.",
            "ta": "கரைந்துள்ள கரிமக் கழிவுகள் மற்றும் துர்நாற்றத்தை அகற்ற செயலாக்கப்பட்ட நிலக்கரி (Activated Carbon) வடிகட்டியைப் பயன்படுத்தவும்."
        })
        community_steps.append({
            "stage": "Aeration & Bioremediation / காற்றோட்டம் மற்றும் உயிரியல் சுத்திகரிப்பு",
            "en": "Install stepped cascade aerators or in-situ bio-enzymatic treatment to digest organic sludge and restore oxygen.",
            "ta": "கரிமக் கழிவுகளை சிதைக்க நீர்வீழ்ச்சி போன்ற காற்றோட்ட அமைப்புகள் (Aeration) மற்றும் உயிரியல் சுத்திகரிப்பு முறைகளை நிறுவவும்."
        })

    # 3. Nitrate-Nitrogen (CRITICAL WARNING)
    if high_nitrate:
        identified_contaminants.append({
            "en": f"Dangerous Nitrate Concentration (Nitrate-N: {nitrate} mg/L vs limit <= 10.0 mg/L)",
            "ta": f"ஆபத்தான நைட்ரேட் அளவு (Nitrate-N: {nitrate} mg/L; பாதுகாப்பான வரம்பு <= 10.0 mg/L)"
        })
        household_steps.append({
            "stage": "Reverse Osmosis (RO) / எதிர் சவ்வூடுபரவல் (RO)",
            "en": "Use a certified Reverse Osmosis (RO) system or Strong Base Anion (SBA) ion-exchange resin. Standard sediment or carbon filters CANNOT remove nitrates.",
            "ta": "சான்றளிக்கப்பட்ட RO (Reverse Osmosis) அல்லது அயனி பரிமாற்ற வடிகட்டியைப் பயன்படுத்தவும். சாதாரண வடிகட்டிகளால் நைட்ரேட்டை நீக்க முடியாது."
        })
        warnings.append({
            "en": "CRITICAL HAZARD: DO NOT BOIL THIS WATER FOR INFANTS OR PREGNANT WOMEN! Boiling evaporates water and concentrates nitrate ions, drastically raising the risk of Methemoglobinemia ('Blue Baby Syndrome').",
            "ta": "முக்கிய எச்சரிக்கை: குழந்தைகளுக்கோ கர்ப்பிணிகளுக்கோ இந்த நீரை கொதிக்க வைத்து கொடுக்கக் கூடாது! நீரைக் கொதிக்க வைத்தால் நீர் ஆவியாகி நைட்ரேட்டின் அடர்த்தி அதிகரித்து உயிருக்கு ஆபத்தை விளைவிக்கும் ('நீலக் குழந்தை நோய்க்குறி' / Blue Baby Syndrome)."
        })

    # 4. Total Dissolved Solids / Conductivity
    if high_salinity:
        identified_contaminants.append({
            "en": f"High Mineral Dissolved Solids (Conductivity: {cond} µmho/cm vs limit <= 1500)",
            "ta": f"அதிக கனிமக் கரைசல் மற்றும் உப்புத்தன்மை (மின்கடத்துத்திறன்: {cond} µmho/cm)"
        })
        household_steps.append({
            "stage": "Membrane Demineralization / உப்பு நீக்கம்",
            "en": "Multi-stage Thin Film Composite (TFC) Reverse Osmosis membrane filtration is required to reduce high ionic content.",
            "ta": "உப்பு மற்றும் அதிகப்படியான தாதுக்களைக் குறைக்க RO சவ்வு வடிகட்டுதல் (Thin Film Membrane) அவசியம்."
        })

    # 5. pH Neutralization
    if acidic_ph:
        identified_contaminants.append({
            "en": f"Corrosive Acidic Water (pH: {ph} vs norm 6.5–8.5)",
            "ta": f"அரிக்கும் அமிலத்தன்மை கொண்ட நீர் (pH: {ph}; இயல்பு 6.5–8.5)"
        })
        household_steps.append({
            "stage": "pH Neutralization / காரத்தன்மை சமநிலை",
            "en": "Install a calcite (calcium carbonate) or magnesium oxide neutralizing bed to bring pH up to 7.0–7.4.",
            "ta": "அமிலத்தன்மையை சமன் செய்ய கால்சைட் (Calcite) வடிகட்டி மூலம் pH அளவை 7.0–7.4 ஆக உயர்த்தவும்."
        })
    elif alkaline_ph:
        identified_contaminants.append({
            "en": f"High Alkaline Water (pH: {ph} vs norm 6.5–8.5)",
            "ta": f"அதிக காரத்தன்மை கொண்ட நீர் (pH: {ph}; இயல்பு 6.5–8.5)"
        })

    # 6. Low Oxygen Recovery
    if depleted_oxygen:
        identified_contaminants.append({
            "en": f"Severe Oxygen Depletion (DO: {do} mg/L vs norm >= 5.0 mg/L)",
            "ta": f"கடுமையான ஆக்ஸிஜன் பற்றாக்குறை (DO: {do} mg/L; இயல்பு >= 5.0 mg/L)"
        })

    # Baseline steps if water is relatively clean
    if not identified_contaminants:
        identified_contaminants.append({
            "en": "Water within baseline physicochemical limits (Minor bacterial disinfection required before drinking).",
            "ta": "நீர் இயல்பான தரத்தில் உள்ளது (குடிப்பதற்கு முன் அடிப்படை கிருமி நீக்கம் தேவை)."
        })
        household_steps.append({
            "stage": "Basic Disinfection / அடிப்படை கிருமி நீக்கம்",
            "en": "Standard boiling for 1 minute or gravity-based carbon-ceramic filtration meets BIS 10500 potable norms.",
            "ta": "1 நிமிடம் கொதிக்க வைத்தல் அல்லது சாதாரண வடிகட்டுதல் மூலம் குடிநீராகப் பயன்படுத்தலாம்."
        })

    # Pre-filtration always recommended
    household_steps.insert(0, {
        "stage": "Stage 1: Pre-Filtration / நிலை 1: ஆரம்ப வடிகட்டுதல்",
        "en": "Filter through a 5-micron sediment filter or clean cotton mesh to remove sand, silt, and suspended particles.",
        "ta": "மணல், வண்டல் மற்றும் தூசிகளை அகற்ற 5-மைக்ரான் அல்லது சுத்தமான பருத்தி துணி கொண்டு வடிகட்டவும்."
    })

    # Final language assembly
    lang_key = "ta" if is_tamil else "en"
    
    return {
        "location": loc,
        "language": "Tamil (தமிழ்)" if is_tamil else "English",
        "contaminants": [c[lang_key] for c in identified_contaminants],
        "household_recipe": [
            {"step": f"{idx+1}. {s['stage']}", "instruction": s[lang_key]}
            for idx, s in enumerate(household_steps)
        ],
        "community_remediation": [
            {"step": f"{idx+1}. {s['stage']}", "instruction": s[lang_key]}
            for idx, s in enumerate(community_steps)
        ] if community_steps else [
            {"step": "1. Watershed Protection / நீர்நிலை பாதுகாப்பு", "instruction": "Prevent open defecation, plastic dumping, and agricultural runoff near water intake." if not is_tamil else "நீர்நிலைகளுக்கு அருகில் கழிவுகள் கொட்டுவதையும் திறந்தவெளி மலம் கழிப்பதையும் தடுக்கவும்."}
        ],
        "critical_warnings": [w[lang_key] for w in warnings],
        "boiling_safe": not high_nitrate
    }


def format_purification_markdown(rec: Dict[str, Any], is_tamil: Any = False) -> str:
    """Format the purification recipe as clean Markdown."""
    tamil_flag = True if (is_tamil is True or str(is_tamil).lower().startswith("ta") or rec.get("language") == "Tamil (தமிழ்)") else False
    if tamil_flag:
        md = f"### 🔬 ஸ்மார்ட் நீர் சுத்திகரிப்பு வழிகாட்டி: **{rec['location']}**\n\n"
        md += "#### ⚠️ கண்டறியப்பட்ட மாசுபாடுகள்:\n"
        for c in rec['contaminants']:
            md += f"- 🔴 {c}\n"
        
        if rec['critical_warnings']:
            md += "\n#### 🚨 மிக முக்கிய எச்சரிக்கை:\n"
            for w in rec['critical_warnings']:
                md += f"> **{w}**\n\n"

        md += "\n#### 🚰 வீட்டு உபயோக குடிநீர் சுத்திகரிப்பு முறை:\n"
        for s in rec['household_recipe']:
            md += f"- **{s['step']}**: {s['instruction']}\n"

        md += "\n#### 🏛️ சமூக மற்றும் நீர்நிலை பாதுகாப்பு நடவடிக்கைகள்:\n"
        for s in rec['community_remediation']:
            md += f"- **{s['step']}**: {s['instruction']}\n"
    else:
        md = f"### 🔬 Smart Water Purification Protocol: **{rec['location']}**\n\n"
        md += "#### ⚠️ Detected Water Quality Issues:\n"
        for c in rec['contaminants']:
            md += f"- 🔴 {c}\n"

        if rec['critical_warnings']:
            md += "\n#### 🚨 Critical Safety Warning:\n"
            for w in rec['critical_warnings']:
                md += f"> **{w}**\n\n"

        md += "\n#### 🚰 Step-by-Step Household Drinking Water Recipe:\n"
        for s in rec['household_recipe']:
            md += f"- **{s['step']}**: {s['instruction']}\n"

        md += "\n#### 🏛️ Community & Environmental Remediation Plan:\n"
        for s in rec['community_remediation']:
            md += f"- **{s['step']}**: {s['instruction']}\n"

    return md


if __name__ == "__main__":
    sample = {
        "monitoring_location": "RIVER BETWA AT CHARANTIRGHAT, VIDISHA",
        "do_min": 5.0,
        "bod_max": 20.4,
        "ph_mean": 8.1,
        "conductivity_max": 1056,
        "nitrate_max": 14.59,
        "total_coliform_max": 1600,
        "water_body_type": "RIVER"
    }
    print("--- ENGLISH RECIPE ---")
    rec_en = recommend_purification(sample, lang="en")
    print(format_purification_markdown(rec_en, is_tamil=False))

    print("\n--- TAMIL RECIPE (தமிழ்) ---")
    rec_ta = recommend_purification(sample, lang="ta")
    print(format_purification_markdown(rec_ta, is_tamil=True))
