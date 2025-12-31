import streamlit as st
import streamlit.components.v1 as components
import textwrap
import time
from agent.travel_agent import TravelAgent
from datetime import date

from datetime import datetime
from datetime import timedelta
from agent.llm_loader import preload_local_models


# SESSION STATE
if "app_ready" not in st.session_state:
    st.session_state.app_ready = False
    
if "show_itinerary" not in st.session_state:
    st.session_state.show_itinerary = False

if "itinerary_typed" not in st.session_state:
    st.session_state.itinerary_typed = False
    
if "itinerary_closing" not in st.session_state:
    st.session_state.itinerary_closing = False

if "show_input" not in st.session_state:
    st.session_state.show_input = True

if "agent" not in st.session_state:
    st.session_state.agent = TravelAgent()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "final_result" not in st.session_state:
    st.session_state.final_result = None

if "thinking" not in st.session_state:
    st.session_state.thinking = False

if "active_mode" not in st.session_state:
    st.session_state.active_mode = "chat"
    
if "result_mode" not in st.session_state:
    st.session_state.result_mode = None
    
if "debug" not in st.session_state:
    st.session_state.debug = True
    
if "chat_result" not in st.session_state:
    st.session_state.chat_result = None

if "form_result" not in st.session_state:
    st.session_state.form_result = None
    
if "chat_locked" not in st.session_state:
    st.session_state.chat_locked = False
    
    
# 🔥 Load local models ONCE per server
preload_local_models()

# PAGE CONFIG
st.set_page_config(
    page_title="AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded" 
)


if not st.session_state.app_ready:
    st.markdown(
        """
        <div id="app-skeleton">
            <div class="splash-skeleton">
                <div class="splash-card"></div>
                <div class="splash-card"></div>
                <div class="splash-card"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    time.sleep(3)

    # trigger fade-out
    st.markdown(
        """
        <style>
        #app-skeleton {
            animation: splashFadeOut 0.6s ease-in forwards;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    time.sleep(0.6)

    st.session_state.app_ready = True
    st.rerun()


# GLOBAL STYLES (iOS Glass UI)
def load_css(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("assets/styles.css")

# WEATHER ICON HELPER
def weather_icon(condition: str) -> str:
    c = condition.lower()
    if "sun" in c or "clear" in c:
        return "☀️"
    if "cloud" in c:
        return "☁️"
    if "rain" in c or "storm" in c:
        return "🌧️"
    if "snow" in c:
        return "❄️"
    return "🌤️"

# STREAMING TEXT
def stream_text(text: str, delay: float = 0.03):
    placeholder = st.empty()
    streamed = ""
    for word in text.split():
        streamed += word + " "
        placeholder.markdown(
            f'<div class="chat-bubble assistant">{streamed}<span style="opacity:0.5">▍</span></div>',
            unsafe_allow_html=True
        )
        time.sleep(delay)
    placeholder.markdown(
        f'<div class="chat-bubble assistant">{streamed}</div>',
        unsafe_allow_html=True
    )
    
st.markdown('<div class="app-content">', unsafe_allow_html=True)


# HEADER

st.markdown("""
<div style="text-align:center; padding:20px;">
<h1>✈️ AI Travel Planner</h1>
<p class="glass-sub">ChatGPT-style trip planning with intelligence</p>
</div>
""", unsafe_allow_html=True)

tab_chat, tab_form = st.tabs(["CHAT MODE", "FORM MODE"])


# SIDEBAR
with st.sidebar:

    # SIDEBAR HEADER
    st.markdown("## ✈️ AI Travel Planner")
    st.caption("Smart trip planning assistant")

    st.divider()
    
    # NEW TRIP
    if st.button("➕ Start New Trip", use_container_width=True):
        st.session_state.messages = []
        st.session_state.final_result = None
        st.session_state.show_input = True
        st.session_state.show_itinerary = False
        st.session_state.itinerary_typed = False
        st.session_state.itinerary_closing = False
        st.session_state.agent = TravelAgent()
        st.rerun()

    st.divider()

    # MODEL CONTROLS
    st.markdown("### ⚙️ Model Settings")

    if "model_mode" not in st.session_state:
        st.session_state.model_mode = "Auto"

    if "local_model_choice" not in st.session_state:
        st.session_state.local_model_choice = "phi"

    model_mode = st.radio(
        "Inference Mode",
        ["Auto (API → Local)", "Use Local Model"],
        index=0 if st.session_state.model_mode == "Auto" else 1,
    )

    st.session_state.model_mode = "Auto" if model_mode.startswith("Auto") else "Local"

    # Local model selector
    if st.session_state.model_mode == "Local":
        choice = st.selectbox(
            "Local Model",
            options=[("Phi-3 Mini (Fast)", "phi"), ("Qwen 2.5 3B (Reasoning)", "qwen")],
            format_func=lambda x: x[0],
            index=0 if st.session_state.local_model_choice == "phi" else 1,
        )
        st.session_state.local_model_choice = choice[1]

    # Apply model
    if st.button("Apply Model", use_container_width=True):
        with st.spinner("Switching model…"):
            #  Reset agent
            st.session_state.agent = TravelAgent(
                force_local=(st.session_state.model_mode == "Local"),
                local_model_choice=st.session_state.local_model_choice,
            )

            # 🧹 Clear chat state
            st.session_state.messages = []
            st.session_state.show_input = True
            st.session_state.thinking = False

            # 🧹 Clear BOTH outputs
            st.session_state.chat_result = None
            st.session_state.form_result = None

            # 🧹 Reset itinerary UI
            st.session_state.show_itinerary = False
            st.session_state.itinerary_typed = False
            st.session_state.itinerary_closing = False

            st.success("Model updated")
            st.rerun()

    st.divider()

    # ACTIVE MODEL STATUS (CLEAN)
    st.markdown("### 🚀 Active Runtime Model:")

    agent = st.session_state.agent

    if agent.model_provider == "HuggingFace":
        st.success(f"🟢 API Connected\n\n**{agent.model_name}**")
    else:
        st.warning(f"🟡 Local Model\n\n**{agent.model_name}**")

    st.divider()
    
    st.markdown("### 🧩 System Status")

    preload = preload_local_models()
    sys = preload["system_status"]
    agent = st.session_state.agent


    # HuggingFace API
    if agent.model_provider == "HuggingFace":
        st.success("🌐 HuggingFace API connected")
    else:
        st.warning("🌐 HuggingFace API not connected")

    st.divider()

    # Local Models
    if sys.get("phi_loaded"):
        st.success("Phi-3 Mini loaded successfully")
    else:
        st.error("Phi-3 Mini failed to load")

    if sys.get("qwen_loaded"):
        st.success("Qwen 2.5 loaded successfully")
    else:
        st.error("Qwen 2.5 failed to load")

    st.divider()



def section_loader(text, delay=2):
    placeholder = st.empty()

    placeholder.markdown(
        f"""
        <div class="section-loader">
            <div class="spinner"></div>
            <div class="loader-text">{text}</div>
        </div>

        <style>
        .section-loader {{
            display:flex;
            align-items:center;
            gap:16px;
            padding:16px 20px;
            border-radius:16px;
            background:rgba(255,255,255,0.06);
            margin:10px 0 10px;
        }}

        .spinner {{
            width:26px;
            height:26px;
            border:3px solid rgba(255,255,255,0.25);
            border-top:3px solid #ffffff;
            border-radius:50%;
            animation: spin 0.9s linear infinite;
        }}

        .loader-text {{
            font-size:18px;
            font-weight:700;
            color:white;
            letter-spacing:0.2px;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    time.sleep(delay)
    placeholder.empty()



def render_full_trip_ui(result):
    if not result:
        return

    plan = result["TRIP_PLAN"]
    intent = result["FINAL_INTENT_JSON"]

    # Trip Overview
    section_loader("🔍 Understanding your trip preferences…")
    st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
    st.markdown("## 🧳 Trip Overview")
    c1, c2, c3 = st.columns(3)

    c1.markdown(f"""
    <div class="glass-card">
    <div class="glass-title">Route</div>
    <div class="metric-big">{intent['source']} → {intent['destination']}</div>
    <div class="glass-sub">{intent['trip_type'].replace('_',' ').title()}</div>
    </div>
    """, unsafe_allow_html=True)

    c2.markdown(f"""
    <div class="glass-card">
    <div class="glass-title">Duration</div>
    <div class="metric-big">{intent['days']} Days</div>
    <div class="glass-sub">{max(intent['days']-1,1)} Nights</div>
    </div>
    """, unsafe_allow_html=True)

    c3.markdown(f"""
    <div class="glass-card">
    <div class="glass-title">Travelers</div>
    <div class="metric-big">{intent['travelers']}</div>
    <div class="glass-sub">People</div>
    </div>
    """, unsafe_allow_html=True)
    
    from datetime import datetime

    def format_date_day(d):
        try:
            dt = datetime.fromisoformat(d)
            return dt.strftime("%b %d, %Y"), dt.strftime("%A")
        except:
            return "—", "—"

    start = datetime.fromisoformat(intent["travel_date"])
    end = start + timedelta(days=intent["days"] - 1)

    c4, c5 = st.columns(2)

    c4.markdown(f"""
        <div class="glass-card">
            <div class="glass-title">Trip Start</div>
            <div class="metric-big">{start.strftime("%d %b %Y")}</div>
            <div class="glass-sub">{start.strftime("%A")}</div>
        </div>
        """, unsafe_allow_html=True)

    c5.markdown(f"""
    <div class="glass-card">
        <div class="glass-title">Trip End</div>
        <div class="metric-big">{end.strftime("%d %b %Y")}</div>
        <div class="glass-sub">{end.strftime("%A")}</div>
    </div>
    """, unsafe_allow_html=True)

    
    # AIRPORT CODE (SAFE)

    def airport_code(city):
        if not city:
            return "—"

        codes = {
            "mumbai": "BOM",
            "goa": "GOI",
            "delhi": "DEL",
            "bangalore": "BLR",
            "chennai": "MAA",
            "hyderabad": "HYD",
            "kolkata": "CCU"
        }
        city_lower = str(city).lower()
        return codes.get(city_lower, city_lower[:3].upper())


    # TIME ICON (SAFE)
    def time_icon(time_str):
        try:
            # Expected: "15 Jul 2025, 14:38"
            hour_part = time_str.split(",")[-1].strip().split(":")[0]
            hour = int(hour_part)

            if 5 <= hour < 12:
                return "🌅"
            if 12 <= hour < 18:
                return "☀️"
            if 18 <= hour < 22:
                return "🌆"
            return "🌙"
        except Exception:
            return "⏰"


    # FLIGHT CARD
    def render_flight_card(title, flight):
        if not flight:
            return

        # ---------- BADGES ----------
        badges = ""
        if flight.get("is_cheapest"):
            badges += "<span class='flight-badge badge-cheapest'>🟢 Cheapest</span>"
        if flight.get("is_fastest"):
            badges += "<span class='flight-badge badge-fastest'>⚡ Fastest</span>"

        # ---------- ICONS ----------
        dep_icon = time_icon(flight.get("departure_time", ""))
        arr_icon = time_icon(flight.get("arrival_time", ""))

        from_city = flight.get("from", "—")
        to_city = flight.get("to", "—")
        from_code = airport_code(from_city)
        to_code = airport_code(to_city)

        # ---------- TIME BLOCK (SEPARATE & CLEAN) ----------
        time_block = f"""
        <div style="
            display:grid;
            grid-template-columns: 1fr 1fr;
            gap:16px;
            padding:16px;
            border-radius:16px;
            background:rgba(255,255,255,0.06);
            color:white;
        ">
            <div>
                <div class="glass-sub">
                    {dep_icon} Departure(Date/Time)
                </div>
                <div style="font-size:16px; font-weight:600;">
                    {flight.get('departure_time','—')}
                </div>
            </div>

            <div style="text-align:right;">
                <div class="glass-sub">
                    {arr_icon} Arrival(Date/Time)
                </div>
                <div style="font-size:16px; font-weight:600;">
                    {flight.get('arrival_time','—')}
                </div>
            </div>
        </div>
        """

        # ---------- MAIN HTML ----------
        html = f"""
        <div class="glass-card">

            <div class="glass-title">{title}</div>

            <!-- ROW 1 -->
            <div style="display:flex; gap:14px; margin-bottom:18px;">

                <div style="flex:2; padding:16px; border-radius:16px;
                            background:rgba(255,255,255,0.06); color:white;">
                    <div style="font-size:18px; font-weight:700;">
                        {flight.get('flight_id','—')}
                    </div>
                    <div class="glass-sub">{flight.get('airline','')}</div>
                    <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                        {badges}
                    </div>
                </div>

                <div style="flex:1; padding:16px; border-radius:16px;
                            background:rgba(255,255,255,0.06);
                            color:white; text-align:right;">
                    <div class="glass-sub">Price</div>
                    <div style="font-size:22px; font-weight:800;">
                        ₹ {flight.get('price','—')}
                    </div>

                    <div class="glass-sub" style="margin-top:10px;">Duration</div>
                    <div style="font-weight:600;">
                        ⏱ {flight.get('duration','')}
                    </div>
                </div>
            </div>

            <!-- ROUTE -->
            <div style="padding:16px; border-radius:16px;
                        background:rgba(255,255,255,0.06);
                        display:flex; justify-content:space-between;
                        align-items:center; margin-bottom:18px;
                        color:white;">
                <div>
                    <div class="glass-sub">From</div>
                    <div style="font-size:16px; font-weight:700;">
                        {from_city} ({from_code})
                    </div>
                </div>

                <div style="font-size:22px; opacity:0.6;">→</div>

                <div style="text-align:right;">
                    <div class="glass-sub">To</div>
                    <div style="font-size:16px; font-weight:700;">
                        {to_city} ({to_code})
                    </div>
                </div>
            </div>

            <!-- TIME -->
            {time_block}

        </div>     
        """



        components.html(
        f"""
        <style>
        body {{
            margin: 0;
            padding: 0;
        }}
        </style>
        {html}
        """,
        height=340,   # adjust once, then forget
        scrolling=False
    )
    def replace_date(original_datetime: str, new_date: str):
        try:
            old_dt = datetime.strptime(original_datetime, "%d %b %Y, %H:%M")
            new_dt = datetime.strptime(new_date, "%Y-%m-%d")

            final_dt = old_dt.replace(
                year=new_dt.year,
                month=new_dt.month,
                day=new_dt.day
            )
            return final_dt.strftime("%d %b %Y, %H:%M")
        except Exception:
            return original_datetime
      

    section_loader("✈️ Fetching best flight options…")
    st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
    st.markdown("## ✈️ Flights")

    # -------------------------------------------------
    # Calculate trip dates
    # -------------------------------------------------
    travel_date = intent["travel_date"]
    days = intent["days"]

    start_date = travel_date
    end_date = (
        datetime.fromisoformat(travel_date)
        + timedelta(days=days - 1)
    ).strftime("%Y-%m-%d")

    # -------------------------------------------------
    # TITLES
    # -------------------------------------------------
    if intent["trip_type"] == "round_trip":
        t1, t2 = st.columns(2)

        t1.markdown(
            "<div class='flight-column-title'>🛫 Onbording Flight</div>",
            unsafe_allow_html=True
        )
        t2.markdown(
            "<div class='flight-column-title'>🛬 Return Flight</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div class='flight-column-title'>🛫 Onbording Flight</div>",
            unsafe_allow_html=True
        )

    # -------------------------------------------------
    # FLIGHT CARDS
    # -------------------------------------------------
    if intent["trip_type"] == "round_trip":
        cols = st.columns(2)
    else:
        cols = st.columns(1)

    # ======================
    # OUTBOUND
    # ======================
    outbound = plan["FLIGHT"].get("outbound")

    if isinstance(outbound, dict):
        outbound = outbound.copy()

        outbound["departure_time"] = replace_date(
            outbound.get("departure_time", ""),
            start_date
        )
        outbound["arrival_time"] = replace_date(
            outbound.get("arrival_time", ""),
            start_date
        )

        with cols[0]:
            render_flight_card("", outbound)

    # ======================
    # RETURN (ONLY ROUND TRIP)
    # ======================
    if intent["trip_type"] == "round_trip":
        return_flight = plan["FLIGHT"].get("return")

        if isinstance(return_flight, dict) and return_flight.get("flight_id"):
            return_flight = return_flight.copy()

            return_flight["departure_time"] = replace_date(
                return_flight.get("departure_time", ""),
                end_date
            )
            return_flight["arrival_time"] = replace_date(
                return_flight.get("arrival_time", ""),
                end_date
            )

            with cols[1]:
                render_flight_card("", return_flight)

    # ===============================
    # 🏨 HOTEL (IMPROVED)
    # ===============================
    section_loader("🏨 Finding the best hotel for your stay…")
    st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
    st.markdown("## 🏨 Hotel")

    hotel = plan.get("HOTEL", {})

    def amenity_icon(name):
        icons = {
            "wifi": "📶",
            "parking": "🅿️",
            "breakfast": "🍳",
            "pool": "🏊",
            "gym": "🏋️",
            "spa": "💆",
            "restaurant": "🍽️"
        }
        return icons.get(name.lower(), "✔️")

    badges = ""
    if hotel.get("is_cheapest"):
        badges += "<span class='hotel-badge badge-cheapest'>🟢 Cheapest</span>"
    if hotel.get("is_best_rated"):
        badges += "<span class='hotel-badge badge-best'>⭐ Best Rated</span>"

    amenities_html = ""
    for a in hotel.get("amenities", []):
        amenities_html += f"""
        <div class="amenity-pill">
            <span class="amenity-icon">{amenity_icon(a)}</span>
            <span>{a.title()}</span>
        </div>
        """

    hotel_html = f"""
    <div class="glass-card">

        <!-- TOP HERO CARD -->
        <div class="hotel-hero-card">

            <div style="display:flex; justify-content:space-between; align-items:flex-start;">

                <div>
                    <div style="font-size:22px; font-weight:800; color:white;">
                        {hotel.get('name','—')}
                    </div>

                    <div style="margin-top:10px; display:flex; gap:8px; flex-wrap:wrap;">
                        {badges}
                    </div>
                </div>

                <div style="text-align:right; color:white;">
                    <div class="glass-sub">Price / Night</div>
                    <div style="font-size:26px; font-weight:900; color:white;">
                        ₹ {hotel.get('price_per_night','—')}
                    </div>
                </div>

            </div>
        </div>

        <!-- INFO CARDS -->
        <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin-bottom:18px;">

            <div class="mini-card">
                <div class="glass-sub">Hotel ID</div>
                <div class="mini-value">{hotel.get('hotel_id','—')}</div>
            </div>

            <div class="mini-card">
                <div class="glass-sub">Stars</div>
                <div class="mini-value">⭐ {hotel.get('stars','—')}</div>
            </div>

            <div class="mini-card">
                <div class="glass-sub">Location</div>
                <div class="mini-value">{hotel.get('city','—')}</div>
            </div>

        </div>

        <!-- AMENITIES -->
        <div>
            <div class="amenities-wrapper">
                {amenities_html}
            </div>
        </div>

    </div>
    <style>
    /* HERO CARD */
    .hotel-hero-card {{
        padding:18px;
        border-radius:18px;
        background:rgba(255,255,255,0.08);
        margin-bottom:18px;
        transition: all 0.3s ease;
    }}
    
    .hotel-hero-card:hover,
    .mini-card:hover,
    .amenity-pill:hover{{
    transform: translateY(-4px) scale(1.01);
    box-shadow: 0 20px 40px rgba(0,0,0,0.35);
}}

    /* BADGES */
    .hotel-badge {{
        padding:6px 14px;
        border-radius:999px;
        font-size:12px;
        font-weight:700;
        background:rgba(255,255,255,0.12);
    }}

    .badge-cheapest {{
        background:rgba(0,255,140,0.22);
        color:#4cffb0;
    }}

    .badge-best {{
        background:rgba(255,215,0,0.22);
        color:#ffd700;
    }}

    /* INFO MINI CARDS */
    .mini-card {{
        padding:14px;
        border-radius:14px;
        background:rgba(255,255,255,0.06);
        color:white;
        transition: all 0.3s ease;
    }}

    .mini-value {{
        margin-top:6px;
        font-size:16px;
        font-weight:700;
    }}

    /* AMENITIES */
    .amenities-wrapper {{
        display:flex;
        gap:12px;
        flex-wrap:wrap;
        padding:14px;
        border-radius:16px;
        background:transparent;
    }}

    .amenity-pill {{
        display:flex;
        align-items:center;
        gap:8px;
        padding:10px 16px;
        border-radius:999px;
        background:rgba(0,160,255,0.18);
        border:1px solid rgba(0,160,255,0.35);
        font-size:13px;
        font-weight:600;
        color:white;
        transition: all 0.3s ease;
    }}

    .amenity-icon {{
        font-size:16px;
    }}
    </style>

    """


    components.html(
    f"""
    <style>
    body {{
        margin: 0;
        padding: 0;
    }}
    </style>
    {hotel_html}
    """,
    height=290,   # adjust once, then forget
    scrolling=False
)

    
    # Places
    section_loader("📍 Curating must-visit places…")
    st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
    st.markdown("## 📍 Places to Visit")
    cols = st.columns(3)
    for i, p in enumerate(plan["PLACES"]):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="glass-card">
                <div class="glass-title">{p['name']}</div>
                <div class="glass-sub">{p['type']} • ⭐ {p.get('rating','N/A')}</div>
            </div>
            """, unsafe_allow_html=True)

    # 🌦 Weather 
    
    import html

    def safe_html(text):
        if text is None:
            return ""
        return html.escape(str(text))


    weather = plan.get("WEATHER")
    if weather:
        section_loader("🌦 Fetching weather forecast…")
        st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
        st.markdown("## 🌦 Weather")

        days = weather.get("daily_forecast", [])

        #  SEASONAL MODE (NO DAILY DATA)
        if not days:
            st.markdown(f"""
            <div class="weather-card" style="max-width:520px;margin:auto;">
                <div class="weather-icon-big">🌤️</div>
                <div class="weather-condition">
                    Seasonal Weather Outlook
                </div>
                <div class="weather-meta">
                    📍 {safe_html(weather.get("city",""))}<br>
                     {safe_html(weather.get("start_date"))}
                    → {safe_html(weather.get("end_date"))}<br><br>

                    🌦 {safe_html(weather.get("seasonal_outlook","Typical conditions"))}
                    📊 Risk Score: {safe_html(weather.get("weather_risk_score", "--"))}/100 
                    💧 Avg Rain: {safe_html(weather.get("rain_probability_avg", "--"))}% 
                    🎯 Best Day: {safe_html(weather.get("best_day_to_travel","--"))} 
                    🔍 Confidence: {safe_html(weather.get("confidence","Low"))}
            </div>
            """, unsafe_allow_html=True)
            st.info("The travel date is too far in the future, and we don’t have day-wise weather data available for that period. The data being used above is based on seasonal weather patterns, not actual day-specific weather information.")

        # NORMAL FORECAST MODE 
        else:
            for i in range(0, len(days), 5):
                cols = st.columns(5)

                for col, d in zip(cols, days[i:i+5]):
                    with col:
                        st.markdown(f"""
                        <div class="weather-card">
                            <div class="weather-date">{safe_html(d['date'])}</div>
                            <div class="weather-icon-big">{weather_icon(d['condition'])}</div>
                            <div class="weather-condition">{safe_html(d['condition'])}</div>
                            <div class="weather-meta">
                                🌡 {safe_html(d['temp_min'])}°C – {safe_html(d['temp_max'])}°C<br>
                                💧 {safe_html(d['rain_probability'])}%<br>
                                😌 Comfort {safe_html(d['comfort_index'])}/100
                            </div>
                        </div>
                        """, unsafe_allow_html=True)



    # 💰 BUDGET ESTIMATE (WITH PER PERSON)
    section_loader("💰 Calculating your trip budget…")
    st.markdown("<div style='height:1vh'></div>", unsafe_allow_html=True)
    st.markdown("## 💰 Total Estimate Budget ")

    budget = plan["BUDGET_ESTIMATE"]
    travelers = intent["travelers"]

    def per_person(amount):
        try:
            return int(amount / travelers)
        except:
            return 0

    budget_html = f"""
    <div class="glass-card budget-card">

        <!-- FLIGHT -->
        <div class="budget-row">
            <div class="budget-info">
                <div class="budget-title">✈️ Flight</div>
                <div class="budget-desc">
                    Round-trip: {intent['source']} → {intent['destination']} → {intent['source']}
                </div>
            </div>
            <div class="budget-amount">
                ₹ {budget['breakdown']['flight']}\n
                <span class="per-person">₹ {per_person(budget['breakdown']['flight'])} / person</span>
            </div>
        </div>

        <!-- HOTEL -->
        <div class="budget-row">
            <div class="budget-info">
                <div class="budget-title">🏨 Hotel</div>
                <div class="budget-desc">
                    {travelers} travelers × {intent['days'] - 1} nights
                </div>
            </div>
            <div class="budget-amount">
                ₹ {budget['breakdown']['hotel']}\n
                <span class="per-person">₹ {per_person(budget['breakdown']['hotel'])} / person</span>
            </div>
        </div>

        <!-- FOOD -->
        <div class="budget-row">
            <div class="budget-info">
                <div class="budget-title">🍽️ Food + Local Travel + Miscellaneous </div>
                <div class="budget-desc">
                    {travelers} travelers × {intent['days']} days
                </div>
            </div>
            <div class="budget-amount">
                ₹ {budget['breakdown']['food_local_travel']}\n
                <span class="per-person">₹ {per_person(budget['breakdown']['food_local_travel'])} / person</span>
            </div>
        </div>

        <!-- DIVIDER -->
        <div class="budget-divider"></div>

        <!-- TOTAL -->
        <div class="budget-total">
            <span>Total Estimated Cost</span>
            <span>
                ₹ {budget['total_estimated_cost']} {budget['currency']}\n
                <span class="per-person-total">
                    ₹ {per_person(budget['total_estimated_cost'])} / person
                </span>

    </div>
    <style>
    .budget-card {{
        padding:24px;
    }}

    .budget-row {{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        margin-bottom:18px;
        color:white;
    }}

    .budget-info {{
        max-width:70%;
    }}

    .budget-title {{
        font-size:16px;
        font-weight:700;
    }}

    .budget-desc {{
        font-size:13px;
        opacity:0.75;
        margin-top:4px;
    }}

    .budget-amount {{
        font-size:16px;
        font-weight:700;
        text-align:right;
    }}

    .per-person {{
        font-size:12px;
        opacity:0.7;
        font-weight:500;
    }}

    .per-person-total {{
        font-size:13px;
        opacity:0.8;
        font-weight:600;
    }}

    .budget-divider {{
        height:1px;
        background:linear-gradient(
            to right,
            transparent,
            rgba(255,255,255,0.25),
            transparent
        );
        margin:20px 0;
    }}

    .budget-total {{
        display:flex;
        justify-content:space-between;
        font-size:20px;
        font-weight:900;
        color:white;
    }}
    </style>


    """
    components.html(budget_html, height=330, scrolling=False) 


    st.success("✨ Your Trip Plan Is Ready")
    
    def render_glass_timeline(itinerary, typing=True):

        closing_class = "fade-out" if st.session_state.itinerary_closing else ""
        section_loader("🗓 Crafting your day-wise itinerary…", delay=0.6)
        st.markdown("## 🗓 Day-Wise Itinerary", unsafe_allow_html=True)

        st.markdown(
            f'<div class="glass-timeline {closing_class}">',
            unsafe_allow_html=True
        )

        for day in itinerary:
            st.markdown('<div class="timeline-day">', unsafe_allow_html=True)
            

            if typing and not st.session_state.itinerary_closing:
                placeholder = st.empty()
                typed = ""

                for word in day["plan"].split():
                    typed += word + " "
                    placeholder.markdown(
                        f"""
                        <div class="timeline-card">
                            <div class="timeline-title">{day['day']}</div>
                            <div class="timeline-date">{day['date']}</div>
                            <div class="timeline-text">{typed}<span style="opacity:.4">▍</span></div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    time.sleep(0.012)

                placeholder.markdown(
                    f"""
                    <div class="timeline-card">
                        <div class="timeline-title">{day['day']}</div>
                        <div class="timeline-date">{day['date']}</div>
                        <div class="timeline-text">{typed}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            else:
                st.markdown(
                    f"""
                    <div class="timeline-card">
                        <div class="timeline-title">{day['day']}</div>
                        <div class="timeline-date">{day['date']}</div>
                        <div class="timeline-text">{day['plan']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)



    # VIEW BUTTON (only when closed)
    if not st.session_state.show_itinerary:
        col_btn, _ = st.columns([1, 5])
        with col_btn:
            if st.button("📅 View Day-Wise Itinerary", key="btn_daywise_itinerary"):
                st.session_state.show_itinerary = True
                st.session_state.itinerary_typed = False
                st.rerun()


    # TIMELINE RENDER
    if st.session_state.show_itinerary:

        render_glass_timeline(
            result["TRIP_PLAN"]["DAY_WISE_ITINERARY"],
            typing=not st.session_state.itinerary_typed
        )

        # mark typing complete AFTER first render
        st.session_state.itinerary_typed = True

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        col_close, _ = st.columns([1, 5])
        with col_close:
            if st.button("❌ Close Day-Wise Itinerary", key="btn_close_itinerary"):
                st.session_state.itinerary_closing = True
                st.rerun()
                
    if st.session_state.itinerary_closing:
        time.sleep(0.25) 
        st.session_state.show_itinerary = False
        st.session_state.itinerary_closing = False
        st.rerun()
    
    
    from pdf.trip_pdf_genertor import generate_trip_pdf

    pdf_path = "trip_plan.pdf"
    generate_trip_pdf(result, pdf_path)
    st.download_button(
        "📄 Download Trip PDF",
        data=open(pdf_path, "rb"),
        file_name="AI_Trip_Plan.pdf",
        mime="application/pdf"
    )

    
        
with tab_chat:
    st.session_state.active_mode = "chat"
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                "👋 Hey! I’m your AI Travel Planner ✈️\n\n"
                "I can help you plan flights, hotels, budgets, weather, "
                "and a complete day-wise itinerary — all in one place.\n\n"
                "👉 To get started, just type plan a trip"
            )
        })
    

    # CHAT MESSAGES
    for msg in st.session_state.messages:
        css = "assistant" if msg["role"] == "assistant" else "user"
        st.markdown(
            f'<div class="chat-bubble {css}">{msg["content"]}</div>',
            unsafe_allow_html=True
        )
    chat_area=st.container()
  
    # INPUT
    if not st.session_state.chat_locked:
        
            st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
            user_input = st.chat_input("Type your message…")
            if user_input:
                st.session_state.messages.append({
                    "role": "user",
                    "content": user_input.strip()
                })
                st.session_state.thinking = True
                st.rerun()

    # --- THINKING ---
    if st.session_state.thinking:
        with chat_area:
            stream_text("Thinking… ✨")
        

        result = st.session_state.agent.run(
            st.session_state.messages[-1]["content"]
        )

        if result["status"] == "NEED_INPUT":
            st.session_state.messages.append({
                "role": "assistant",
                "content": result["question"]
            })

        elif result["status"] == "COMPLETED":
            st.session_state.chat_result = result
            st.session_state.chat_locked = True
            st.session_state.messages.append({
                "role": "assistant",
                "content": "✨ Your travel plan is ready! Scroll down to see the full details."
            })

        st.session_state.thinking = False
        st.rerun()

    # --- RESULT RENDER ---
    if st.session_state.chat_result:
        st.divider()
        render_full_trip_ui(st.session_state.chat_result)


with tab_form:
    st.session_state.active_mode = "form"

    # ---------------- UI STYLES ----------------
    st.markdown("""
    <style>
    .form-card {
        background: rgba(255,255,255,0.06);
        border-radius: 20px;
        padding: 24px;
        margin-top: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }

    .form-title {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 6px;
    }

    .form-sub {
        font-size: 13px;
        opacity: 0.7;
        margin-bottom: 18px;
    }

    .form-divider {
        height: 1px;
        background: linear-gradient(
            to right,
            transparent,
            rgba(255,255,255,0.25),
            transparent
        );
        margin: 26px 0;
    }

    .form-reveal {
        animation: revealForm 0.45s ease-out forwards;
        transform: translateY(12px);
        opacity: 0;
    }

    @keyframes revealForm {
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # ---------------- HEADER ----------------
    st.markdown("## 📝 Quick Trip Planner")
    st.caption("Fill details once — get a complete plan instantly")

    agent = st.session_state.agent
    extractor = agent.city_extractor

    # RESET DESTINATION WHEN SOURCE CHANGES
 
    if "prev_form_source" not in st.session_state:
        st.session_state.prev_form_source = None

    if "form_source" in st.session_state:
        if st.session_state.prev_form_source != st.session_state.form_source:
            if "form_destination" in st.session_state:
                del st.session_state.form_destination
            st.session_state.prev_form_source = st.session_state.form_source


    # CLEAR PREVIOUS RESULT WHEN ROUTE CHANGES

    if "prev_form_route" not in st.session_state:
        st.session_state.prev_form_route = (None, None)

    current_route = (
        st.session_state.get("form_source"),
        st.session_state.get("form_destination")
    )

    if current_route != st.session_state.prev_form_route:
        st.session_state.form_result = None
        st.session_state.prev_form_route = current_route


    # DEPARTURE CITY (ALL SOURCES)
    source_options = ["Select departure city"] + extractor.all_sources()

    source = st.selectbox(
        "Departure City",
        source_options,
        key="form_source"
    )

    if source == "Select departure city":
        st.info("⬆️ Select a departure city to continue")
        st.stop()

    src_norm = extractor.normalize(source)

 
    # DESTINATION CITY (FILTERED)
    dest_options = ["Select destination"] + [
        city for city in extractor.destinations_from(src_norm)
        if extractor.normalize(city) != src_norm
    ]

    destination = st.selectbox(
        "Destination City",
        dest_options,
        key="form_destination"
    )

    if destination == "Select destination":
        st.info("⬆️ Select a destination to unlock trip details")
        st.stop()


    # FORM (REVEALED ONLY AFTER BOTH CITIES)
   
    submitted = False
    st.markdown('<div class="form-reveal">', unsafe_allow_html=True)
    with st.form("quick_trip_form"):

        trip_type = st.radio(
            "Trip Type",
            ["One Way", "Round Trip"],
            horizontal=True
        )

        travel_date = st.date_input(
            "Travel Date",
            min_value=date.today()
        )

        days = st.number_input(
            "Number of Days",
            min_value=1,
            max_value=30,
            value=5
        )

        travelers = st.number_input(
            "Travelers",
            min_value=1,
            max_value=10,
            value=2
        )

        budget = st.selectbox(
            "Budget Preference",
            ["budget", "mid-range", "luxury"]
        )

        submitted = st.form_submit_button("✨ Generate Trip Plan")

    st.markdown("</div>", unsafe_allow_html=True)

    


    if submitted:
        st.spinner("Gathhering All Information ")
        st.session_state.form_result = None

        # RESET AGENT
        st.session_state.agent = TravelAgent()
        agent = st.session_state.agent

        agent.state.update({
            "started": True,
            "source": source,
            "destination": destination,
            "trip_type": "round_trip" if trip_type == "Round Trip" else "one_way",
            "travel_date": travel_date.isoformat(),
            "return_date": (
                travel_date + timedelta(days=days - 1)
            ).isoformat() if trip_type == "Round Trip" else None,
            "days": days,
            "travelers": travelers,
            "preferences": {
                "budget": budget,
                "interests": []
            },
            "return_resolved": True
        })

        #  FORCE FINALIZATION
        agent.pending_slot = None
        agent.pending_outbound_options = None
        agent.pending_return_options = None
        agent._parsed_this_turn = True
        agent.force_finalize = True

        # RUN AGENT
        result = agent.run("plan a trip")

        if result.get("status") == "COMPLETED":
            st.session_state.form_result = result
            st.rerun()

        elif result.get("status") == "FORM_ERROR":
            st.info(result["message"])

        else:
            st.error("❌ Unable to generate trip plan. Please try again.")



    # RENDER FINAL RESULT (FORM MODE)
    if st.session_state.form_result:
        st.divider()
        render_full_trip_ui(st.session_state.form_result)
