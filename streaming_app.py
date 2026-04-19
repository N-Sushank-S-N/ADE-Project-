import streamlit as st
import requests

# Set page to wide mode for a better streaming layout
st.set_page_config(page_title="PandaStream", layout="wide", page_icon="🍿")

# --- STATE MANAGEMENT (LOGIN LOGIC) ---
if "stream_logged_in" not in st.session_state:
    st.session_state.stream_logged_in = False
if "stream_user" not in st.session_state:
    st.session_state.stream_user = ""

# --- UI CSS ---
st.markdown("""
    <style>
    /* Dark mode background */
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Style the movie titles */
    h3 { font-size: 1.2rem !important; margin-bottom: 0px !important; }
    p { color: #8b949e; font-size: 0.9rem; }
    
    /* Make the images look like real movie posters with rounded corners */
    img { border-radius: 8px; }
    
    /* Style the login box */
    [data-testid="stForm"] { background-color: #161b22; border-radius: 12px; border: 1px solid #30363d; padding: 30px; }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# PAGE 1: WHO IS WATCHING? (Login)
# ==========================================
if not st.session_state.stream_logged_in:
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🍿 PandaStream</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Who's watching today?</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Profile Name", placeholder="e.g., sushank")
            submitted = st.form_submit_button("Enter Matrix", use_container_width=True)
            
            if submitted and username:
                st.session_state.stream_logged_in = True
                st.session_state.stream_user = username
                st.rerun()

# ==========================================
# PAGE 2: MAIN STREAMING INTERFACE
# ==========================================
else:
    user_id = st.session_state.stream_user
    
    # Header with Logout Button
    h1, h2 = st.columns([5, 1])
    with h1:
        st.title("🍿 PandaStream")
    with h2:
        st.write("") # Spacing
        if st.button("🚪 Change Profile", use_container_width=True):
            st.session_state.stream_logged_in = False
            st.rerun()

    st.divider()
    
    # --- 1. ASK THE ENGINE FOR RECOMMENDATIONS ---
    st.subheader(f"✨ Recommended for {user_id.title()}")
    st.caption("Powered by your ABDEE real-time behavioral engine")
    
    try:
        res = requests.get(f"http://127.0.0.1:8000/active_features?user_id={user_id}")
        if res.status_code == 200:
            data = res.json().get("active_features", [])
            if data:
                # Sort features by highest score
                sorted_data = sorted(data, key=lambda x: x['score'], reverse=True)
                
                # Show the top recommendations
                rec_cols = st.columns(min(len(sorted_data), 4)) 
                for idx, feature in enumerate(sorted_data[:4]):
                    with rec_cols[idx]:
                        match_pct = int(feature['score'] * 100)
                        st.success(f"⭐ **{feature['feature_id'].replace('_', ' ').title()}** ({match_pct}% Match)")
            else:
                st.info("No watch history found! Click 'Like' on some movies below to train your algorithm.")
    except Exception as e:
        st.error("Recommendation Engine Offline. Is FastAPI running?")

    st.divider()

    # --- 2. THE MOVIE CATALOG ---
    st.subheader("🎬 Trending Now")
    
    movies = [
        {
            "id": "sci_fi_movies", 
            "title": "Interstellar Journey", 
            "image": "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=600&q=80",
            "desc": "Explore the unknown reaches of the galaxy."
        },
        {
            "id": "action_movies", 
            "title": "Explosion Protocol", 
            "image": "https://images.unsplash.com/photo-1508614589041-895b88991e3e?w=600&q=80",
            "desc": "High-octane thrills and non-stop action."
        },
        {
            "id": "documentary", 
            "title": "Planet Earth Secrets", 
            "image": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600&q=80", 
            "desc": "Discover the hidden wonders of nature."
        },
        {
            "id": "comedy_specials", 
            "title": "Standup Night", 
            "image": "https://images.unsplash.com/photo-1585647347384-2593bc35786b?w=600&q=80",
            "desc": "Grab some popcorn and laugh out loud."
        }
    ]
    
    # Create a 4-column grid for the movies
    cols = st.columns(4)
    
    for idx, movie in enumerate(movies):
        with cols[idx]:
            # Load the movie poster
            st.image(movie["image"], use_container_width=True)
            st.markdown(f"### {movie['title']}")
            st.markdown(f"<p>{movie['desc']}</p>", unsafe_allow_html=True)
            
            # Dual Action Buttons!
            btn1, btn2 = st.columns(2)
            
            with btn1:
                # REINFORCEMENT (Boost Score)
                if st.button("👍 Like", key=f"like_{movie['id']}", use_container_width=True):
                    try:
                        res = requests.post("http://127.0.0.1:8000/add_event", 
                                      json={"user_id": user_id, "feature_id": movie['id'], "weight": 1.0})
                        if res.status_code == 200:
                            st.toast(f"✅ Liked {movie['title']}! Engine updated.")
                            st.rerun()
                    except requests.exceptions.ConnectionError:
                        st.error("🚨 Backend Offline.")

            with btn2:
                # PENALTY / SUPPRESSION (Crush Score via ML Loop)
                if st.button("👎 Pass", key=f"pass_{movie['id']}", use_container_width=True):
                    try:
                        res = requests.post("http://127.0.0.1:8000/feedback", 
                                      json={"user_id": user_id, "feature_id": movie['id'], "action": "ignore"})
                        
                        if res.status_code == 200:
                            data = res.json()
                            if data.get("status") == "not found":
                                st.toast("Got it! We'll keep this out of your recommendations.")
                            else:
                                st.toast(f"❌ Passed on {movie['title']}! Decay rate accelerated.")
                                st.rerun()
                    except requests.exceptions.ConnectionError:
                        st.error("🚨 Backend Offline.")