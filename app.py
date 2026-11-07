"""
Streamlit Web Application: AI Agent-Based Water Quality Monitoring, Public Awareness & Purification Recommender Assistant.
Features:
1. Conversational AI Assistant (Local Expert + Optional Gemini 3.5 Flash Lite)
2. Smart Water Purification & Treatment Recommender (English & தமிழ்)
3. Interactive Water Quality Dashboard & Explorer
4. Station Deep-Dive & Citizen Health Scorecard
5. Citizen Science & Manual Field Data Ingestion
6. Citizen Grievance & Regulatory Action Letter Generator
"""

import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from data_processor import add_manual_sample
from water_agent import WaterQualityAgent
from purification_recommender import recommend_purification, format_purification_markdown

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Automatically load .env
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Page configuration
st.set_page_config(
    page_title="NeerParvai (நீர் பார்வை) - AI Water Quality Assistant",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

CLEAN_CSV_PATH = os.path.join(BASE_DIR, "clean_water_data.csv")


@st.cache_resource
def load_agent(api_key=None, mode_preference="Auto", model_name="gemini-3.5-flash-lite"):
    effective_key = api_key if mode_preference != "Local Expert (Offline)" else None
    mode = "expert" if mode_preference == "Local Expert (Offline)" else "llm"
    return WaterQualityAgent(api_key=effective_key, mode_override=mode, model_name=model_name)


@st.cache_data
def load_data():
    if os.path.exists(CLEAN_CSV_PATH):
        return pd.read_csv(CLEAN_CSV_PATH)
    return pd.DataFrame()


# Initialize state and data
df = load_data()

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/water.png", width=70)
    st.title("NeerParvai AI (நீர் பார்வை) 💧")
    st.caption("AI நீர் தரம் கண்காணிப்பு & சுத்திகரிப்பு ஆலோசகர் / Water Quality & Purification Assistant")
    st.markdown("---")

    ui_lang = st.radio(
        "🌐 Language / மொழி",
        ["English", "தமிழ் (Tamil)"],
        horizontal=True,
        help="Select language for UI recommendations and purification advice"
    )

    nav = st.radio(
        "Navigation / வழிசெலுத்தல்",
        [
            "💬 AI Citizen Assistant",
            "🔬 Purification Recommender / நீர் சுத்திகரிப்பு",
            "📊 Monitoring Explorer",
            "🎯 Station Deep-Dive",
            "➕ Submit Water Sample",
            "📑 Grievance Generator",
            "📖 Standards & Guides"
        ]
    )

    st.markdown("---")
    st.subheader("⚙️ AI & LLM Engine")
    
    env_key = os.environ.get("GEMINI_API_KEY", "").strip("'\" ")
    if env_key:
        st.success(f"✅ `.env` detected: `GEMINI_API_KEY` ({env_key[:6]}...{env_key[-4:]})")
    
    mode_selection = st.radio(
        "Agent Execution Mode",
        ["🤖 Gemini LLM Agent (Live)", "⚡ Local Expert Agent (Offline Fast)"],
        index=0 if env_key else 1
    )

    if mode_selection == "🤖 Gemini LLM Agent (Live)":
        custom_key = st.text_input("Gemini API Key", value=env_key, type="password")
        model_choice = st.selectbox(
            "Gemini Model",
            ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"],
            index=0,
            help="Gemini 3.5 Flash Lite is optimized for low-latency reasoning and high-throughput RAG generation."
        )
        agent = load_agent(api_key=custom_key, mode_preference="LLM", model_name=model_choice)
        st.success(f"Active LLM: **{model_choice}**")
    else:
        agent = load_agent(api_key=None, mode_preference="Local Expert (Offline)")
        st.info("Using **Local Deterministic Expert Agent** (CPCB/WQI rule engine, instant response).")

    st.markdown("---")
    st.caption("Dataset: CPCB Indian Water Monitoring (194 Stations, 17 States)")


# -------------------------------------------------------------
# TAB 1: CONVERSATIONAL ASSISTANT
# -------------------------------------------------------------
if nav == "💬 AI Citizen Assistant":
    st.header("💬 NeerParvai (நீர் பார்வை): AI Water Quality & Purification Assistant")
    st.markdown(
        "Ask questions about Indian rivers, bathing safety, drinking water standards, pollution hotspots, state summaries, or purification methods in English or தமிழ்."
    )

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Vanakkam! (வணக்கம்) 🙏 I am your **Intelligent Water Quality & Purification Assistant (நீர் பார்வை)**.\n\n"
                    "You can ask me questions in English or தமிழ், such as:\n"
                    "- *'Is River Betwa at Charantirghat safe for holy dipping?'*\n"
                    "- *'How to purify water with high nitrate concentration?'*\n"
                    "- *'அதிக பாக்டீரியா உள்ள நீரை சுத்திகரிப்பது எப்படி?' (How to purify water with high bacteria?)*\n"
                    "- *'Show top 5 water pollution hotspots with highest BOD'* \n"
                    "- *'Check water quality at Rushikonda Beach, Visakhapatnam'*\n"
                    "- *'State summary and CPCB class distribution for Jharkhand'*\n"
                    "- *'Draft formal SPCB grievance petition for Agra Canal'*"
                )
            }
        ]

    # Quick Prompts
    st.markdown("**Suggested Quick Inquiries / பரிந்துரைக்கப்பட்ட வினவல்கள்:**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🌊 Is Betwa safe for bath?"):
            st.session_state.quick_query = "Is River Betwa at Charantirghat safe for bathing?"
        if st.button("🏖️ Rushikonda Beach quality?"):
            st.session_state.quick_query = "Check water quality at Rushikonda Beach, Visakhapatnam"
    with col2:
        if st.button("🚨 Top 5 BOD Hotspots"):
            st.session_state.quick_query = "Show top 5 water pollution hotspots with highest BOD"
        if st.button("📊 State Summary: Jharkhand"):
            st.session_state.quick_query = "State summary and overview for Jharkhand"
    with col3:
        if st.button("📑 Draft SPCB Grievance"):
            st.session_state.quick_query = "Draft formal SPCB grievance petition for Agra Canal"
        if st.button("📚 Explain BOD & Coliform"):
            st.session_state.quick_query = "Explain what BOD and Fecal Coliform mean for drinking water"
    with col4:
        if st.button("🔬 Purify High Nitrate Water"):
            st.session_state.quick_query = "How to purify water with high nitrate concentration?"
        if st.button("🌿 சுத்திகரிப்பு முறை (Tamil)"):
            st.session_state.quick_query = "அதிக பாக்டீரியா உள்ள நீரை சுத்திகரிப்பது எப்படி?"

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    query_input = st.chat_input("Ask about water quality, river safety, or regulations...")
    active_query = query_input or st.session_state.pop("quick_query", None)

    if active_query:
        # User message
        st.session_state.messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        # Agent processing
        with st.chat_message("assistant"):
            with st.spinner("Analyzing water monitoring parameters & retrieving standards..."):
                response_data = agent.answer_query(active_query)
                answer_text = response_data["response"]
                mode_tag = f"\n\n*Generated by {response_data['mode']} (Intent: `{response_data['intent']}`)*"
                full_reply = answer_text + mode_tag
                st.markdown(full_reply)

                # Show retrieved evidence in an expander
                with st.expander("🔍 View Retrieved Knowledge & Data Evidence"):
                    st.write("**Identified Intent:**", response_data["intent"])
                    if response_data.get("retrieved_context"):
                        st.write("**Retrieved Regulatory & Health Chunks:**")
                        for doc in response_data["retrieved_context"]:
                            st.caption(f"- **{doc['title']}** (Score: {doc['similarity_score']})")
                    if response_data.get("evidence"):
                        st.write("**Queried Evidence Payload:**")
                        st.json(response_data["evidence"])

        st.session_state.messages.append({"role": "assistant", "content": full_reply})


# -------------------------------------------------------------
# TAB 2: SMART WATER PURIFICATION & TREATMENT RECOMMENDER
# -------------------------------------------------------------
elif nav == "🔬 Purification Recommender / நீர் சுத்திகரிப்பு":
    st.header("🔬 Smart Water Purification & Treatment Recommender / சுத்திகரிப்பு ஆலோசகர்")
    st.markdown(
        "Automated multi-barrier treatment diagnosis and step-by-step purification recipes for households, farms, and local communities based on CPCB and BIS 10500 standards."
    )

    p_col1, p_col2 = st.columns([1, 1])
    with p_col1:
        source_mode = st.radio(
            "Select Water Source / நீர் மூலத்தைத் தேர்ந்தெடுக்கவும்:",
            ["📍 Monitored CPCB Station (கண்காணிக்கப்படும் நிலையம்)", "🧪 Custom Water Sample & Field Input (தனிப்பயன் மாதிரி)"],
            horizontal=False
        )

    sample_dict = {}

    if "Monitored CPCB Station" in source_mode:
        if not df.empty:
            stn_options = [f"{row['stn_code']} - {row['monitoring_location']} ({row['state_name']})" for _, row in df.iterrows()]
            default_ix = 0
            for i, opt in enumerate(stn_options):
                if "CHARANTIRGHAT" in opt:
                    default_ix = i
                    break
            chosen_stn_str = st.selectbox("Select Station / நிலையத்தைத் தேர்ந்தெடுக்கவும்", stn_options, index=default_ix)
            chosen_code = int(chosen_stn_str.split(" - ")[0])
            stn_row = df[df['stn_code'] == chosen_code].iloc[0]

            st.caption(f"Category: **{stn_row['water_body_type']}** | State: **{stn_row['state_name']}** | WQI: **{stn_row['wqi_score']}** | CPCB: **{stn_row['cpcb_class']}**")

            with st.expander("⚙️ View / Adjust Station Measurements", expanded=False):
                ca, cb, cc = st.columns(3)
                adj_bod = ca.number_input("Peak BOD (mg/L)", value=float(stn_row['bod_max']), min_value=0.0, step=0.5)
                adj_coliform = cb.number_input("Peak Coliform (MPN/100ml)", value=float(stn_row['total_coliform_max']), min_value=0.0, step=100.0)
                adj_nitrate = cc.number_input("Peak Nitrate-N (mg/L)", value=float(stn_row['nitrate_max']), min_value=0.0, step=0.5)

                cd, ce, cf = st.columns(3)
                adj_cond = cd.number_input("Conductivity (µmho/cm)", value=float(stn_row['conductivity_max']), min_value=0.0, step=50.0)
                adj_ph = ce.number_input("pH Level", value=float(stn_row['ph_max']), min_value=1.0, max_value=14.0, step=0.1)
                adj_do = cf.number_input("Minimum DO (mg/L)", value=float(stn_row['do_min']), min_value=0.0, step=0.5)

            sample_dict = {
                "monitoring_location": stn_row['monitoring_location'],
                "water_body_type": stn_row['water_body_type'],
                "bod_max": adj_bod,
                "total_coliform_max": adj_coliform,
                "nitrate_max": adj_nitrate,
                "conductivity_max": adj_cond,
                "ph_max": adj_ph,
                "do_min": adj_do
            }
        else:
            st.error("No water monitoring data loaded.")
    else:
        # Custom Water Sample
        preset = st.selectbox(
            "Quick Water Type Preset / மாதிரி வகை:",
            [
                "Custom / Manual Input (தனிப்பயன் உள்ளீடு)",
                "🚨 Raw Sewage Contaminated Surface Water (High Coliform & BOD)",
                "🌾 Agricultural Runoff / High Nitrate Well Water",
                "🌊 Brackish / High Salinity Ground Water",
                "🏞️ Natural Upland Stream / Spring (Relatively Clean)"
            ]
        )

        preset_defaults = {
            "Custom / Manual Input (தனிப்பயன் உள்ளீடு)": (2.0, 500.0, 1.0, 350.0, 7.4, 6.0, "Custom Well Water"),
            "🚨 Raw Sewage Contaminated Surface Water (High Coliform & BOD)": (22.5, 4500.0, 4.2, 850.0, 7.8, 1.8, "Urban Nallah / Polluted River"),
            "🌾 Agricultural Runoff / High Nitrate Well Water": (2.8, 180.0, 16.5, 950.0, 7.2, 5.5, "Agricultural Area Borewell"),
            "🌊 Brackish / High Salinity Ground Water": (1.5, 40.0, 2.0, 2800.0, 8.2, 6.2, "Coastal Ground Water"),
            "🏞️ Natural Upland Stream / Spring (Relatively Clean)": (0.8, 40.0, 0.4, 120.0, 7.2, 7.8, "Upland Hill Spring")
        }

        def_bod, def_col, def_nit, def_cond, def_ph, def_do, def_loc = preset_defaults[preset]

        cust_loc = st.text_input("Sample / Location Name / மாதிரியின் பெயர்", value=def_loc)
        ca, cb, cc = st.columns(3)
        inp_bod = ca.number_input("BOD (mg/L)", value=def_bod, min_value=0.0, step=0.5, help="CPCB limit <= 3.0 mg/L")
        inp_coliform = cb.number_input("Total Coliform (MPN/100ml)", value=def_col, min_value=0.0, step=50.0, help="CPCB Bathing <= 500, Drinking = 0")
        inp_nitrate = cc.number_input("Nitrate-N (mg/L)", value=def_nit, min_value=0.0, step=0.5, help="BIS 10500 safe limit <= 10.0 mg/L")

        cd, ce, cf = st.columns(3)
        inp_cond = cd.number_input("Conductivity (µmho/cm)", value=def_cond, min_value=0.0, step=50.0, help="Irrigation <= 2250 µmho/cm")
        inp_ph = ce.number_input("pH Level", value=def_ph, min_value=1.0, max_value=14.0, step=0.1, help="Safe norm 6.5 - 8.5")
        inp_do = cf.number_input("Dissolved Oxygen (mg/L)", value=def_do, min_value=0.0, step=0.5, help="Healthy aquatic life >= 5.0 mg/L")

        sample_dict = {
            "monitoring_location": cust_loc,
            "water_body_type": "SAMPLE",
            "bod_max": inp_bod,
            "total_coliform_max": inp_coliform,
            "nitrate_max": inp_nitrate,
            "conductivity_max": inp_cond,
            "ph_max": inp_ph,
            "do_min": inp_do
        }

    st.markdown("---")
    
    col_btn, col_lang = st.columns([2, 1])
    with col_lang:
        override_lang = st.selectbox(
            "Protocol Language / நெறிமுறை மொழி",
            ["English", "தமிழ் (Tamil)"],
            index=1 if "தமிழ்" in ui_lang else 0
        )
        rec_lang = "ta" if "தமிழ்" in override_lang else "en"

    with col_btn:
        generate_clicked = st.button("🔬 Generate Purification Protocol / சுத்திகரிப்பு வழிகாட்டியை உருவாக்கு", type="primary")

    if (generate_clicked or sample_dict) and sample_dict:
        recipe = recommend_purification(sample_dict, lang=rec_lang)
        recipe_md = format_purification_markdown(recipe, is_tamil=(rec_lang == "ta"))

        if recipe.get("critical_warnings"):
            for w in recipe["critical_warnings"]:
                st.error(f"🚨 {w}")

        st.markdown(recipe_md)

        loc_slug = str(sample_dict.get('monitoring_location', 'water_sample')).replace(' ', '_')[:30]
        st.download_button(
            label="📥 Download Purification Protocol (.md)",
            data=recipe_md,
            file_name=f"purification_protocol_{loc_slug}.md",
            mime="text/markdown"
        )


# -------------------------------------------------------------
# TAB 3: MONITORING EXPLORER
# -------------------------------------------------------------
elif nav == "📊 Monitoring Explorer":
    st.header("📊 National Water Quality Monitoring Explorer")
    st.markdown("Filter, analyze, and explore 194 continuous monitoring stations across 17 States and Union Territories.")

    if df.empty:
        st.error("Cleaned water dataset not found. Please run data_processor.py.")
    else:
        # High level KPIs
        k1, k2, k3, k4 = st.columns(4)
        avg_wqi = df['wqi_score'].mean()
        safe_bathing = (df['bathing_safety'].str.contains('SAFE')).sum() / len(df) * 100
        severely_polluted = (df['cpcb_class'].str.contains('Below Class E')).sum()
        total_stns = len(df)

        k1.metric("Monitored Stations", f"{total_stns}")
        k2.metric("National Avg WQI", f"{avg_wqi:.1f} / 100")
        k3.metric("Bathing Safe Stations", f"{safe_bathing:.1f}%")
        k4.metric("Severely Polluted", f"{severely_polluted}", delta=f"{severely_polluted/total_stns*100:.1f}% of total", delta_color="inverse")

        st.markdown("---")

        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            states = ["ALL"] + sorted(df['state_name'].dropna().unique().tolist())
            sel_state = st.selectbox("Filter by State", states)
        with f2:
            wbtypes = ["ALL"] + sorted(df['water_body_type'].dropna().unique().tolist())
            sel_wbtype = st.selectbox("Filter by Water Body Type", wbtypes)
        with f3:
            wqi_classes = ["ALL"] + sorted(df['wqi_status'].dropna().unique().tolist())
            sel_wqi = st.selectbox("Filter by WQI Status", wqi_classes)

        filtered_df = df.copy()
        if sel_state != "ALL":
            filtered_df = filtered_df[filtered_df['state_name'] == sel_state]
        if sel_wbtype != "ALL":
            filtered_df = filtered_df[filtered_df['water_body_type'] == sel_wbtype]
        if sel_wqi != "ALL":
            filtered_df = filtered_df[filtered_df['wqi_status'] == sel_wqi]

        st.subheader(f"Filtered Results ({len(filtered_df)} stations)")

        # Visualizations
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.markdown("#### CPCB Class Breakdown")
            cpcb_counts = filtered_df['cpcb_class'].value_counts()
            st.bar_chart(cpcb_counts)

        with chart_col2:
            st.markdown("#### BOD vs Dissolved Oxygen (DO)")
            chart_data = filtered_df[['do_mean', 'bod_mean']].dropna()
            st.scatter_chart(chart_data, x='bod_mean', y='do_mean')

        # Data table
        display_cols = [
            'stn_code', 'monitoring_location', 'state_name', 'water_body_type',
            'wqi_score', 'wqi_status', 'cpcb_class', 'bathing_safety', 'bod_max', 'do_min', 'total_coliform_max'
        ]
        st.dataframe(filtered_df[display_cols], use_container_width=True)


# -------------------------------------------------------------
# TAB 3: STATION DEEP-DIVE
# -------------------------------------------------------------
elif nav == "🎯 Station Deep-Dive":
    st.header("🎯 Monitoring Station Deep-Dive & Public Health Scorecard")
    st.markdown("Select any monitoring station to inspect full physicochemical ranges and public safety assessments.")

    if not df.empty:
        station_options = [f"{row['stn_code']} - {row['monitoring_location']} ({row['state_name']})" for _, row in df.iterrows()]
        selected_option = st.selectbox("Select Station", station_options, index=0)
        selected_stn_code = int(selected_option.split(" - ")[0])

        stn = df[df['stn_code'] == selected_stn_code].iloc[0]

        st.markdown(f"### {stn['monitoring_location']}")
        st.caption(f"Station Code: `{stn['stn_code']}` | State: **{stn['state_name']}** | Category: **{stn['water_body_type']}** | Year: **{stn['year']}**")

        # Scorecard badges
        c1, c2, c3 = st.columns(3)
        wqi = stn['wqi_score']
        wqi_color = "🟢" if wqi >= 70 else ("🟡" if wqi >= 50 else "🔴")
        c1.metric("Water Quality Index (WQI)", f"{wqi_color} {wqi}/100", stn['wqi_status'])
        c2.metric("CPCB Classification", stn['cpcb_class'])
        c3.metric("Bathing Safety Status", stn['bathing_safety'].split(":")[0])

        st.markdown("---")

        # Public Safety Details
        st.subheader("🛡️ Public Health & Safety Assessment")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown(f"**🏊 Bathing / Dipping:**\n\n`{stn['bathing_safety']}`")
        with p2:
            st.markdown(f"**🚰 Potable / Drinking:**\n\n`{stn['drinking_suitability']}`")
        with p3:
            st.markdown(f"**🐟 Aquatic Ecosystem:**\n\n`{stn['aquatic_health']}`")

        st.markdown(f"**Primary Environmental Concerns:** `{stn['primary_concerns']}`")

        # Detailed Parameters Table
        st.markdown("---")
        st.subheader("🧪 Monitored Chemical & Biological Parameters")
        param_data = {
            "Parameter": [
                "Dissolved Oxygen (DO)", "Biochemical Oxygen Demand (BOD)", "pH",
                "Total Coliform", "Fecal Coliform", "Conductivity", "Nitrate-N", "Temperature"
            ],
            "Min Recorded": [
                f"{stn['do_min']} mg/L", f"{stn['bod_min']} mg/L", f"{stn['ph_min']}",
                f"{stn['total_coliform_min']} MPN", f"{stn['fecal_coliform_min']} MPN",
                f"{stn['conductivity_min']} µmho/cm", f"{stn['nitrate_min']} mg/L", f"{stn['temp_min']} °C"
            ],
            "Max Recorded": [
                f"{stn['do_max']} mg/L", f"{stn['bod_max']} mg/L", f"{stn['ph_max']}",
                f"{stn['total_coliform_max']} MPN", f"{stn['fecal_coliform_max']} MPN",
                f"{stn['conductivity_max']} µmho/cm", f"{stn['nitrate_max']} mg/L", f"{stn['temp_max']} °C"
            ],
            "CPCB / BIS Standard": [
                ">= 5.0 mg/L (Bathing)", "<= 3.0 mg/L (Bathing)", "6.5 - 8.5",
                "<= 500 MPN/100ml", "<= 500 MPN/100ml", "<= 2250 µmho/cm",
                "<= 10.0 mg/L", "Ambient"
            ]
        }
        st.table(pd.DataFrame(param_data))

        # Smart Water Purification & Treatment Recommendation
        st.markdown("---")
        with st.expander("🔬 Recommended Water Purification & Treatment Protocol / சுத்திகரிப்பு வழிகாட்டி", expanded=True):
            purif_rec = recommend_purification(
                stn.to_dict(),
                lang="ta" if "தமிழ்" in ui_lang else "en"
            )
            purif_md = format_purification_markdown(purif_rec, is_tamil=("தமிழ்" in ui_lang))

            if purif_rec.get("critical_warnings"):
                for w in purif_rec["critical_warnings"]:
                    st.error(f"🚨 {w}")

            st.markdown(purif_md)


# -------------------------------------------------------------
# TAB 4: MANUAL DATA SUBMISSION (CITIZEN SCIENCE)
# -------------------------------------------------------------
elif nav == "➕ Submit Water Sample":
    st.header("➕ Citizen Science & Field Water Sample Ingestion")
    st.markdown(
        "Manually submit water quality measurements from local field test kits, portable sensors, or laboratory reports. "
        "The system will **instantly calculate the Water Quality Index (WQI)**, assign the official **CPCB Best Use Class**, "
        "generate **Citizen Safety Advisories**, and index the sample into the **AI RAG Assistant**."
    )

    # Quick presets
    st.markdown("#### ⚡ Quick Sample Presets (Optional)")
    p1, p2, p3, p4 = st.columns(4)
    preset_data = {}
    with p1:
        if st.button("🏔️ Clean Mountain Stream"):
            preset_data = {
                "loc": "Upper Mountain Stream, Manali",
                "state": "HIMACHAL PRADESH",
                "wtype": "RIVER",
                "do": 8.5,
                "bod": 1.1,
                "ph": 7.4,
                "cond": 120.0,
                "col": 25.0,
                "nitrate": 0.4
            }
    with p2:
        if st.button("🌊 Holy Bathing Ghat"):
            preset_data = {
                "loc": "Ganga Ghat at Haridwar",
                "state": "UTTARAKHAND",
                "wtype": "RIVER",
                "do": 7.2,
                "bod": 2.2,
                "ph": 7.6,
                "cond": 280.0,
                "col": 350.0,
                "nitrate": 1.2
            }
    with p3:
        if st.button("🌾 Rural Irrigation Lake"):
            preset_data = {
                "loc": "Village Panchayat Lake, Sagar",
                "state": "MADHYA PRADESH",
                "wtype": "LAKE",
                "do": 5.2,
                "bod": 3.8,
                "ph": 8.1,
                "cond": 750.0,
                "col": 2200.0,
                "nitrate": 3.5
            }
    with p4:
        if st.button("🚨 Untreated Sewage Drain"):
            preset_data = {
                "loc": "Industrial Outfall Drain, Ludhiana",
                "state": "PUNJAB",
                "wtype": "DRAIN",
                "do": 0.5,
                "bod": 48.0,
                "ph": 6.2,
                "cond": 2400.0,
                "col": 850000.0,
                "nitrate": 12.0
            }

    if preset_data:
        st.session_state["manual_preset"] = preset_data

    active_preset = st.session_state.get("manual_preset", {})

    with st.form("manual_sample_form"):
        st.subheader("📍 Sample Location & Metadata")
        m1, m2, m3 = st.columns(3)
        with m1:
            sample_loc = st.text_input(
                "Location / Landmark Name*",
                value=active_preset.get("loc", "Community River Ghat near Temple, Varanasi"),
                placeholder="e.g. Yamuna Ghat at Mathura"
            )
        with m2:
            all_states = sorted(df['state_name'].dropna().unique().tolist()) if not df.empty else ["UTTAR PRADESH", "MADHYA PRADESH", "JHARKHAND", "DELHI"]
            def_state_idx = all_states.index(active_preset["state"]) if active_preset.get("state") in all_states else 0
            sample_state = st.selectbox("State / Union Territory*", all_states, index=def_state_idx)
        with m3:
            wtype_list = ["RIVER", "LAKE", "POND", "CANAL", "DRAIN", "BEACH", "WELL / GROUNDWATER", "STP OUTLET", "RAW WATER INTAKE"]
            def_wtype_idx = wtype_list.index(active_preset["wtype"]) if active_preset.get("wtype") in wtype_list else 0
            sample_wtype = st.selectbox("Water Body Type*", wtype_list, index=def_wtype_idx)

        st.subheader("🧪 Chemical & Biological Measurements")
        c1, c2, c3 = st.columns(3)
        with c1:
            sample_do = st.number_input(
                "Dissolved Oxygen (DO in mg/L)*",
                min_value=0.0, max_value=20.0,
                value=float(active_preset.get("do", 6.8)),
                step=0.1,
                help="Standard for Outdoor Bathing: >= 5.0 mg/L"
            )
            sample_bod = st.number_input(
                "BOD (mg/L)*",
                min_value=0.0, max_value=500.0,
                value=float(active_preset.get("bod", 2.4)),
                step=0.1,
                help="Bathing limit: <= 3.0 mg/L; Drinking source: <= 2.0 mg/L"
            )
            sample_ph = st.number_input(
                "pH Value*",
                min_value=0.0, max_value=14.0,
                value=float(active_preset.get("ph", 7.6)),
                step=0.1,
                help="Normal range: 6.5 to 8.5"
            )
        with c2:
            sample_coliform = st.number_input(
                "Total Coliform (MPN/100ml)",
                min_value=0.0, max_value=100000000.0,
                value=float(active_preset.get("col", 450.0)),
                step=10.0,
                help="Bathing limit: <= 500 MPN/100ml"
            )
            sample_fecal = st.number_input(
                "Fecal Coliform (MPN/100ml)",
                min_value=0.0, max_value=100000000.0,
                value=float(active_preset.get("col", 450.0)) * 0.4,
                step=10.0,
                help="Bathing limit: <= 500 MPN/100ml"
            )
            sample_cond = st.number_input(
                "Electrical Conductivity (µmho/cm)",
                min_value=0.0, max_value=100000.0,
                value=float(active_preset.get("cond", 350.0)),
                step=50.0,
                help="Freshwater limit: <= 2250 µmho/cm"
            )
        with c3:
            sample_nitrate = st.number_input(
                "Nitrate-N (mg/L)",
                min_value=0.0, max_value=100.0,
                value=float(active_preset.get("nitrate", 1.2)),
                step=0.1,
                help="Potable drinking limit: <= 10.0 mg/L"
            )
            sample_temp = st.number_input("Water Temperature (°C)", min_value=0.0, max_value=60.0, value=24.5, step=0.5)
            sample_year = st.number_input("Observation Year", min_value=2020, max_value=2030, value=2026)

        submitted = st.form_submit_button("🧪 Save Sample & Compute Water Safety")

    if submitted:
        if not sample_loc.strip():
            st.error("Please provide a valid location name.")
        else:
            with st.spinner("Calculating WQI & indexing into RAG memory..."):
                new_record = add_manual_sample(
                    monitoring_location=sample_loc,
                    state_name=sample_state,
                    water_body_type=sample_wtype,
                    do=sample_do,
                    bod=sample_bod,
                    ph=sample_ph,
                    conductivity=sample_cond,
                    nitrate=sample_nitrate,
                    total_coliform=sample_coliform,
                    fecal_coliform=sample_fecal,
                    temp=sample_temp,
                    year=sample_year
                )
                # Refresh RAG memory and clear Streamlit cache
                st.cache_resource.clear()
                st.cache_data.clear()
                if hasattr(agent, "reload_agent"):
                    agent.reload_agent()
                elif hasattr(agent, "rag") and hasattr(agent.rag, "reload_index"):
                    agent.rag.reload_index()

                st.success(f"✅ Sample successfully submitted! Assigned Station Code: `{new_record['stn_code']}`.")

                # Instant Scorecard
                st.markdown("### 📋 Instant Environmental & Health Scorecard")
                sc1, sc2, sc3 = st.columns(3)
                w_score = new_record['wqi_score']
                w_emoji = "🟢" if w_score >= 70 else ("🟡" if w_score >= 50 else "🔴")
                sc1.metric("Computed WQI", f"{w_emoji} {w_score}/100", new_record['wqi_status'])
                sc2.metric("CPCB Best Use Class", new_record['cpcb_class'])
                sc3.metric("Outdoor Bathing Verdict", new_record['bathing_safety'].split(":")[0])

                st.markdown("---")
                h1, h2, h3 = st.columns(3)
                with h1:
                    st.info(f"**🏊 Bathing Safety:**\n\n{new_record['bathing_safety']}")
                with h2:
                    st.warning(f"**🚰 Drinking Suitability:**\n\n{new_record['drinking_suitability']}")
                with h3:
                    st.success(f"**🐟 Aquatic Ecosystem:**\n\n{new_record['aquatic_health']}")

                st.caption(f"**Primary Environmental Concerns:** {new_record['primary_concerns']}")
                st.info(f"💡 You can now ask the AI Assistant questions about this station directly in the **💬 AI Citizen Assistant** tab (e.g., *'Is {sample_loc} safe for holy dipping?'*).")

                # Smart Water Purification Recommender for Submitted Sample
                with st.expander("🔬 Recommended Purification & Treatment Protocol / சுத்திகரிப்பு வழிகாட்டி", expanded=True):
                    sub_purif = recommend_purification(
                        new_record,
                        lang="ta" if "தமிழ்" in ui_lang else "en"
                    )
                    sub_md = format_purification_markdown(sub_purif, is_tamil=("தமிழ்" in ui_lang))
                    if sub_purif.get("critical_warnings"):
                        for w in sub_purif["critical_warnings"]:
                            st.error(f"🚨 {w}")
                    st.markdown(sub_md)

    # Display citizen-submitted samples table
    st.markdown("---")
    st.subheader("📑 Recent Citizen-Submitted Samples")
    try:
        current_df = load_data()
        manual_stns = current_df[current_df['stn_code'] >= 90000]
        if not manual_stns.empty:
            disp_cols = [
                'stn_code', 'monitoring_location', 'state_name', 'water_body_type',
                'wqi_score', 'wqi_status', 'cpcb_class', 'bathing_safety', 'bod_mean', 'do_mean', 'total_coliform_mean'
            ]
            st.dataframe(manual_stns[disp_cols], use_container_width=True)
        else:
            st.caption("No manual samples submitted yet in this session. Submit your first sample above!")
    except Exception as e:
        st.caption("No manual samples recorded yet.")


# -------------------------------------------------------------
# TAB 5: GRIEVANCE GENERATOR
# -------------------------------------------------------------
elif nav == "📑 Grievance Generator":
    st.header("📑 Citizen Grievance & Regulatory Petition Generator")
    st.markdown(
        "Empowering citizens and civil society organizations to file formal legal petitions under the "
        "**Water (Prevention and Control of Pollution) Act, 1974** with State Pollution Control Boards."
    )

    if not df.empty:
        # Show polluted stations by default
        polluted_options = df[df['cpcb_class'].str.contains('Below Class E|Class D', na=False)]
        if polluted_options.empty:
            polluted_options = df

        stn_list = [f"{row['stn_code']} - {row['monitoring_location']} ({row['state_name']})" for _, row in polluted_options.iterrows()]
        selected = st.selectbox("Select Contaminated Station to Report", stn_list)
        selected_code = int(selected.split(" - ")[0])
        stn_dict = df[df['stn_code'] == selected_code].iloc[0].to_dict()

        if st.button("Generate Legal Grievance Petition"):
            letter_text = agent.tool_draft_grievance_letter(stn_dict)
            st.text_area("Official Grievance Document", letter_text, height=450)
            st.download_button(
                label="📥 Download Complaint Letter (.txt)",
                data=letter_text,
                file_name=f"SPCB_Grievance_STN_{selected_code}.txt",
                mime="text/plain"
            )


# -------------------------------------------------------------
# TAB 5: STANDARDS & GUIDELINES
# -------------------------------------------------------------
elif nav == "📖 Standards & Guides":
    st.header("📖 CPCB & BIS Water Quality Guidelines Reference")
    st.markdown("Official regulatory benchmarks utilized by the Assistant to evaluate water safety.")

    t1, t2, t3, t4 = st.tabs([
        "CPCB Designated Best Use",
        "BIS 10500 Potable Standards",
        "Health Hazard Guidelines",
        "Purification Protocols / சுத்திகரிப்பு"
    ])

    with t1:
        st.markdown("""
        ### CPCB Water Quality Criteria for Inland Surface Waters
        - **Class A**: Drinking water source without conventional treatment but after disinfection (DO $\ge 6$, BOD $\le 2$, Total Coliform $\le 50$)
        - **Class B**: Outdoor bathing (organized) (DO $\ge 5$, BOD $\le 3$, Total Coliform $\le 500$)
        - **Class C**: Drinking water source after conventional treatment (DO $\ge 4$, BOD $\le 3$, Total Coliform $\le 5000$)
        - **Class D**: Propagation of Wildlife and Fisheries (DO $\ge 4$, pH 6.5 - 8.5)
        - **Class E**: Irrigation, Industrial cooling (Conductivity $\le 2250$ µmho/cm, pH 6.0 - 8.5)
        - **Below Class E**: Severely Polluted / Non-Compliant (Unfit for human contact or consumption)
        """)

    with t2:
        st.markdown("""
        ### Bureau of Indian Standards (BIS 10500:2012) Potable Water Norms
        - **Total Coliform & E. coli**: Must be **0 MPN/100ml** (Absent in all potable supplies).
        - **Nitrate (as NO3)**: Maximum permissible limit is **45 mg/L** (~10 mg/L as Nitrate-N). High levels cause infant methemoglobinemia.
        - **pH Range**: 6.5 to 8.5.
        - **Total Dissolved Solids (TDS)**: Desirable $\le 500$ mg/L, Max permissible $\le 2000$ mg/L.
        """)

    with t3:
        st.markdown("""
        ### Waterborne Health Hazards & Pathogens
        - **Coliforms & Fecal Streptococci**: Indicators of untreated human or animal sewage. Ingestion causes acute gastroenteritis, cholera, typhoid fever, and hepatitis.
        - **Biochemical Oxygen Demand (BOD)**: Indicates heavy organic dumping. High BOD consumes dissolved oxygen, suffocates fish, and fosters pathogenic bacterial blooms.
        - **Hypoxia (Low DO < 4 mg/L)**: Converts water bodies into septic zones emitting hydrogen sulfide ($H_2S$) and methane.
        """)

    with t4:
        st.markdown("""
        ### 🔬 Multi-Barrier Water Purification Protocols & Guidelines
        
        #### 1. Household Multi-Barrier Sequence:
        1. **Sediment Pre-Filtration**: 5-micron spun polypropylene or clean multi-layer cotton cloth to trap silt, rust, and macro-particles.
        2. **Coagulation / Flocculation**: Using alum (Fitkari / படிகாரம்) @ 10–30 mg/L for turbid surface waters, followed by 30-minute settling.
        3. **Granular Activated Carbon (GAC)**: Adsorbs pesticides, toxic organics, bad odors, chlorine residuals, and micro-pollutants.
        4. **Microbial Disinfection**:
           - **Vigorous Boiling**: $\ge 1-3$ minutes kills viruses, bacteria, and protozoan cysts (*Giardia*, *Cryptosporidium*).
           - **Ultraviolet (UV)**: 254 nm germicidal wavelength inactivates pathogens without chemical byproducts.
           - **Chlorination**: Halazone / sodium hypochlorite (0.2–0.5 mg/L residual).
        5. **Reverse Osmosis (RO)**: Required if TDS $> 500$ mg/L, heavy metals, or excessive nitrates are present.

        #### 🚨 Critical Nitrate Hazard & Boiling Contraindication:
        > **NEVER boil water with high nitrate levels ($> 10$ mg/L Nitrate-N) for infant formula or pregnant women.**
        > Boiling evaporates pure water and concentrates nitrate ions, drastically escalating the risk of **Methemoglobinemia ("Blue Baby Syndrome")**, which suffocates infant tissue oxygenation.
        > Nitrates can ONLY be removed via **Reverse Osmosis (RO)** or **Strong Base Anion Ion-Exchange Resins**.
        """)

