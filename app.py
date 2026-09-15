import streamlit as st
import pandas as pd
import io
import re
import base64
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime, date, timedelta

from supabase import create_client


# =========================================================
# KONUHA
# نظام إدارة الأعضاء والمشرفين
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# SETTINGS
# =========================================================

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = BASE_DIR / "fonts"

LEAF_PATH = ASSETS_DIR / "naruto_leaf.png"

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
SITE_PASSWORD = st.secrets.get("SITE_PASSWORD", "")


# =========================================================
# HELPERS
# =========================================================

def file_to_base64(path: Path):
    """تحويل صورة إلى Base64 حتى نستخدمها داخل HTML."""
    try:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode()
    except Exception:
        pass
    return ""


LEAF_BASE64 = file_to_base64(LEAF_PATH)


def normalize_arabic(text):
    """
    توحيد الأسماء والألقاب للمقارنة.
    مثال:
    أرين / ايرن / أيرن
    """
    text = str(text or "").strip().lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[\s_\-.]+", "", text)
    text = re.sub(r"[^\w\u0600-\u06ff]+", "", text)

    return text


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_arabic(a),
        normalize_arabic(b),
    ).ratio()


def parse_date(value):
    try:
        if not value:
            return None

        value = str(value).replace("Z", "+00:00")

        return datetime.fromisoformat(value).date()

    except Exception:
        return None


def logo_html(class_name="brand-logo"):
    """
    K + شعار ناروتو + NUHA
    """

    if LEAF_BASE64:
        return f"""
        <div class="{class_name}">
            <span>K</span>
            <img src="data:image/png;base64,{LEAF_BASE64}">
            <span>NUHA</span>
        </div>
        """

    return f"""
    <div class="{class_name}">
        <span>KONUHA</span>
    </div>
    """


def supervisor_name(supervisors, supervisor_id):
    for supervisor in supervisors:
        if str(supervisor.get("id")) == str(supervisor_id):
            return supervisor.get("name", "-")

    return "-"


# =========================================================
# SUPABASE
# =========================================================

@st.cache_resource
def get_database():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )
    except Exception:
        return None


supabase = get_database()


@st.cache_data(ttl=20)
def check_connection():
    try:
        if supabase is None:
            return False

        supabase \
            .table("supervisors") \
            .select("id") \
            .limit(1) \
            .execute()

        return True

    except Exception:
        return False


@st.cache_data(ttl=15)
def load_members():
    try:
        if supabase is None:
            return []

        response = (
            supabase
            .table("members")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception:
        return []


@st.cache_data(ttl=15)
def load_supervisors():
    try:
        if supabase is None:
            return []

        response = (
            supabase
            .table("supervisors")
            .select("*")
            .order("created_at")
            .execute()
        )

        return response.data or []

    except Exception:
        return []


def clear_database_cache():
    try:
        load_members.clear()
    except Exception:
        pass

    try:
        load_supervisors.clear()
    except Exception:
        pass

    try:
        check_connection.clear()
    except Exception:
        pass


# =========================================================
# GLOBAL CSS
# =========================================================

st.markdown(
    """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&family=Readex+Pro:wght@400;500;600;700&display=swap'
);


/* =====================================================
   GLOBAL
   ===================================================== */

* {
    box-sizing: border-box;
}

html,
body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {

    background:
        radial-gradient(
            850px 500px at 75% -10%,
            rgba(164, 75, 255, .10),
            transparent 65%
        ),
        radial-gradient(
            700px 500px at 0% 100%,
            rgba(231, 77, 171, .07),
            transparent 65%
        ),
        #070914 !important;

    color: #f7f3ff !important;
}


[data-testid="stHeader"] {
    display: none !important;
}

#MainMenu {
    display: none !important;
}

footer {
    display: none !important;
}


/* =====================================================
   MAIN CONTAINER
   ===================================================== */

.block-container {
    max-width: 1500px !important;
    padding: 18px 25px 50px !important;
}


/* =====================================================
   SIDEBAR
   ===================================================== */

[data-testid="stSidebar"] {

    width: 285px !important;
    min-width: 285px !important;

    background:
        linear-gradient(
            180deg,
            #0c1021 0%,
            #080b17 100%
        ) !important;

    border-right:
        1px solid rgba(177, 99, 255, .12) !important;
}


[data-testid="stSidebar"] > div:first-child {
    padding: 0 14px 20px !important;
}


/* =====================================================
   LOGO
   ===================================================== */

.brand-area {

    padding:
        25px
        8px
        21px;

    border-bottom:
        1px solid rgba(178, 96, 255, .12);

    margin-bottom: 12px;
}


.brand-logo {

    display: flex;

    justify-content: center;

    align-items: center;

    gap: 1px;

    font-family: Inter, sans-serif;

    font-size: 38px;

    font-weight: 800;

    letter-spacing: 1px;

    color: #ffffff;

    text-shadow:
        0 0 25px rgba(211, 95, 255, .45);
}


.brand-logo img {

    width: 40px;

    height: 40px;

    object-fit: contain;

    filter:
        drop-shadow(
            0 0 10px
            rgba(205, 90, 255, .65)
        );
}


.brand-sub {

    text-align: center;

    margin-top: 5px;

    color: #777b94;

    font-family: Cairo, sans-serif;

    font-size: 12px;
}


.side-label {

    padding:
        10px
        15px
        7px;

    color: #656980;

    font-family: Cairo, sans-serif;

    font-size: 11px;
}


/* =====================================================
   SIDEBAR BUTTONS
   ===================================================== */

[data-testid="stSidebar"] .stButton > button {

    width: 100% !important;

    min-height: 46px !important;

    margin: 2px 0 !important;

    padding:
        0
        18px !important;

    border:
        1px solid transparent !important;

    border-radius: 13px !important;

    background: transparent !important;

    color: #aaaec3 !important;

    font-family: Cairo, sans-serif !important;

    font-size: 13px !important;

    text-align: right !important;

    box-shadow: none !important;

    transition:
        .2s ease;
}


[data-testid="stSidebar"] .stButton > button:hover {

    color: #ffffff !important;

    background:
        rgba(164, 91, 255, .10) !important;

    border-color:
        rgba(180, 105, 255, .15) !important;
}


/*
  Active navigation.
*/

.nav-active button {

    color: #ffffff !important;

    background:
        linear-gradient(
            90deg,
            rgba(155, 85, 255, .23),
            rgba(225, 80, 178, .07)
        ) !important;

    border-color:
        rgba(185, 105, 255, .18) !important;

    box-shadow:
        inset 4px 0
        #c25cff !important;
}


/* =====================================================
   TOP BAR
   ===================================================== */

.topbar {

    min-height: 52px;

    display: flex;

    justify-content: flex-end;

    align-items: center;

    gap: 10px;

    margin-bottom: 10px;
}


.connection {

    padding:
        9px
        16px;

    border-radius: 999px;

    font-family: Cairo, sans-serif;

    font-size: 12px;

    border:
        1px solid rgba(69, 227, 153, .35);
}


.connection.online {

    color: #63e8a6;

    background:
        rgba(69, 227, 153, .05);
}


.connection.offline {

    color: #ff8298;

    background:
        rgba(255, 90, 113, .05);

    border-color:
        rgba(255, 90, 113, .35);
}


.top-brand {

    padding:
        9px
        17px;

    border-radius: 999px;

    border:
        1px solid rgba(171, 92, 255, .18);

    color: #c8bbd9;

    font-family: Inter, sans-serif;

    font-size: 12px;
}


/* =====================================================
   HERO
   ===================================================== */

.hero {

    min-height: 330px;

    position: relative;

    overflow: hidden;

    border-radius: 25px;

    border:
        1px solid rgba(175, 94, 255, .18);

    padding:
        48px;

    background:

        radial-gradient(
            circle at 78% 38%,
            rgba(224, 83, 180, .18),
            transparent 27%
        ),

        radial-gradient(
            circle at 60% 100%,
            rgba(108, 70, 255, .12),
            transparent 40%
        ),

        linear-gradient(
            120deg,
            #090c1c,
            #11152a 54%,
            #181126
        );

    box-shadow:
        0 25px 75px
        rgba(0,0,0,.35);
}


/* tiny particles */

.hero::before {

    content: "";

    position: absolute;

    inset: 0;

    opacity: .25;

    background-image:

        radial-gradient(
            circle,
            rgba(255,255,255,.9)
            0 1px,
            transparent 2px
        ),

        radial-gradient(
            circle,
            rgba(205,112,255,.8)
            0 1px,
            transparent 2px
        );

    background-size:
        150px 120px,
        220px 170px;

    pointer-events: none;
}


/* =====================================================
   HERO CHARACTER / SILHOUETTE
   ===================================================== */

.hero-character {

    position: absolute;

    right: -20px;

    bottom: -110px;

    width: 440px;

    height: 530px;

    opacity: .72;

    pointer-events: none;

    z-index: 1;

    background:

        radial-gradient(
            ellipse at 50% 22%,
            rgba(235,91,191,.25)
            0 7%,
            transparent 8%
        ),

        radial-gradient(
            ellipse at 50% 40%,
            #17142e
            0 21%,
            transparent 22%
        ),

        radial-gradient(
            ellipse at 50% 78%,
            #111225
            0 36%,
            transparent 37%
        );

    filter:
        drop-shadow(
            0 0 35px
            rgba(187,82,255,.18)
        );
}


.hero-character::before {

    content: "";

    position: absolute;

    left: 50%;

    top: 17%;

    transform:
        translateX(-50%);

    width: 180px;

    height: 120px;

    border-radius:
        50%
        50%
        45%
        45%;

    background:
        #0e0f1f;

    box-shadow:
        0 0 50px
        rgba(215,88,195,.20);
}


.hero-character::after {

    content: "";

    position: absolute;

    left: 50%;

    top: 36%;

    transform:
        translateX(-50%);

    width: 230px;

    height: 30px;

    border-radius: 8px;

    background:
        #28233f;

    box-shadow:
        0 65px 90px
        45px
        rgba(141,74,255,.10);
}


/* =====================================================
   HERO CONTENT
   ===================================================== */

.hero-content {

    position: relative;

    z-index: 3;

    max-width: 650px;
}


.hero-logo {

    display: flex;

    align-items: center;

    font-family: Inter, sans-serif;

    font-size: 72px;

    font-weight: 800;

    letter-spacing: 2px;

    line-height: 1;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #b978ff 52%,
            #ed59b8
        );

    -webkit-background-clip: text;

    background-clip: text;

    color: transparent;
}


.hero-logo img {

    width: 73px;

    height: 73px;

    object-fit: contain;

    filter:
        drop-shadow(
            0 0 16px
            rgba(205,88,255,.75)
        );
}


.hero-subtitle {

    margin-top: 15px;

    font-family: Cairo, sans-serif;

    font-size: 17px;

    color: #d8d5e2;
}


.hero-quote {

    margin-top: 30px;

    font-family: Cairo, sans-serif;

    font-size: 15px;

    font-weight: 600;

    color: #eee9f3;
}


.hero-line {

    width: 50px;

    height: 3px;

    margin-top: 12px;

    border-radius: 10px;

    background:
        linear-gradient(
            90deg,
            #aa5cff,
            #e45ab7
        );
}


/* =====================================================
   STATISTICS CARDS
   ===================================================== */

.stats-grid {

    display: grid;

    grid-template-columns:
        repeat(4, minmax(0,1fr));

    gap: 16px;

    margin-top: 18px;
}


.stat-card {

    min-height: 145px;

    position: relative;

    padding: 20px;

    border:
        1px solid
        rgba(167,91,255,.15);

    border-radius: 20px;

    background:
        linear-gradient(
            145deg,
            rgba(21,25,54,.92),
            rgba(12,16,35,.92)
        );

    box-shadow:
        0 16px 45px
        rgba(0,0,0,.25);
}


.stat-icon {

    position: absolute;

    left: 20px;

    top: 20px;

    width: 50px;

    height: 50px;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 16px;

    background:
        rgba(150,84,255,.10);

    font-size: 22px;
}


.stat-label {

    text-align: right;

    font-family: Cairo, sans-serif;

    font-size: 13px;

    color: #aaaec3;
}


.stat-value {

    margin-top: 20px;

    text-align: right;

    font-family: Inter, sans-serif;

    font-size: 38px;

    font-weight: 800;

    color: #ffffff;
}


.stat-green {

    border-color:
        rgba(70,229,157,.20);
}


.stat-green .stat-value {

    color: #62e7a9;
}


.stat-pink {

    border-color:
        rgba(232,86,184,.20);
}


.stat-blue {

    border-color:
        rgba(59,202,224,.20);
}


/* =====================================================
   MAIN PANELS
   ===================================================== */

.main-grid {

    display: grid;

    grid-template-columns:
        minmax(0, 2.15fr)
        minmax(290px, .8fr);

    gap: 18px;

    margin-top: 18px;
}


.panel {

    min-height: 430px;

    padding: 22px;

    border:
        1px solid
        rgba(167,91,255,.14);

    border-radius: 22px;

    background:
        rgba(12,16,32,.84);

    box-shadow:
        0 20px 55px
        rgba(0,0,0,.25);
}


.panel-title {

    margin-bottom: 16px;

    font-family:
        "Readex Pro",
        Cairo,
        sans-serif;

    font-size: 18px;

    font-weight: 600;

    color: #f1eef8;
}


.empty-state {

    min-height: 315px;

    display: flex;

    flex-direction: column;

    justify-content: center;

    align-items: center;

    text-align: center;

    color: #7e829e;

    font-family: Cairo, sans-serif;

    font-size: 14px;
}


/* =====================================================
   INFO CARD
   ===================================================== */

.info-card {

    min-height: 430px;

    padding: 25px;

    border:
        1px solid
        rgba(229,87,187,.32);

    border-radius: 22px;

    background:

        radial-gradient(
            circle at 50% 0%,
            rgba(191,76,158,.12),
            transparent 38%
        ),

        #0d1021;
}


.info-logo {

    text-align: center;

    font-family: Inter, sans-serif;

    font-size: 35px;

    font-weight: 800;

    background:
        linear-gradient(
            90deg,
            #ffffff,
            #b66fff,
            #ec5ab7
        );

    -webkit-background-clip: text;

    background-clip: text;

    color: transparent;
}


.info-title {

    text-align: center;

    margin-top: 7px;

    margin-bottom: 20px;

    font-family: Cairo, sans-serif;

    font-size: 14px;

    color: #e9e5ef;
}


.info-item {

    display: flex;

    align-items: center;

    gap: 12px;

    margin: 18px 0;
}


.info-icon {

    width: 43px;

    height: 43px;

    flex-shrink: 0;

    display: flex;

    align-items: center;

    justify-content: center;

    border-radius: 50%;

    background:
        rgba(164,105,255,.10);
}


.info-item strong {

    display: block;

    font-family: Cairo, sans-serif;

    font-size: 13px;

    color: #eeeaf5;
}


.info-item span {

    display: block;

    margin-top: 2px;

    font-family: Cairo, sans-serif;

    font-size: 11px;

    color: #85899f;
}


/* =====================================================
   FORMS
   ===================================================== */

input,
textarea,
[data-baseweb="select"] > div {

    background:
        #0d1225 !important;

    color:
        #ffffff !important;

    border-color:
        rgba(163,91,255,.22) !important;

    border-radius:
        12px !important;
}


label {

    font-family:
        Cairo,
        sans-serif !important;

    color:
        #b9bacb !important;
}


.stButton > button {

    font-family:
        Cairo,
        sans-serif !important;

    border-radius:
        12px !important;
}


.stFormSubmitButton > button {

    background:
        linear-gradient(
            90deg,
            #8d4cff,
            #d953b1
        ) !important;

    border:
        0 !important;

    color:
        white !important;

    min-height:
        46px !important;

    font-weight:
        700 !important;
}


.stDownloadButton > button {

    background:
        #11162d !important;

    color:
        #ffffff !important;

    border:
        1px solid
        rgba(166,91,255,.20) !important;
}


/* =====================================================
   DATAFRAME
   ===================================================== */

[data-testid="stDataFrame"] {

    border:
        1px solid
        rgba(165,91,255,.13) !important;

    border-radius:
        16px !important;

    overflow:
        hidden !important;
}


/* =====================================================
   SECTION HEAD
   ===================================================== */

.section-head {

    margin:
        8px 0 18px;

    font-family:
        "Readex Pro",
        Cairo,
        sans-serif;

    font-size:
        25px;

    font-weight:
        700;

    color:
        #ffffff;
}


/* =====================================================
   LOGIN
   ===================================================== */

.login-wrap {

    width:
        min(460px, calc(100vw - 28px));

    margin:
        8vh auto 0;

    padding:
        35px 28px;

    position:
        relative;

    overflow:
        hidden;

    border:
        1px solid
        rgba(169,91,255,.25);

    border-radius:
        28px;

    text-align:
        center;

    background:

        radial-gradient(
            circle at 80% 10%,
            rgba(224,86,184,.12),
            transparent 35%
        ),

        linear-gradient(
            145deg,
            #11152b,
            #080c1b
        );

    box-shadow:
        0 30px 100px
        rgba(0,0,0,.55);
}


.login-wrap::after {

    content: "";

    position: absolute;

    width: 320px;

    height: 380px;

    right: -120px;

    bottom: -160px;

    background:
        radial-gradient(
            ellipse,
            rgba(214,87,184,.18),
            transparent 65%
        );

    pointer-events: none;
}


.login-logo {

    position:
        relative;

    z-index:
        2;

    display:
        flex;

    justify-content:
        center;

    align-items:
        center;

    font-family:
        Inter,
        sans-serif;

    font-size:
        54px;

    font-weight:
        800;

    color:
        #ffffff;
}


.login-logo img {

    width:
        57px;

    height:
        57px;

    object-fit:
        contain;

    filter:
        drop-shadow(
            0 0 14px
            rgba(208,91,255,.7)
        );
}


.login-sub {

    position:
        relative;

    z-index:
        2;

    margin:
        8px 0 25px;

    font-family:
        Cairo,
        sans-serif;

    font-size:
        14px;

    color:
        #9498af;
}


/* =====================================================
   MOBILE NAVIGATION
   ===================================================== */

.mobile-navigation {

    display:
        none;

    margin-bottom:
        12px;
}


.mobile-navigation label {

    display:
        block;

    margin-bottom:
        5px;
}


/* =====================================================
   MOBILE
   ===================================================== */

@media (max-width: 900px) {

    [data-testid="stSidebar"] {
        display:
            none !important;
    }

    .mobile-navigation {
        display:
            block !important;
    }

    .block-container {
        padding:
            10px 14px 35px !important;
    }


    .topbar {
        justify-content:
            center;

        min-height:
            48px;
    }


    .hero {

        min-height:
            350px;

        padding:
            32px 22px;

        border-radius:
            22px;
    }


    .hero-logo {

        font-size:
            56px;
    }


    .hero-logo img {

        width:
            57px;

        height:
            57px;
    }


    .hero-subtitle {

        font-size:
            14px;

        max-width:
            270px;
    }


    .hero-character {

        width:
            340px;

        height:
            430px;

        right:
            -105px;

        bottom:
            -100px;

        opacity:
            .42;
    }


    .hero-quote {

        position:
            absolute;

        right:
            22px;

        bottom:
            32px;

        top:
            auto;

        max-width:
            230px;
    }


    .stats-grid {

        grid-template-columns:
            repeat(2, minmax(0, 1fr));

        gap:
            12px;
    }


    .stat-card {

        min-height:
            130px;

        padding:
            17px;

        border-radius:
            18px;
    }


    .stat-icon {

        width:
            43px;

        height:
            43px;

        left:
            17px;

        top:
            17px;
    }


    .stat-value {

        font-size:
            31px;
    }


    .main-grid {

        grid-template-columns:
            1fr;
    }


    .info-card {

        min-height:
            auto;
    }
}


/* =====================================================
   SMALL PHONE
   ===================================================== */

@media (max-width: 520px) {

    .topbar {

        flex-wrap:
            wrap;

        gap:
            7px;
    }


    .connection,
    .top-brand {

        padding:
            8px 12px;

        font-size:
            11px;
    }


    .hero {

        min-height:
            330px;

        padding:
            27px 19px;

        border-radius:
            20px;
    }


    .hero-logo {

        font-size:
            43px;

        letter-spacing:
            1px;
    }


    .hero-logo img {

        width:
            45px;

        height:
            45px;
    }


    .hero-subtitle {

        font-size:
            13px;
    }


    .hero-quote {

        font-size:
            12px;

        max-width:
            205px;
    }


    .hero-character {

        width:
            280px;

        height:
            370px;

        right:
            -105px;

        bottom:
            -90px;

        opacity:
            .34;
    }


    .stats-grid {

        grid-template-columns:
            repeat(2, minmax(0, 1fr));

        gap:
            10px;
    }


    .stat-card {

        min-height:
            124px;

        padding:
            15px;

        border-radius:
            17px;
    }


    .stat-label {

        font-size:
            11px;
    }


    .stat-value {

        font-size:
            28px;

        margin-top:
            18px;
    }


    .stat-icon {

        width:
            40px;

        height:
            40px;

        left:
            14px;

        top:
            14px;

        font-size:
            18px;
    }


    .section-head {

        font-size:
            21px;
    }


    .login-wrap {

        margin-top:
            6vh;

        padding:
            30px 19px;
    }


    .login-logo {

        font-size:
            43px;
    }


    .login-logo img {

        width:
            45px;

        height:
            45px;
    }
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# LOGIN
# =========================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


if not st.session_state.authenticated:

    st.markdown(
        f"""
        <div class="login-wrap">

            <div class="login-logo">
                K
                <img
                    src="data:image/png;base64,{LEAF_BASE64}"
                >
                NUHA
            </div>

            <div class="login-sub">
                نظام إدارة الأعضاء والمشرفين
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("konuha_login"):

        password = st.text_input(
            "كلمة المرور",
            type="password",
            placeholder="أدخل كلمة المرور",
        )

        login_button = st.form_submit_button(
            "دخول إلى KONUHA",
            use_container_width=True,
        )

    if login_button:

        if SITE_PASSWORD and password == SITE_PASSWORD:

            st.session_state.authenticated = True

            st.rerun()

        else:

            st.error(
                "كلمة المرور غير صحيحة."
            )

    st.stop()


# =========================================================
# DATA
# =========================================================

members = load_members()
supervisors = load_supervisors()


# =========================================================
# NAVIGATION
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"


NAVIGATION = [
    ("⌂", "الرئيسية"),
    ("♟", "الأعضاء"),
    ("＋", "إضافة عضو"),
    ("⬡", "المشرفين"),
    ("✚", "إضافة مشرف"),
    ("▥", "الإحصائيات"),
    ("⇩", "التصدير"),
    ("⌫", "الحذف"),
]


# =========================================================
# SIDEBAR - DESKTOP
# =========================================================

with st.sidebar:

    st.markdown(
        f"""
        <div class="brand-area">

            {logo_html("brand-logo")}

            <div class="brand-sub">
                نظام إدارة الأعضاء
            </div>

        </div>

        <div class="side-label">
            القائمة الرئيسية
        </div>
        """,
        unsafe_allow_html=True,
    )


    for icon, label in NAVIGATION:

        active = (
            st.session_state.page == label
        )

        if active:
            st.markdown(
                '<div class="nav-active">',
                unsafe_allow_html=True,
            )

        clicked = st.button(
            f"{icon}   {label}",
            key=f"sidebar_{label}",
            use_container_width=True,
        )

        if active:
            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        if clicked:

            st.session_state.page = label

            st.rerun()


    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )


    if st.button(
        "↪   تسجيل الخروج",
        key="logout_button",
        use_container_width=True,
    ):

        st.session_state.authenticated = False

        st.rerun()


# =========================================================
# MOBILE NAVIGATION
# =========================================================

st.markdown(
    '<div class="mobile-navigation">',
    unsafe_allow_html=True,
)


mobile_page = st.selectbox(
    "القائمة",
    [item[1] for item in NAVIGATION],
    index=[
        item[1]
        for item in NAVIGATION
    ].index(
        st.session_state.page
    ),
    key="mobile_page_selector",
)


if mobile_page != st.session_state.page:

    st.session_state.page = mobile_page

    st.rerun()


st.markdown(
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# TOP STATUS
# =========================================================

is_connected = check_connection()

if is_connected:

    status_class = "online"

    status_text = (
        "🟢 متصل بـ Supabase"
    )

else:

    status_class = "offline"

    status_text = (
        "🔴 غير متصل بـ Supabase"
    )


st.markdown(
    f"""
    <div class="topbar">

        <div class="connection {status_class}">
            {status_text}
        </div>

        <div class="top-brand">
            KONUHA
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-character"></div>

            <div class="hero-content">

                <div class="hero-logo">

                    <span>K</span>

                    <img
                        src="data:image/png;base64,{LEAF_BASE64}"
                    >

                    <span>NUHA</span>

                </div>

                <div class="hero-subtitle">
                    نظام إدارة الأعضاء والمشرفين
                </div>

                <div class="hero-quote">
                    "الأشياء العظيمة تبدأ بخطوة صغيرة"
                </div>

                <div class="hero-line"></div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # TODAY COUNT
    # -----------------------------------------------------

    today_members = 0

    for member in members:

        created = parse_date(
            member.get("created_at")
        )

        if created == date.today():

            today_members += 1


    # -----------------------------------------------------
    # STATISTICS
    # -----------------------------------------------------

    stats = [

        (
            "👥",
            "إجمالي الأعضاء",
            len(members),
            "",
        ),

        (
            "🛡️",
            "المشرفين",
            len(supervisors),
            "stat-pink",
        ),

        (
            "▣",
            "أعضاء اليوم",
            today_members,
            "stat-blue",
        ),

        (
            "🔗",
            "حالة النظام",
            "متصل" if is_connected else "غير متصل",
            "stat-green",
        ),

    ]


    stats_html = ""

    for icon, label, value, css_class in stats:

        stats_html += f"""
        <div class="stat-card {css_class}">

            <div class="stat-icon">
                {icon}
            </div>

            <div class="stat-label">
                {label}
            </div>

            <div class="stat-value">
                {value}
            </div>

        </div>
        """


    st.markdown(
        f"""
        <div class="stats-grid">
            {stats_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # MAIN CONTENT
    # -----------------------------------------------------

    st.markdown(
        '<div class="main-grid">',
        unsafe_allow_html=True,
    )


    # LEFT
    st.markdown(
        '<div class="panel">',
        unsafe_allow_html=True,
    )


    st.markdown(
        '<div class="panel-title">♟ آخر الأعضاء</div>',
        unsafe_allow_html=True,
    )


    if members:

        latest_rows = []

        for member in members[:10]:

            latest_rows.append(
                {
                    "اللقب":
                        member.get(
                            "nickname",
                            "",
                        ),

                    "الرقم":
                        member.get(
                            "phone",
                            "",
                        ),

                    "من طرف":
                        supervisor_name(
                            supervisors,
                            member.get(
                                "referrer_id"
                            ),
                        ),

                    "استقبله":
                        supervisor_name(
                            supervisors,
                            member.get(
                                "receiver_id"
                            ),
                        ),

                    "تاريخ الإضافة":
                        member.get(
                            "created_at",
                            "",
                        ),
                }
            )


        st.dataframe(
            pd.DataFrame(
                latest_rows
            ),
            use_container_width=True,
            hide_index=True,
            height=320,
        )

    else:

        st.markdown(
            """
            <div class="empty-state">

                <div style="font-size:35px">
                    ♙
                </div>

                <div>
                    لا توجد أعضاء مسجلين حالياً
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


    # RIGHT
    st.markdown(
        """
        <div class="info-card">

            <div class="info-logo">
                KONUHA
            </div>

            <div class="info-title">
                معاً نصنع مجتمعاً أفضل
            </div>

            <hr style="border-color:rgba(165,91,255,.12)">

            <div class="info-item">

                <div class="info-icon">
                    👥
                </div>

                <div>
                    <strong>
                        إدارة الأعضاء بسهولة
                    </strong>

                    <span>
                        نظام متكامل لإدارة أعضائك
                    </span>
                </div>

            </div>


            <div class="info-item">

                <div class="info-icon">
                    🛡️
                </div>

                <div>
                    <strong>
                        أمان ومرونة
                    </strong>

                    <span>
                        بياناتك في بيئة آمنة
                    </span>
                </div>

            </div>


            <div class="info-item">

                <div class="info-icon">
                    ⚡
                </div>

                <div>
                    <strong>
                        بسرعة وكفاءة
                    </strong>

                    <span>
                        لجميع احتياجاتك الإدارية
                    </span>
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":

    st.markdown(
        '<div class="section-head">الأعضاء</div>',
        unsafe_allow_html=True,
    )


    search = st.text_input(
        "البحث",
        placeholder="اكتب اللقب أو الرقم...",
    )


    rows = []


    for member in members:

        nickname = member.get(
            "nickname",
            "",
        )

        phone = member.get(
            "phone",
            "",
        )


        if search:

            nickname_match = (
                normalize_arabic(search)
                in normalize_arabic(nickname)
            )

            phone_match = (
                search in phone
            )

            if not nickname_match and not phone_match:
                continue


        rows.append(
            {
                "اللقب": nickname,

                "الرقم": phone,

                "من طرف":
                    supervisor_name(
                        supervisors,
                        member.get(
                            "referrer_id"
                        ),
                    ),

                "استقبله":
                    supervisor_name(
                        supervisors,
                        member.get(
                            "receiver_id"
                        ),
                    ),

                "تاريخ الإضافة":
                    member.get(
                        "created_at",
                        "",
                    ),
            }
        )


    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "لا توجد نتائج."
        )


# =========================================================
# ADD MEMBER
# =========================================================

elif st.session_state.page == "إضافة عضو":

    st.markdown(
        '<div class="section-head">إضافة عضو</div>',
        unsafe_allow_html=True,
    )


    if not supervisors:

        st.warning(
            "لا يوجد مشرفون. أضف مشرفاً أولاً."
        )

    else:

        with st.form(
            "add_member_form"
        ):

            nickname = st.text_input(
                "اللقب",
                placeholder="مثال: ايرن",
            )

            phone = st.text_input(
                "الرقم",
                placeholder="9647XXXXXXXX",
            )


            supervisor_names = [
                supervisor["name"]
                for supervisor in supervisors
                if supervisor.get(
                    "is_active",
                    True,
                )
            ]


            referrer = st.selectbox(
                "من طرف",
                supervisor_names,
            )


            receiver = st.selectbox(
                "استقبله",
                supervisor_names,
            )


            force_add = st.checkbox(
                "إضافة إجبارية إذا كان هناك لقب مشابه",
            )


            submit = st.form_submit_button(
                "إضافة العضو",
                use_container_width=True,
            )


        if submit:

            nickname = nickname.strip()
            phone = phone.strip()


            if not nickname or not phone:

                st.error(
                    "أكمل جميع البيانات."
                )

            else:

                # -----------------------------------------
                # EXACT PHONE DUPLICATE
                # -----------------------------------------

                try:

                    duplicate = (
                        supabase
                        .table("members")
                        .select("id,nickname,phone")
                        .eq("phone", phone)
                        .limit(1)
                        .execute()
                        .data
                    )

                except Exception:

                    duplicate = []


                # -----------------------------------------
                # SIMILAR NICKNAMES
                # -----------------------------------------

                similar_members = []


                for member in members:

                    score = similarity(
                        member.get(
                            "nickname",
                            "",
                        ),
                        nickname,
                    )

                    if score >= 0.82:

                        similar_members.append(
                            {
                                "nickname":
                                    member.get(
                                        "nickname",
                                        "",
                                    ),
                                "score":
                                    score,
                            }
                        )


                # -----------------------------------------
                # DUPLICATE PHONE
                # -----------------------------------------

                if duplicate:

                    st.error(
                        "هذا الرقم مسجل مسبقاً. "
                        "الإضافة الإجبارية لا تتجاوز تكرار الرقم."
                    )


                # -----------------------------------------
                # SIMILAR NICKNAME
                # -----------------------------------------

                elif similar_members and not force_add:

                    names = ", ".join(
                        item["nickname"]
                        for item in similar_members[:5]
                    )

                    st.warning(
                        f"يوجد لقب مشابه بالفعل: {names}"
                    )

                    st.info(
                        "إذا كنت متأكداً أن العضو مختلف، "
                        "فعّل خيار الإضافة الإجبارية."
                    )


                # -----------------------------------------
                # INSERT
                # -----------------------------------------

                else:

                    referrer_obj = next(
                        (
                            supervisor
                            for supervisor in supervisors
                            if supervisor["name"]
                            == referrer
                        ),
                        None,
                    )


                    receiver_obj = next(
                        (
                            supervisor
                            for supervisor in supervisors
                            if supervisor["name"]
                            == receiver
                        ),
                        None,
                    )


                    if not referrer_obj or not receiver_obj:

                        st.error(
                            "تعذر العثور على المشرف."
                        )

                    else:

                        try:

                            (
                                supabase
                                .table("members")
                                .insert(
                                    {
                                        "nickname":
                                            nickname,

                                        "normalized_nickname":
                                            normalize_arabic(
                                                nickname
                                            ),

                                        "phone":
                                            phone,

                                        "referrer_id":
                                            referrer_obj[
                                                "id"
                                            ],

                                        "receiver_id":
                                            receiver_obj[
                                                "id"
                                            ],
                                    }
                                )
                                .execute()
                            )


                            clear_database_cache()

                            st.success(
                                "تمت إضافة العضو بنجاح."
                            )

                            st.rerun()

                        except Exception as error:

                            st.error(
                                f"حدث خطأ أثناء الإضافة: {error}"
                            )


# =========================================================
# SUPERVISORS
# =========================================================

elif st.session_state.page == "المشرفين":

    st.markdown(
        '<div class="section-head">المشرفين</div>',
        unsafe_allow_html=True,
    )


    if supervisors:

        rows = []

        for supervisor in supervisors:

            rows.append(
                {
                    "الاسم":
                        supervisor.get(
                            "name",
                            "",
                        ),

                    "اللقب":
                        supervisor.get(
                            "nickname",
                            "",
                        ),

                    "الحالة":
                        (
                            "فعال"
                            if supervisor.get(
                                "is_active",
                                True,
                            )
                            else
                            "متوقف"
                        ),

                    "تاريخ الإضافة":
                        supervisor.get(
                            "created_at",
                            "",
                        ),
                }
            )


        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "لا يوجد مشرفون حالياً."
        )


# =========================================================
# ADD SUPERVISOR
# =========================================================

elif st.session_state.page == "إضافة مشرف":

    st.markdown(
        '<div class="section-head">إضافة مشرف</div>',
        unsafe_allow_html=True,
    )


    with st.form(
        "add_supervisor_form"
    ):

        name = st.text_input(
            "اسم المشرف",
            placeholder="مثال: احمد",
        )

        nickname = st.text_input(
            "لقب المشرف",
            placeholder="مثال: المشرف العام",
        )


        submit = st.form_submit_button(
            "إضافة المشرف",
            use_container_width=True,
        )


    if submit:

        name = name.strip()
        nickname = nickname.strip()


        if not name or not nickname:

            st.error(
                "أكمل جميع البيانات."
            )

        else:

            try:

                existing = (
                    supabase
                    .table("supervisors")
                    .select("id,name,nickname")
                    .eq(
                        "normalized_name",
                        normalize_arabic(name),
                    )
                    .limit(1)
                    .execute()
                    .data
                )


                if existing:

                    st.warning(
                        "يوجد مشرف بهذا الاسم مسبقاً."
                    )

                else:

                    (
                        supabase
                        .table("supervisors")
                        .insert(
                            {
                                "name":
                                    name,

                                "nickname":
                                    nickname,

                                "normalized_name":
                                    normalize_arabic(
                                        name
                                    ),

                                "normalized_nickname":
                                    normalize_arabic(
                                        nickname
                                    ),

                                "is_active":
                                    True,
                            }
                        )
                        .execute()
                    )


                    clear_database_cache()

                    st.success(
                        "تمت إضافة المشرف بنجاح."
                    )

                    st.rerun()


            except Exception as error:

                st.error(
                    f"حدث خطأ: {error}"
                )


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":

    st.markdown(
        '<div class="section-head">الإحصائيات</div>',
        unsafe_allow_html=True,
    )


    supervisor_filter = st.selectbox(
        "المشرف",
        [
            "الكل"
        ]
        +
        [
            supervisor["name"]
            for supervisor in supervisors
        ],
    )


    period = st.selectbox(
        "الفترة",
        [
            "الكل",
            "اليوم",
            "امس",
            "هذا_الشهر",
            "تاريخ محدد",
        ],
    )


    selected_date = None


    if period == "تاريخ محدد":

        selected_date = st.date_input(
            "التاريخ",
            date.today(),
        )


    filtered_members = []


    for member in members:

        if supervisor_filter != "الكل":

            member_supervisor = supervisor_name(
                supervisors,
                member.get(
                    "referrer_id"
                ),
            )

            if member_supervisor != supervisor_filter:

                continue


        created_date = parse_date(
            member.get(
                "created_at"
            )
        )


        if not created_date:

            continue


        if period == "اليوم":

            if created_date != date.today():

                continue


        elif period == "امس":

            if created_date != (
                date.today()
                -
                timedelta(days=1)
            ):

                continue


        elif period == "هذا_الشهر":

            current = date.today()

            if (
                created_date.year != current.year
                or
                created_date.month != current.month
            ):

                continue


        elif period == "تاريخ محدد":

            if created_date != selected_date:

                continue


        filtered_members.append(
            member
        )


    # -----------------------------------------------------
    # STAT CARDS
    # -----------------------------------------------------

    st.markdown(
        f"""
        <div class="stats-grid">

            <div class="stat-card">
                <div class="stat-label">
                    النتيجة
                </div>

                <div class="stat-value">
                    {len(filtered_members)}
                </div>
            </div>


            <div class="stat-card stat-pink">

                <div class="stat-label">
                    المشرف
                </div>

                <div
                    class="stat-value"
                    style="font-size:22px"
                >
                    {supervisor_filter}
                </div>

            </div>


            <div class="stat-card stat-blue">

                <div class="stat-label">
                    الفترة
                </div>

                <div
                    class="stat-value"
                    style="font-size:20px"
                >
                    {period}
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


    # -----------------------------------------------------
    # SUPERVISOR BREAKDOWN
    # -----------------------------------------------------

    st.markdown(
        "<br>",
        unsafe_allow_html=True,
    )


    if supervisors:

        breakdown = []


        for supervisor in supervisors:

            count = 0


            for member in filtered_members:

                if str(
                    member.get(
                        "referrer_id"
                    )
                ) == str(
                    supervisor.get(
                        "id"
                    )
                ):

                    count += 1


            breakdown.append(
                {
                    "المشرف":
                        supervisor.get(
                            "name",
                            "",
                        ),

                    "اللقب":
                        supervisor.get(
                            "nickname",
                            "",
                        ),

                    "عدد الأعضاء":
                        count,
                }
            )


        st.dataframe(
            pd.DataFrame(breakdown),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":

    st.markdown(
        '<div class="section-head">التصدير</div>',
        unsafe_allow_html=True,
    )


    export_rows = []


    for member in members:

        export_rows.append(
            {
                "اللقب":
                    member.get(
                        "nickname",
                        "",
                    ),

                "الرقم":
                    member.get(
                        "phone",
                        "",
                    ),

                "من طرف":
                    supervisor_name(
                        supervisors,
                        member.get(
                            "referrer_id"
                        ),
                    ),

                "استقبله":
                    supervisor_name(
                        supervisors,
                        member.get(
                            "receiver_id"
                        ),
                    ),

                "تاريخ الإضافة":
                    member.get(
                        "created_at",
                        "",
                    ),
            }
        )


    export_df = pd.DataFrame(
        export_rows
    )


    st.markdown(
        "### تحميل البيانات",
    )


    # CSV

    csv_data = export_df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )


    st.download_button(
        "⇩ تحميل CSV",
        data=csv_data,
        file_name="konuha_members.csv",
        mime="text/csv",
        use_container_width=True,
    )


    # EXCEL

    excel_buffer = io.BytesIO()


    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:

        export_df.to_excel(
            writer,
            index=False,
            sheet_name="Members",
        )


    st.download_button(
        "⇩ تحميل Excel",
        data=excel_buffer.getvalue(),
        file_name="konuha_members.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )


    # PDF

    try:

        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas


        pdf_buffer = io.BytesIO()

        pdf = canvas.Canvas(
            pdf_buffer,
            pagesize=A4,
        )


        width, height = A4

        y = height - 50


        pdf.setFont(
            "Helvetica-Bold",
            20,
        )

        pdf.drawString(
            50,
            y,
            "KONUHA Members",
        )


        y -= 40

        pdf.setFont(
            "Helvetica",
            9,
        )


        for member in members:

            nickname = str(
                member.get(
                    "nickname",
                    "",
                )
            )

            phone = str(
                member.get(
                    "phone",
                    "",
                )
            )


            line = (
                f"{nickname} | {phone}"
            )


            pdf.drawString(
                50,
                y,
                line[:95],
            )


            y -= 17


            if y < 50:

                pdf.showPage()

                y = height - 50

                pdf.setFont(
                    "Helvetica",
                    9,
                )


        pdf.save()


        st.download_button(
            "⇩ تحميل PDF",
            data=pdf_buffer.getvalue(),
            file_name="konuha_members.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


    except Exception:

        st.info(
            "PDF غير متاح حالياً. تأكد من وجود reportlab."
        )


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":

    st.markdown(
        '<div class="section-head">حذف عضو</div>',
        unsafe_allow_html=True,
    )


    if not members:

        st.info(
            "لا توجد أعضاء للحذف."
        )

    else:

        member_options = [
            member.get(
                "nickname",
                "",
            )
            for member in members
        ]


        selected_nickname = st.selectbox(
            "اختر العضو",
            member_options,
        )


        selected_member = next(
            (
                member
                for member in members
                if member.get(
                    "nickname"
                )
                == selected_nickname
            ),
            None,
        )


        if selected_member:

            st.markdown(
                f"""
                <div class="panel">

                    <div class="panel-title">
                        معلومات العضو
                    </div>

                    <p style="font-family:Cairo">
                        <b>اللقب:</b>
                        {selected_member.get("nickname","")}
                    </p>

                    <p style="font-family:Cairo">
                        <b>الرقم:</b>
                        {selected_member.get("phone","")}
                    </p>

                    <p style="font-family:Cairo">
                        <b>من طرف:</b>
                        {
                            supervisor_name(
                                supervisors,
                                selected_member.get(
                                    "referrer_id"
                                )
                            )
                        }
                    </p>

                    <p style="font-family:Cairo">
                        <b>استقبله:</b>
                        {
                            supervisor_name(
                                supervisors,
                                selected_member.get(
                                    "receiver_id"
                                )
                            )
                        }
                    </p>

                </div>
                """,
                unsafe_allow_html=True,
            )


        st.markdown(
            "<br>",
            unsafe_allow_html=True,
        )


        confirm_delete = st.checkbox(
            "أؤكد أنني أريد حذف هذا العضو نهائياً",
        )


        delete_button = st.button(
            "حذف العضو نهائياً",
            use_container_width=True,
        )


        if delete_button:

            if not confirm_delete:

                st.warning(
                    "فعّل التأكيد أولاً."
                )

            elif selected_member:

                try:

                    (
                        supabase
                        .table("members")
                        .delete()
                        .eq(
                            "id",
                            selected_member["id"],
                        )
                        .execute()
                    )


                    clear_database_cache()


                    st.success(
                        "تم حذف العضو بنجاح."
                    )


                    st.rerun()


                except Exception as error:

                    st.error(
                        f"حدث خطأ أثناء الحذف: {error}"
                    )


# =========================================================
# END
# =========================================================
