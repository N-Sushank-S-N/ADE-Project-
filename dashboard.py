import streamlit as st
import requests
import pandas as pd
import altair as alt
import numpy as np

# Force Wide mode for the dashboard
st.set_page_config(page_title="ABDEE Admin", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# SESSION STATE (LOGIN LOGIC)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# ==========================================
# PAGE 1: LOGIN SCREEN (Dark Theme)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; }
        [data-testid="stForm"] { background-color: #161b22; border-radius: 16px; border: 1px solid #30363d; padding: 30px; }
        [data-testid="stFormSubmitButton"] button { background: linear-gradient(90deg, #4F8BFF 0%, #1e5fe3 100%); color: white; width: 100%; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; color: white;'>🐼 ABDEE Platform</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Admin Username", placeholder="e.g., sushank")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Secure Login")
            if submitted and username:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun() 

# ==========================================
# PAGE 2: MAIN DASHBOARD (SaaS Light Theme)
# ==========================================
else:
    # --- SAAS UI CSS INJECTION ---
    st.markdown("""
        <style>
        /* Light background for the main dashboard area */
        .stApp { background-color: #F8FAFC !important; }
        
        /* Clean white sidebar */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
        }
        
        /* Elevated Metric Cards */
        [data-testid="metric-container"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }
        
        /* Color the Engage/Ignore Buttons */
        div[data-testid="column"]:nth-of-type(1) button { background-color: #17B169; color: white; }
        div[data-testid="column"]:nth-of-type(2) button { background-color: #FF4B4B; color: white; }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 👤 Admin: **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
        
    st.sidebar.divider()
    content_categories = ["sci_fi_movies", "documentary", "action_movies", "comedy_specials"]

    st.sidebar.markdown("#### 📥 Manual Data Injection")
    with st.sidebar.form("event_form", border=False):
        new_feature = st.selectbox("Select Content Type", content_categories)
        if st.form_submit_button("Inject Data", use_container_width=True):
            requests.post("http://127.0.0.1:8000/add_event", json={"user_id": st.session_state.username, "feature_id": new_feature, "weight": 1.0})

    st.sidebar.markdown("#### 🤖 Train the AI Engine")
    with st.sidebar.form("feedback_form", border=False):
        train_feature = st.selectbox("Target Content", content_categories)
        colA, colB = st.columns(2)
        with colA:
            if st.form_submit_button("👍 Engage"):
                requests.post("http://127.0.0.1:8000/feedback", json={"user_id": st.session_state.username, "feature_id": train_feature, "action": "engage"})
        with colB:
            if st.form_submit_button("👎 Ignore"):
                requests.post("http://127.0.0.1:8000/feedback", json={"user_id": st.session_state.username, "feature_id": train_feature, "action": "ignore"})

    # --- MAIN PAGE ---
    colA, colB = st.columns([4, 1])
    with colA:
        st.markdown("<h2>🧠 Data Control Center</h2>", unsafe_allow_html=True)
    with colB:
        fetch_btn = st.button("🔄 Refresh Real-Time Data", use_container_width=True)

    try:
        response = requests.get(f"http://127.0.0.1:8000/active_features?user_id={st.session_state.username}")
        if response.status_code == 200:
            features = response.json().get("active_features", [])
            
            if features:
                df = pd.DataFrame(features)
                
                # Metrics Row
                m1, m2, m3 = st.columns(3)
                m1.metric("Active Content Nodes", len(features))
                m2.metric("Highest User Affinity", round(df['score'].max(), 3))
                fastest_decay = df.loc[df['decay_multiplier'].idxmax()]['feature_id']
                m3.metric("Highest Flight Risk", fastest_decay)
                
                st.write("") # Spacing
                
                # Charts Row
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("#### Feature Dominance (Current Interest)")
                    chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                        x=alt.X('feature_id', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('score', scale=alt.Scale(domain=[0, 1.2])),
                        color=alt.value("#4F8BFF") 
                    )
                    st.altair_chart(chart, use_container_width=True)
                    
                with c2:
                    st.markdown("#### Engine Confidence (Decay Multiplier)")
                    mem_chart = alt.Chart(df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                        x=alt.X('feature_id', axis=alt.Axis(labelAngle=0)),
                        y='decay_multiplier',
                        color=alt.value("#FF4B4B") 
                    )
                    st.altair_chart(mem_chart, use_container_width=True)

                # --- Predictive Forecast Chart ---
                st.divider()
                st.markdown("#### 📈 Predictive Expiry Forecast (Next 30 Days)")

                future_days = 30
                seconds_per_day = 86400
                base_lambda = 0.000005 
                expiry_threshold = 0.05
                projection_data = []

                for index, row in df.iterrows():
                    dynamic_lambda = base_lambda * row['decay_multiplier']
                    for day in range(future_days + 1):
                        future_score = row['score'] * np.exp(-dynamic_lambda * (day * seconds_per_day))
                        projection_data.append({"feature_id": row['feature_id'], "day": day, "projected_score": future_score})

                proj_df = pd.DataFrame(projection_data)
                
                line_chart = alt.Chart(proj_df).mark_line(interpolate='monotone').encode(
                    x=alt.X('day:Q', title="Days from Now"),
                    y=alt.Y('projected_score:Q', title="Predicted Score", scale=alt.Scale(domain=[0, 1.2])),
                    color=alt.Color('feature_id:N', legend=alt.Legend(title="Features")),
                    tooltip=['feature_id', 'day', 'projected_score']
                )

                threshold_rule = alt.Chart(pd.DataFrame({'y': [expiry_threshold]})).mark_rule(
                    strokeDash=[5, 5], color='#FF4B4B', strokeWidth=2
                ).encode(y='y:Q')

                st.altair_chart(line_chart + threshold_rule, use_container_width=True)
                
            else:
                st.info(f"No database records found for {st.session_state.username}. Use the Streaming App to generate data!")
    except Exception as e:
        st.error("🚨 Backend disconnected. Ensure Uvicorn is running.")