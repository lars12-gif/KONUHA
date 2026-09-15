
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
# KONUHA — نظام إدارة الأعضاء والمشرفين
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)

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
    try:
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception:
        pass
    return ""


LEAF_BASE64 = file_to_base64(LEAF_PATH)


def normalize_arabic(text):
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

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
    return SequenceMatcher(None, normalize_arabic(a), normalize_arabic(b)).ratio()


def parse_date(value):
    try:
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except Exception:
        return None


def supervisor_name(supervisors, supervisor_id):
    for supervisor in supervisors:
        if str(supervisor.get("id")) == str(supervisor_id):
            return supervisor.get("name", "-")
    return "-"


def font_file(keyword, weight_words):
    normalized_keyword = keyword.lower().replace("_", "").replace("-", "").replace(" ", "")
    for path in FONTS_DIR.glob("*.ttf"):
        name = path.name.lower().replace("_", "").replace("-", "").replace(" ", "")
        if normalized_keyword in name and any(word in name for word in weight_words):
            return path
    return None


def font_face(keyword, family, weight_words, css_weight):
    path = font_file(keyword, weight_words)
    if not path:
        return ""
    data = file_to_base64(path)
    if not data:
        return ""
    return (
        f"@font-face{{font-family:'{family}';font-style:normal;"
        f"font-weight:{css_weight};src:url(data:font/ttf;base64,{data}) format('truetype');}}"
    )


def build_font_css():
    regular_words = ["regular", "normal", "400"]
    medium_words = ["medium", "500"]
    semibold_words = ["semibold", "600"]
    bold_words = ["bold", "700", "800"]

    css = []
    for keyword, family in [
        ("Cairo", "KonohaCairo"),
        ("Inter", "KonohaInter"),
        ("ReadexPro", "KonohaReadex"),
        ("Readex_Pro", "KonohaReadex"),
    ]:
        css.extend([
            font_face(keyword, family, regular_words, 400),
            font_face(keyword, family, medium_words, 500),
            font_face(keyword, family, semibold_words, 600),
            font_face(keyword, family, bold_words, 700),
        ])
    return "\n".join(dict.fromkeys(css))


FONT_CSS = build_font_css()


# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def get_database():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


supabase = get_database()


@st.cache_data(ttl=20)
def check_connection():
    try:
        if supabase is None:
            return False
        supabase.table("supervisors").select("id").limit(1).execute()
        return True
    except Exception:
        return False


@st.cache_data(ttl=15)
def load_members():
    try:
        if supabase is None:
            return []
        response = (
            supabase.table("members")
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
            supabase.table("supervisors")
            .select("*")
            .order("created_at")
            .execute()
        )
        return response.data or []
    except Exception:
        return []


def clear_database_cache():
    for fn in (load_members, load_supervisors, check_connection):
        try:
            fn.clear()
        except Exception:
            pass


# =========================================================
# VISUAL SYSTEM
# =========================================================

st.markdown(
    f"""
    <style>
    {FONT_CSS}

    :root {{
        --bg: #05060b;
        --surface: #0a0c14;
        --surface-2: #0f1220;
        --surface-3: #151827;
        --text: #f7f8ff;
        --muted: #9298ab;
        --red: #ff3158;
        --red-2: #b70f35;
        --purple: #8b5cff;
        --pink: #e948a4;
        --green: #42e6a1;
        --line: rgba(255,255,255,.08);
    }}

    * {{ box-sizing: border-box; }}

    html, body,
    [data-testid="stApp"],
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {{
        background:
            radial-gradient(900px 500px at 92% -8%, rgba(255,49,88,.11), transparent 62%),
            radial-gradient(800px 600px at 5% 30%, rgba(139,92,255,.09), transparent 64%),
            #05060b !important;
        color: var(--text) !important;
    }}

    [data-testid="stHeader"], #MainMenu, footer {{
        display: none !important;
    }}

    [data-testid="stToolbar"] {{
        display: none !important;
    }}

    .block-container {{
        max-width: 1480px !important;
        padding: 18px 28px 60px !important;
    }}

    /* ---------- top navigation ---------- */

    .k-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 16px;
    }}

    .k-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 180px;
    }}

    .k-brand-mark {{
        width: 42px;
        height: 42px;
        border-radius: 13px;
        display: grid;
        place-items: center;
        background: linear-gradient(145deg, #ff3158, #8b2cff);
        box-shadow: 0 0 28px rgba(255,49,88,.22);
        font: 800 18px 'KonohaInter', Inter, sans-serif;
        color: #fff;
    }}

    .k-brand-name {{
        font: 800 22px 'KonohaInter', Inter, sans-serif;
        letter-spacing: 1px;
    }}

    .k-brand-sub {{
        color: var(--muted);
        font: 500 10px 'KonohaCairo', Cairo, sans-serif;
        margin-top: -2px;
    }}

    .k-status {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 13px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: rgba(255,255,255,.035);
        font: 600 11px 'KonohaCairo', Cairo, sans-serif;
        white-space: nowrap;
    }}

    .k-status.online {{
        color: #6af0b3;
        border-color: rgba(66,230,161,.22);
    }}

    .k-status.offline {{
        color: #ff8297;
        border-color: rgba(255,49,88,.25);
    }}

    /* ---------- native buttons = custom nav, no HTML wrappers ---------- */

    div.stButton > button {{
        min-height: 42px;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,.07) !important;
        background: rgba(255,255,255,.035) !important;
        color: #bfc3d2 !important;
        font: 600 12px 'KonohaCairo', Cairo, sans-serif !important;
        transition: all .18s ease !important;
        box-shadow: none !important;
    }}

    div.stButton > button:hover {{
        color: #fff !important;
        border-color: rgba(255,49,88,.28) !important;
        background: linear-gradient(135deg, rgba(255,49,88,.14), rgba(139,92,255,.10)) !important;
        transform: translateY(-1px);
    }}

    .k-nav-active + div.stButton > button {{
        color: #fff !important;
        border-color: rgba(255,49,88,.38) !important;
        background: linear-gradient(135deg, rgba(255,49,88,.22), rgba(139,92,255,.16)) !important;
        box-shadow: 0 0 22px rgba(255,49,88,.08) !important;
    }}

    /* ---------- hero ---------- */

    .k-hero {{
        position: relative;
        overflow: hidden;
        min-height: 360px;
        border-radius: 30px;
        border: 1px solid rgba(255,255,255,.09);
        padding: 48px 50px;
        background:
            radial-gradient(circle at 80% 45%, rgba(255,49,88,.22), transparent 25%),
            radial-gradient(circle at 68% 90%, rgba(139,92,255,.17), transparent 34%),
            linear-gradient(135deg, #090b12 0%, #0d101b 52%, #150b16 100%);
        box-shadow:
            0 30px 90px rgba(0,0,0,.48),
            inset 0 1px rgba(255,255,255,.035);
    }}

    .k-hero::before {{
        content: "";
        position: absolute;
        inset: 0;
        opacity: .18;
        background-image:
            linear-gradient(rgba(255,255,255,.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px);
        background-size: 45px 45px;
        mask-image: linear-gradient(to right, black, transparent 75%);
        pointer-events: none;
    }}

    .k-orb {{
        position: absolute;
        width: 300px;
        height: 300px;
        right: 8%;
        top: 50%;
        transform: translateY(-50%);
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,49,88,.22), rgba(139,92,255,.08) 42%, transparent 70%);
        filter: blur(4px);
        pointer-events: none;
    }}

    .k-hero-art {{
        position: absolute;
        right: 3%;
        bottom: -70px;
        width: 430px;
        height: 430px;
        opacity: .46;
        border-radius: 50%;
        background:
            radial-gradient(circle at 50% 35%, rgba(255,255,255,.12) 0 7%, transparent 7.5%),
            radial-gradient(ellipse at 50% 52%, rgba(18,20,34,.98) 0 25%, transparent 25.7%),
            radial-gradient(ellipse at 50% 80%, rgba(11,13,24,.98) 0 38%, transparent 38.7%);
        filter: drop-shadow(0 0 55px rgba(255,49,88,.15));
        pointer-events: none;
    }}

    .k-hero-content {{
        position: relative;
        z-index: 3;
        max-width: 690px;
        direction: rtl;
        text-align: right;
    }}

    .k-eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 11px;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,.08);
        background: rgba(255,255,255,.035);
        color: #bfc4d5;
        font: 600 11px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-eyebrow i {{
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--red);
        box-shadow: 0 0 12px var(--red);
    }}

    .k-hero-title {{
        margin-top: 20px;
        font: 900 78px/1 'KonohaInter', Inter, sans-serif;
        letter-spacing: 3px;
        background: linear-gradient(105deg, #fff 10%, #ff7b92 52%, #9d6cff 95%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        filter: drop-shadow(0 0 30px rgba(255,49,88,.14));
    }}

    .k-hero-title span {{
        display: inline-block;
        margin-left: 10px;
        color: #fff;
        font-weight: 900;
    }}

    .k-hero-sub {{
        margin-top: 14px;
        color: #c4c8d6;
        font: 500 17px/1.9 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-hero-quote {{
        margin-top: 24px;
        color: #f4f4fb;
        font: 700 14px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-hero-line {{
        width: 80px;
        height: 3px;
        margin-top: 13px;
        border-radius: 10px;
        background: linear-gradient(90deg, var(--red), var(--purple));
        box-shadow: 0 0 18px rgba(255,49,88,.35);
    }}

    /* ---------- cards ---------- */

    .k-section-title {{
        margin: 28px 0 13px;
        font: 800 21px 'KonohaReadex', 'KonohaCairo', sans-serif;
        color: #fff;
        direction: rtl;
        text-align: right;
    }}

    .k-card-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
    }}

    .k-card {{
        position: relative;
        min-height: 145px;
        overflow: hidden;
        padding: 20px;
        border-radius: 21px;
        border: 1px solid rgba(255,255,255,.075);
        background: linear-gradient(145deg, rgba(20,23,37,.92), rgba(8,10,18,.92));
        box-shadow: 0 20px 55px rgba(0,0,0,.28);
        direction: rtl;
        text-align: right;
    }}

    .k-card::after {{
        content: "";
        position: absolute;
        width: 130px;
        height: 130px;
        right: -55px;
        bottom: -65px;
        border-radius: 50%;
        background: rgba(255,49,88,.12);
        filter: blur(25px);
    }}

    .k-card.red {{ border-color: rgba(255,49,88,.20); }}
    .k-card.purple {{ border-color: rgba(139,92,255,.20); }}
    .k-card.green {{ border-color: rgba(66,230,161,.20); }}
    .k-card.blue {{ border-color: rgba(63,191,255,.18); }}

    .k-card-icon {{
        width: 45px;
        height: 45px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        background: rgba(255,255,255,.05);
        font-size: 19px;
    }}

    .k-card-label {{
        margin-top: 17px;
        color: #9398ab;
        font: 600 11px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-card-value {{
        margin-top: 3px;
        color: #fff;
        font: 900 31px 'KonohaInter', Inter, sans-serif;
    }}

    .k-card.red .k-card-value {{ color: #ff6a83; }}
    .k-card.purple .k-card-value {{ color: #b28dff; }}
    .k-card.green .k-card-value {{ color: #68edb1; }}
    .k-card.blue .k-card-value {{ color: #73d6ff; }}

    .k-panel {{
        border: 1px solid rgba(255,255,255,.07);
        border-radius: 24px;
        padding: 22px;
        background: rgba(8,10,18,.78);
        box-shadow: 0 22px 60px rgba(0,0,0,.25);
    }}

    .k-panel-title {{
        margin-bottom: 14px;
        color: #fff;
        font: 700 17px 'KonohaReadex', 'KonohaCairo', sans-serif;
        direction: rtl;
        text-align: right;
    }}

    .k-info {{
        border-radius: 24px;
        padding: 28px;
        min-height: 360px;
        border: 1px solid rgba(255,49,88,.20);
        background:
            radial-gradient(circle at 50% 0%, rgba(255,49,88,.14), transparent 38%),
            linear-gradient(145deg, #0e111d, #090b13);
        text-align: center;
    }}

    .k-info-logo {{
        font: 900 36px 'KonohaInter', Inter, sans-serif;
        background: linear-gradient(90deg, #fff, #ff6d87, #9d6cff);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}

    .k-info-title {{
        margin-top: 7px;
        color: #d9dbe5;
        font: 600 13px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-info-item {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 22px 0;
        direction: rtl;
        text-align: right;
    }}

    .k-info-icon {{
        width: 43px;
        height: 43px;
        flex: 0 0 43px;
        display: grid;
        place-items: center;
        border-radius: 14px;
        background: rgba(255,49,88,.08);
        border: 1px solid rgba(255,49,88,.10);
    }}

    .k-info-item strong {{
        display: block;
        color: #f1f2f7;
        font: 700 12px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-info-item span {{
        display: block;
        margin-top: 2px;
        color: #7f8497;
        font: 500 10px 'KonohaCairo', Cairo, sans-serif;
    }}

    /* ---------- forms / tables ---------- */

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {{
        background: #0d101a !important;
        border-color: rgba(255,255,255,.09) !important;
        border-radius: 13px !important;
    }}

    input, textarea {{
        color: #fff !important;
        font-family: 'KonohaCairo', Cairo, sans-serif !important;
    }}

    label {{
        color: #b8bdcd !important;
        font: 600 12px 'KonohaCairo', Cairo, sans-serif !important;
    }}

    .stForm {{
        border: 1px solid rgba(255,255,255,.07) !important;
        border-radius: 24px !important;
        padding: 22px !important;
        background: rgba(8,10,18,.78) !important;
    }}

    div[data-testid="stDataFrame"] {{
        border: 1px solid rgba(255,255,255,.07) !important;
        border-radius: 17px !important;
        overflow: hidden !important;
    }}

    div.stFormSubmitButton > button {{
        min-height: 47px !important;
        border: 0 !important;
        color: #fff !important;
        background: linear-gradient(100deg, #ff3158, #b52bff) !important;
        box-shadow: 0 12px 28px rgba(255,49,88,.17) !important;
        font-weight: 800 !important;
    }}

    div.stDownloadButton > button {{
        min-height: 46px !important;
        border-color: rgba(255,255,255,.09) !important;
        background: #10131f !important;
        color: #fff !important;
    }}

    .k-login {{
        max-width: 500px;
        margin: 8vh auto 0;
        padding: 42px 34px 30px;
        border: 1px solid rgba(255,49,88,.18);
        border-radius: 30px;
        background:
            radial-gradient(circle at 80% 5%, rgba(255,49,88,.16), transparent 35%),
            linear-gradient(145deg, #10131f, #070911);
        box-shadow: 0 35px 110px rgba(0,0,0,.55);
        text-align: center;
    }}

    .k-login-logo {{
        font: 900 58px 'KonohaInter', Inter, sans-serif;
        letter-spacing: 2px;
        background: linear-gradient(90deg, #fff, #ff617c, #9b6cff);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }}

    .k-login-sub {{
        margin: 8px 0 24px;
        color: #858a9d;
        font: 500 12px 'KonohaCairo', Cairo, sans-serif;
    }}

    .k-alert {{
        margin: 15px 0;
        padding: 13px 16px;
        border-radius: 15px;
        background: rgba(255,49,88,.08);
        border: 1px solid rgba(255,49,88,.18);
        color: #ff91a2;
        font: 600 12px 'KonohaCairo', Cairo, sans-serif;
        direction: rtl;
        text-align: right;
    }}

    @media (max-width: 1000px) {{
        .k-card-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .k-hero-art {{ right: -100px; opacity: .28; }}
        .k-hero-title {{ font-size: 60px; }}
    }}

    @media (max-width: 700px) {{
        .block-container {{ padding: 12px 12px 40px !important; }}
        .k-top {{ align-items: flex-start; flex-direction: column; }}
        .k-brand {{ min-width: 0; }}
        .k-hero {{ min-height: 350px; padding: 30px 22px; border-radius: 23px; }}
        .k-hero-title {{ font-size: 45px; letter-spacing: 1px; }}
        .k-hero-sub {{ font-size: 13px; }}
        .k-hero-art {{ width: 330px; height: 330px; right: -105px; bottom: -65px; opacity: .23; }}
        .k-card-grid {{ gap: 10px; }}
        .k-card {{ min-height: 125px; padding: 15px; }}
        .k-card-value {{ font-size: 27px; }}
        .k-info {{ min-height: auto; }}
    }}

    @media (max-width: 430px) {{
        .k-card-grid {{ grid-template-columns: 1fr 1fr; }}
        .k-brand-name {{ font-size: 19px; }}
        .k-brand-mark {{ width: 38px; height: 38px; }}
    }}
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
        """
        <div class="k-login">
            <div class="k-login-logo">KONUHA</div>
            <div class="k-login-sub">نظام إدارة الأعضاء والمشرفين</div>
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
        login = st.form_submit_button(
            "دخول إلى KONUHA",
            use_container_width=True,
        )

    if login:
        if SITE_PASSWORD and password == SITE_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        elif not SITE_PASSWORD:
            st.error("لم يتم ضبط SITE_PASSWORD في Secrets.")
        else:
            st.error("كلمة المرور غير صحيحة.")
    st.stop()


# =========================================================
# DATA
# =========================================================

members = load_members()
supervisors = load_supervisors()

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"

NAVIGATION = [
    ("⌂", "الرئيسية"),
    ("♙", "الأعضاء"),
    ("＋", "إضافة عضو"),
    ("♜", "المشرفين"),
    ("✚", "إضافة مشرف"),
    ("▦", "الإحصائيات"),
    ("⇩", "التصدير"),
    ("⌫", "الحذف"),
]


# =========================================================
# HEADER + NAV
# =========================================================

connected = check_connection()
status_class = "online" if connected else "offline"
status_text = "🟢 متصل بـ Supabase" if connected else "🔴 غير متصل بـ Supabase"

st.markdown(
    f"""
    <div class="k-top">
        <div class="k-brand">
            <div class="k-brand-mark">K</div>
            <div>
                <div class="k-brand-name">KONUHA</div>
                <div class="k-brand-sub">CONTROL • MEMBERS • DATA</div>
            </div>
        </div>
        <div class="k-status {status_class}">{status_text}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_cols = st.columns(len(NAVIGATION), gap="small")
for col, (icon, label) in zip(nav_cols, NAVIGATION):
    with col:
        if st.session_state.page == label:
            st.markdown('<div class="k-nav-active"></div>', unsafe_allow_html=True)
        if st.button(
            f"{icon}  {label}",
            key=f"nav_{label}",
            use_container_width=True,
        ):
            st.session_state.page = label
            st.rerun()

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# Logout is deliberately native Streamlit and not wrapped in HTML.
logout_col = st.columns([7, 1])[1]
with logout_col:
    if st.button("↪ خروج", key="logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":
    today_members = sum(
        1 for member in members
        if parse_date(member.get("created_at")) == date.today()
    )

    st.markdown(
        """
        <section class="k-hero">
            <div class="k-orb"></div>
            <div class="k-hero-art"></div>
            <div class="k-hero-content">
                <div class="k-eyebrow"><i></i> KONUHA CONTROL CENTER</div>
                <div class="k-hero-title">KONUHA</div>
                <div class="k-hero-sub">
                    نظام إدارة الأعضاء والمشرفين — كل بياناتك في مكان واحد،
                    بواجهة سريعة وواضحة ومصممة بهوية KONUHA.
                </div>
                <div class="k-hero-quote">"نظام مرتب. بيانات واضحة. إدارة أسهل."</div>
                <div class="k-hero-line"></div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="k-section-title">نظرة سريعة</div>', unsafe_allow_html=True)

    cards = [
        ("👥", "إجمالي الأعضاء", len(members), "red"),
        ("♜", "المشرفين", len(supervisors), "purple"),
        ("✦", "أعضاء اليوم", today_members, "blue"),
        ("⌁", "حالة النظام", "متصل" if connected else "غير متصل", "green"),
    ]

    card_html = '<div class="k-card-grid">'
    for icon, label, value, color in cards:
        card_html += f"""
        <div class="k-card {color}">
            <div class="k-card-icon">{icon}</div>
            <div class="k-card-label">{label}</div>
            <div class="k-card-value">{value}</div>
        </div>
        """
    card_html += "</div>"
    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown('<div class="k-section-title">آخر النشاطات</div>', unsafe_allow_html=True)
    left, right = st.columns([2.05, 1], gap="medium")

    with left:
        st.markdown('<div class="k-panel"><div class="k-panel-title">آخر الأعضاء المضافين</div>', unsafe_allow_html=True)
        latest_rows = []
        for member in members[:10]:
            latest_rows.append({
                "اللقب": member.get("nickname", ""),
                "الرقم": member.get("phone", ""),
                "من طرف": supervisor_name(supervisors, member.get("referrer_id")),
                "استقبله": supervisor_name(supervisors, member.get("receiver_id")),
                "تاريخ الإضافة": member.get("created_at", ""),
            })
        if latest_rows:
            st.dataframe(
                pd.DataFrame(latest_rows),
                use_container_width=True,
                hide_index=True,
                height=330,
            )
        else:
            st.info("لا توجد أعضاء مسجلين حالياً.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown(
            """
            <div class="k-info">
                <div class="k-info-logo">KONUHA</div>
                <div class="k-info-title">لوحة تحكم واحدة لكل ما تحتاجه</div>
                <div class="k-info-item">
                    <div class="k-info-icon">👥</div>
                    <div><strong>إدارة الأعضاء</strong><span>إضافة، فحص، عرض وحذف البيانات.</span></div>
                </div>
                <div class="k-info-item">
                    <div class="k-info-icon">♜</div>
                    <div><strong>المشرفون</strong><span>تحديد المسؤولين واستخدامهم في التسجيل.</span></div>
                </div>
                <div class="k-info-item">
                    <div class="k-info-icon">⚡</div>
                    <div><strong>إحصائيات واضحة</strong><span>متابعة الأرقام حسب المشرف والفترة.</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":
    st.markdown('<div class="k-section-title">الأعضاء</div>', unsafe_allow_html=True)
    search = st.text_input(
        "البحث",
        placeholder="اكتب اللقب أو الرقم...",
        key="member_search",
    )

    rows = []
    query = normalize_arabic(search) if search else ""
    for member in members:
        nickname = member.get("nickname", "")
        phone = str(member.get("phone", ""))

        if search:
            nickname_match = query in normalize_arabic(nickname)
            phone_match = str(search).strip() in phone
            if not nickname_match and not phone_match:
                continue

        rows.append({
            "اللقب": nickname,
            "الرقم": phone,
            "من طرف": supervisor_name(supervisors, member.get("referrer_id")),
            "استقبله": supervisor_name(supervisors, member.get("receiver_id")),
            "تاريخ الإضافة": member.get("created_at", ""),
        })

    st.markdown('<div class="k-panel">', unsafe_allow_html=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد نتائج.")
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ADD MEMBER
# =========================================================

elif st.session_state.page == "إضافة عضو":
    st.markdown('<div class="k-section-title">إضافة عضو جديد</div>', unsafe_allow_html=True)

    if not supervisors:
        st.warning("لا يوجد مشرفون. أضف مشرفاً أولاً.")
    else:
        active_supervisors = [
            s for s in supervisors if s.get("is_active", True)
        ]
        supervisor_names = [s["name"] for s in active_supervisors]

        st.markdown('<div class="k-panel">', unsafe_allow_html=True)
        with st.form("add_member_form"):
            c1, c2 = st.columns(2)
            with c1:
                nickname = st.text_input("اللقب", placeholder="مثال: ايرن")
            with c2:
                phone = st.text_input("الرقم", placeholder="9647XXXXXXXX")

            c3, c4 = st.columns(2)
            with c3:
                referrer = st.selectbox("من طرف", supervisor_names)
            with c4:
                receiver = st.selectbox("استقبله", supervisor_names)

            force_add = st.checkbox("إضافة إجبارية إذا كان هناك لقب مشابه")
            submit = st.form_submit_button("إضافة العضو", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if submit:
            nickname = nickname.strip()
            phone = phone.strip()

            if not nickname or not phone:
                st.error("أكمل جميع البيانات.")
            elif supabase is None:
                st.error("قاعدة البيانات غير متصلة.")
            else:
                try:
                    duplicate = (
                        supabase.table("members")
                        .select("id,nickname,phone")
                        .eq("phone", phone)
                        .limit(1)
                        .execute()
                        .data
                    )
                except Exception:
                    duplicate = []

                similar_members = [
                    member.get("nickname", "")
                    for member in members
                    if similarity(member.get("nickname", ""), nickname) >= 0.82
                ]

                if duplicate:
                    st.error("هذا الرقم مسجل مسبقاً. الإضافة الإجبارية لا تتجاوز تكرار الرقم.")
                elif similar_members and not force_add:
                    names = ", ".join(similar_members[:5])
                    st.warning(f"يوجد لقب مشابه بالفعل: {names}")
                    st.info("إذا كنت متأكداً أن العضو مختلف، فعّل خيار الإضافة الإجبارية.")
                else:
                    referrer_obj = next(
                        (s for s in active_supervisors if s["name"] == referrer),
                        None,
                    )
                    receiver_obj = next(
                        (s for s in active_supervisors if s["name"] == receiver),
                        None,
                    )

                    if not referrer_obj or not receiver_obj:
                        st.error("تعذر العثور على المشرف.")
                    else:
                        try:
                            supabase.table("members").insert({
                                "nickname": nickname,
                                "normalized_nickname": normalize_arabic(nickname),
                                "phone": phone,
                                "referrer_id": referrer_obj["id"],
                                "receiver_id": receiver_obj["id"],
                            }).execute()
                            clear_database_cache()
                            st.success("تمت إضافة العضو بنجاح.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"حدث خطأ أثناء الإضافة: {error}")


# =========================================================
# SUPERVISORS
# =========================================================

elif st.session_state.page == "المشرفين":
    st.markdown('<div class="k-section-title">المشرفين</div>', unsafe_allow_html=True)

    rows = [
        {
            "الاسم": s.get("name", ""),
            "اللقب": s.get("nickname", ""),
            "الحالة": "فعال" if s.get("is_active", True) else "متوقف",
            "تاريخ الإضافة": s.get("created_at", ""),
        }
        for s in supervisors
    ]

    st.markdown('<div class="k-panel">', unsafe_allow_html=True)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا يوجد مشرفون حالياً.")
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ADD SUPERVISOR
# =========================================================

elif st.session_state.page == "إضافة مشرف":
    st.markdown('<div class="k-section-title">إضافة مشرف</div>', unsafe_allow_html=True)

    st.markdown('<div class="k-panel">', unsafe_allow_html=True)
    with st.form("add_supervisor_form"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم المشرف", placeholder="مثال: احمد")
        with c2:
            nickname = st.text_input("لقب المشرف", placeholder="مثال: المشرف العام")
        submit = st.form_submit_button("إضافة المشرف", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if submit:
        name = name.strip()
        nickname = nickname.strip()

        if not name or not nickname:
            st.error("أكمل جميع البيانات.")
        elif supabase is None:
            st.error("قاعدة البيانات غير متصلة.")
        else:
            try:
                existing = (
                    supabase.table("supervisors")
                    .select("id,name,nickname")
                    .eq("normalized_name", normalize_arabic(name))
                    .limit(1)
                    .execute()
                    .data
                )

                if existing:
                    st.warning("يوجد مشرف بهذا الاسم مسبقاً.")
                else:
                    supabase.table("supervisors").insert({
                        "name": name,
                        "nickname": nickname,
                        "normalized_name": normalize_arabic(name),
                        "normalized_nickname": normalize_arabic(nickname),
                        "is_active": True,
                    }).execute()
                    clear_database_cache()
                    st.success("تمت إضافة المشرف بنجاح.")
                    st.rerun()
            except Exception as error:
                st.error(f"حدث خطأ: {error}")


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":
    st.markdown('<div class="k-section-title">الإحصائيات</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        supervisor_filter = st.selectbox(
            "المشرف",
            ["الكل"] + [s["name"] for s in supervisors],
        )
    with c2:
        period = st.selectbox(
            "الفترة",
            ["الكل", "اليوم", "امس", "هذا_الشهر", "تاريخ محدد"],
        )

    selected_date = date.today()
    if period == "تاريخ محدد":
        selected_date = st.date_input("التاريخ", date.today())

    filtered_members = []
    for member in members:
        if supervisor_filter != "الكل":
            if supervisor_name(supervisors, member.get("referrer_id")) != supervisor_filter:
                continue

        created_date = parse_date(member.get("created_at"))
        if not created_date:
            continue

        if period == "اليوم" and created_date != date.today():
            continue
        if period == "امس" and created_date != date.today() - timedelta(days=1):
            continue
        if period == "هذا_الشهر":
            current = date.today()
            if created_date.year != current.year or created_date.month != current.month:
                continue
        if period == "تاريخ محدد" and created_date != selected_date:
            continue

        filtered_members.append(member)

    stat_cards = [
        ("◉", "النتيجة", len(filtered_members), "red"),
        ("♜", "المشرف", supervisor_filter, "purple"),
        ("◷", "الفترة", period, "blue"),
        ("✓", "حالة الاتصال", "متصل" if connected else "غير متصل", "green"),
    ]

    html = '<div class="k-card-grid">'
    for icon, label, value, color in stat_cards:
        html += f"""
        <div class="k-card {color}">
            <div class="k-card-icon">{icon}</div>
            <div class="k-card-label">{label}</div>
            <div class="k-card-value" style="font-size:{'22px' if isinstance(value, str) else '31px'}">{value}</div>
        </div>
        """
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown('<div class="k-section-title">تفصيل المشرفين</div>', unsafe_allow_html=True)
    breakdown = []
    for supervisor in supervisors:
        count = sum(
            1 for member in filtered_members
            if str(member.get("referrer_id")) == str(supervisor.get("id"))
        )
        breakdown.append({
            "المشرف": supervisor.get("name", ""),
            "اللقب": supervisor.get("nickname", ""),
            "عدد الأعضاء": count,
        })

    st.markdown('<div class="k-panel">', unsafe_allow_html=True)
    if breakdown:
        st.dataframe(pd.DataFrame(breakdown), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد بيانات.")
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":
    st.markdown('<div class="k-section-title">التصدير</div>', unsafe_allow_html=True)

    export_rows = [
        {
            "اللقب": m.get("nickname", ""),
            "الرقم": m.get("phone", ""),
            "من طرف": supervisor_name(supervisors, m.get("referrer_id")),
            "استقبله": supervisor_name(supervisors, m.get("receiver_id")),
            "تاريخ الإضافة": m.get("created_at", ""),
        }
        for m in members
    ]
    export_df = pd.DataFrame(export_rows)

    st.markdown('<div class="k-panel">', unsafe_allow_html=True)
    st.markdown("### تحميل البيانات")

    csv_data = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⇩ تحميل CSV",
        data=csv_data,
        file_name="konuha_members.csv",
        mime="text/csv",
        use_container_width=True,
    )

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Members")

    st.download_button(
        "⇩ تحميل Excel",
        data=excel_buffer.getvalue(),
        file_name="konuha_members.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        pdf_buffer = io.BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, y, "KONUHA Members")
        y -= 40
        pdf.setFont("Helvetica", 9)

        for member in members:
            line = f"{member.get('nickname','')} | {member.get('phone','')}"
            pdf.drawString(50, y, line[:95])
            y -= 17
            if y < 50:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 9)

        pdf.save()

        st.download_button(
            "⇩ تحميل PDF",
            data=pdf_buffer.getvalue(),
            file_name="konuha_members.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception:
        st.info("PDF غير متاح حالياً. تأكد من وجود reportlab.")

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":
    st.markdown('<div class="k-section-title">حذف عضو</div>', unsafe_allow_html=True)

    if not members:
        st.info("لا توجد أعضاء للحذف.")
    else:
        member_options = [m.get("nickname", "") for m in members]
        selected_nickname = st.selectbox("اختر العضو", member_options)
        selected_member = next(
            (m for m in members if m.get("nickname") == selected_nickname),
            None,
        )

        if selected_member:
            st.markdown(
                f"""
                <div class="k-panel" style="direction:rtl;text-align:right">
                    <div class="k-panel-title">معلومات العضو</div>
                    <div style="color:#c8ccd9;font:500 13px 'KonohaCairo',Cairo,sans-serif;line-height:2.1">
                        <b>اللقب:</b> {selected_member.get("nickname","")}<br>
                        <b>الرقم:</b> {selected_member.get("phone","")}<br>
                        <b>من طرف:</b> {supervisor_name(supervisors, selected_member.get("referrer_id"))}<br>
                        <b>استقبله:</b> {supervisor_name(supervisors, selected_member.get("receiver_id"))}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        confirm_delete = st.checkbox("أؤكد أنني أريد حذف هذا العضو نهائياً")
        delete_button = st.button("حذف العضو نهائياً", use_container_width=True)

        if delete_button:
            if not confirm_delete:
                st.warning("فعّل التأكيد أولاً.")
            elif selected_member and supabase is not None:
                try:
                    (
                        supabase.table("members")
                        .delete()
                        .eq("id", selected_member["id"])
                        .execute()
                    )
                    clear_database_cache()
                    st.success("تم حذف العضو بنجاح.")
                    st.rerun()
                except Exception as error:
                    st.error(f"حدث خطأ أثناء الحذف: {error}")
            elif supabase is None:
                st.error("قاعدة البيانات غير متصلة.")
