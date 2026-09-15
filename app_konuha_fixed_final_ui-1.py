
import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
import base64

import pandas as pd
import streamlit as st
from supabase import create_client

# =========================================================
# KONUHA
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Secrets ----------
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
SITE_PASSWORD = st.secrets.get("SITE_PASSWORD", "")


# ---------- Database ----------
@st.cache_resource
def get_db():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


db = get_db()


@st.cache_data(ttl=10)
def online():
    if db is None:
        return False
    try:
        db.table("supervisors").select("id").limit(1).execute()
        return True
    except Exception:
        return False


@st.cache_data(ttl=10)
def members_data():
    if db is None:
        return []
    try:
        return (
            db.table("members")
            .select("*")
            .order("created_at", desc=True)
            .execute()
            .data or []
        )
    except Exception:
        return []


@st.cache_data(ttl=10)
def supervisors_data():
    if db is None:
        return []
    try:
        return (
            db.table("supervisors")
            .select("*")
            .order("created_at")
            .execute()
            .data or []
        )
    except Exception:
        return []


def refresh():
    members_data.clear()
    supervisors_data.clear()
    online.clear()


def set_flash(message, kind="success"):
    st.session_state["konuha_flash"] = {
        "message": message,
        "kind": kind,
    }


def show_flash():
    flash = st.session_state.pop("konuha_flash", None)
    if not flash:
        return

    kind = flash.get("kind", "success")
    message = flash.get("message", "")

    if kind == "error":
        st.error(message)
    elif kind == "warning":
        st.warning(message)
    else:
        st.success(message)


# ---------- Arabic helpers ----------
def norm(text):
    text = str(text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    for a, b in {
        "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
        "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي", "ـ": "",
    }.items():
        text = text.replace(a, b)
    return re.sub(r"[^\w\u0600-\u06ff]+", "", text)


def phone_clean(value):
    return re.sub(r"\D", "", str(value or ""))


def similarity(a, b):
    from difflib import SequenceMatcher
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def as_date(value):
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def fmt_dt(value):
    try:
        d = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        return d.strftime("%Y-%m-%d  %H:%M")
    except Exception:
        return str(value or "-")


def supervisor_by_id(items, sid):
    for s in items:
        if str(s.get("id")) == str(sid):
            return s
    return None


def supervisor_by_name(items, name):
    target = norm(name)
    for s in items:
        if norm(s.get("name", "")) == target:
            return s
    return None



# ---------- Local fonts + export reports ----------
APP_DIR = Path(__file__).resolve().parent
FONT_DIR = APP_DIR / "fonts"

def font_file(*names):
    for name in names:
        p = FONT_DIR / name
        if p.exists():
            return p
    return None

def first_glob(*patterns):
    if not FONT_DIR.exists():
        return None
    for pattern in patterns:
        matches = sorted(FONT_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None

CAIRO_FONTS = {}  # Cairo disabled: avoid missing-glyph squares in exports.

READEX_FONTS = {
    200: font_file("ReadexPro-ExtraLight.ttf"),
    300: font_file("ReadexPro-Light.ttf"),
    400: font_file("ReadexPro-Regular.ttf"),
    500: font_file("ReadexPro-Medium.ttf"),
    600: font_file("ReadexPro-SemiBold.ttf"),
    700: font_file("ReadexPro-Bold.ttf"),
}
TAJAWAL_FONTS = {
    200: font_file("Tajawal-ExtraLight.ttf"),
    300: font_file("Tajawal-Light.ttf"),
    400: font_file("Tajawal-Regular.ttf"),
    500: font_file("Tajawal-Medium.ttf"),
    700: font_file("Tajawal-Bold.ttf"),
    800: font_file("Tajawal-ExtraBold.ttf"),
    900: font_file("Tajawal-Black.ttf"),
}
INTER_FONTS = {
    200: font_file("Inter_18pt-ExtraLight.ttf"),
    300: font_file("Inter_18pt-Light.ttf"),
    400: font_file("Inter_18pt-Regular.ttf"),
    500: font_file("Inter_18pt-Medium.ttf"),
    600: font_file("Inter_18pt-SemiBold.ttf"),
    700: font_file("Inter_18pt-Bold.ttf"),
    800: font_file("Inter_18pt-ExtraBold.ttf"),
    900: font_file("Inter_18pt-Black.ttf"),
}
INTER_VARIABLE = first_glob("Inter-VariableFont*.ttf")


def font_face_css(family, path, weight, style="normal"):
    if not path or not path.exists():
        return ""
    try:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"""
        @font-face {{
            font-family: '{family}';
            src: url(data:font/ttf;base64,{encoded}) format('truetype');
            font-weight: {weight};
            font-style: {style};
            font-display: swap;
        }}
        """
    except Exception:
        return ""

LOCAL_FONT_CSS = ""
for weight, path in READEX_FONTS.items():
    LOCAL_FONT_CSS += font_face_css("Readex Pro", path, weight)
for weight, path in TAJAWAL_FONTS.items():
    LOCAL_FONT_CSS += font_face_css("Tajawal", path, weight)
for weight, path in INTER_FONTS.items():
    LOCAL_FONT_CSS += font_face_css("Inter", path, weight)
if INTER_VARIABLE:
    LOCAL_FONT_CSS += font_face_css("Inter Variable", INTER_VARIABLE, "100 900")

TAJAWAL_REGULAR = TAJAWAL_FONTS.get(400) or first_glob("Tajawal-*.ttf")
TAJAWAL_BOLD = TAJAWAL_FONTS.get(700) or TAJAWAL_FONTS.get(800) or TAJAWAL_REGULAR
READEX_REGULAR = READEX_FONTS.get(400) or first_glob("ReadexPro-*.ttf")
READEX_BOLD = READEX_FONTS.get(700) or READEX_FONTS.get(600) or READEX_REGULAR

CSS = """
    <style>
        /* Local font faces are injected below by Streamlit */
__LOCAL_FONT_CSS__
    :root {
        --bg: #080910;
        --panel: #10121c;
        --panel2: #151827;
        --line: #24283a;
        --text: #f4f5f8;
        --muted: #9da3b5;
        --accent: #8b5cf6;
        --accent2: #d946ef;
        --good: #35d399;
        --danger: #fb7185;
    }

    html, body, [class*="st-"] {
        font-family: Tajawal, "Readex Pro", sans-serif !important;
    }

    .stApp {
        background:
            radial-gradient(900px 500px at 90% -10%, rgba(139,92,246,.12), transparent 60%),
            radial-gradient(700px 450px at -10% 100%, rgba(217,70,239,.07), transparent 60%),
            var(--bg);
        color: var(--text);
        min-height: 100vh;
        position: relative;
        overflow-x: hidden;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: -20%;
        pointer-events: none;
        z-index: 0;
        background:
            radial-gradient(circle at 20% 30%, rgba(139,92,246,.10), transparent 25%),
            radial-gradient(circle at 80% 20%, rgba(217,70,239,.09), transparent 22%),
            radial-gradient(circle at 60% 90%, rgba(80,120,255,.06), transparent 24%);
        animation: konuha-glow 12s ease-in-out infinite alternate;
    }

    @keyframes konuha-glow {
        0% { transform: translate3d(-2%, -1%, 0) scale(1); opacity: .72; }
        100% { transform: translate3d(2%, 2%, 0) scale(1.06); opacity: 1; }
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer,
    [data-testid="stSidebar"] {
        visibility: hidden;
        height: 0;
    }

    .block-container {
        position: relative;
        z-index: 1;
        max-width: 1380px;
        padding: 28px 30px 55px;
        animation: konuha-enter .45s ease-out;
    }

    @keyframes konuha-enter {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    [data-testid="stMetric"],
    .stAlert,
    [data-testid="stForm"] {
        animation: konuha-card .35s ease-out both;
    }

    @keyframes konuha-card {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: translateY(0); }
    }

    h1, h2, h3 {
        letter-spacing: -.02em;
    }

    .brand-title {
        font-size: 30px;
        font-weight: 850;
        letter-spacing: .12em;
        margin-bottom: 0;
    }

    .brand-sub {
        color: var(--muted);
        font-size: 13px;
        margin-top: -5px;
    }

    .status {
        color: var(--good);
        font-weight: 700;
        text-align: right;
        padding-top: 8px;
    }

    .status-off {
        color: var(--danger);
        font-weight: 700;
        text-align: right;
        padding-top: 8px;
    }

    .hero-title {
        font-size: clamp(38px, 6vw, 72px);
        font-weight: 900;
        line-height: 1;
        margin: 14px 0 10px;
        background: linear-gradient(90deg, #fff, #b79cff 55%, #ee82df);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }

    .hero-copy {
        color: var(--muted);
        font-size: 16px;
        max-width: 680px;
    }

    .card {
        background: linear-gradient(145deg, rgba(20,23,36,.96), rgba(12,14,23,.96));
        border: 1px solid var(--line);
        border-radius: 20px;
        padding: 20px;
    }

    .section-label {
        color: #c7cbd8;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .04em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .stButton > button {
        border-radius: 12px;
        border: 1px solid #292d40;
        background: #111421;
        color: #eef0f5;
        font-weight: 650;
        min-height: 42px;
    }

    .stButton > button:hover {
        border-color: #7654cf;
        background: #171a2b;
    }

    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input {
        background: #0d1019;
        border: 1px solid #292d40;
        border-radius: 12px;
    }

    div[data-baseweb="select"] > div {
        background: #0d1019;
        border-color: #292d40;
        border-radius: 12px;
    }

    [data-testid="stMetric"] {
        background: #10131e;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    [data-testid="stMetricValue"] {
        font-weight: 850;
    }

    .stDataFrame {
        border: 1px solid var(--line);
        border-radius: 14px;
    }


    h1, h2, h3, h4, h5, h6, .hero-title, .brand-title {
        font-family: "Readex Pro", Tajawal, sans-serif !important;
    }

    .stButton > button, .stTextInput input, .stTextArea textarea,
    div[data-baseweb="select"] *, label, .stCaption, .stMarkdown,
    [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stAlert"] {
        font-family: Tajawal, "Readex Pro", sans-serif !important;
    }

    .brand-title, .hero-title {
        font-family: Inter, "Readex Pro", sans-serif !important;
    }
    /* KONUHA explanation cards */
    .k-section-info {
        width:100% !important;
        margin:22px 0 26px !important;
        padding:24px !important;
        border:1px solid rgba(139,92,246,.28) !important;
        border-radius:22px !important;
        background:linear-gradient(145deg,rgba(21,24,39,.98),rgba(12,14,24,.98)) !important;
        box-shadow:0 18px 45px rgba(0,0,0,.22), inset 0 1px 0 rgba(255,255,255,.035) !important;
        direction:rtl !important;
    }
    .k-section-top {
        display:flex !important; align-items:flex-start !important; justify-content:space-between !important;
        gap:18px !important; margin-bottom:18px !important;
    }
    .k-eyebrow {
        color:#a78bfa !important; font-size:12px !important; font-weight:800 !important;
        letter-spacing:.08em !important; margin-bottom:7px !important;
    }
    .k-section-title {
        color:#fff !important; font-family:"Readex Pro",Tajawal,sans-serif !important;
        font-size:clamp(20px,2.2vw,28px) !important; font-weight:800 !important;
        line-height:1.35 !important; margin:0 !important;
    }
    .k-section-sub {
        color:#aeb4c5 !important; font-size:14px !important; line-height:1.9 !important;
        margin-top:7px !important; max-width:760px !important;
    }
    .k-section-badge {
        flex:0 0 auto !important; padding:9px 13px !important; border-radius:12px !important;
        border:1px solid rgba(139,92,246,.25) !important;
        background:rgba(139,92,246,.09) !important; color:#cfc5ff !important;
        font-size:12px !important; font-weight:700 !important; white-space:nowrap !important;
    }
    .k-info-grid {
        display:grid !important; grid-template-columns:repeat(3,minmax(0,1fr)) !important;
        gap:12px !important; width:100% !important;
    }
    .k-info-item {
        display:flex !important; align-items:flex-start !important; gap:12px !important;
        min-height:104px !important; padding:16px !important;
        border:1px solid rgba(255,255,255,.07) !important; border-radius:16px !important;
        background:linear-gradient(145deg,rgba(28,31,48,.88),rgba(17,19,30,.88)) !important;
        box-sizing:border-box !important; direction:rtl !important;
        transition:transform .2s ease,border-color .2s ease,background .2s ease !important;
    }
    .k-info-item:hover {
        transform:translateY(-2px) !important; border-color:rgba(139,92,246,.38) !important;
        background:linear-gradient(145deg,rgba(34,37,57,.95),rgba(18,20,32,.95)) !important;
    }
    .k-info-emoji {
        flex:0 0 42px !important; width:42px !important; height:42px !important;
        display:flex !important; align-items:center !important; justify-content:center !important;
        border-radius:12px !important; background:rgba(139,92,246,.12) !important;
        border:1px solid rgba(139,92,246,.2) !important; font-size:20px !important;
    }
    .k-info-title {
        color:#f5f6fa !important; font-family:"Readex Pro",Tajawal,sans-serif !important;
        font-size:15px !important; font-weight:800 !important; line-height:1.5 !important;
        margin:0 0 4px !important;
    }
    .k-info-text {
        color:#9da3b5 !important; font-family:Tajawal,"Readex Pro",sans-serif !important;
        font-size:13px !important; line-height:1.75 !important; margin:0 !important;
    }

    .k-section-info, .k-home-showcase, .card { overflow:hidden !important; box-sizing:border-box !important; }
    .k-section-top { display:flex !important; flex-wrap:wrap !important; min-width:0 !important; }
    .k-section-top > div:first-child { flex:1 1 520px !important; min-width:0 !important; }
    .k-section-sub, .k-showcase-sub, .k-info-text, .k-feature span, .hero-copy {
        max-width:100% !important; min-width:0 !important; overflow-wrap:anywhere !important; word-break:normal !important;
        white-space:normal !important; direction:rtl !important;
    }
    .k-info-grid, .k-feature-grid { grid-template-columns:repeat(3,minmax(0,1fr)) !important; min-width:0 !important; }
    .k-info-item, .k-feature { min-width:0 !important; overflow:hidden !important; box-sizing:border-box !important; }
    .k-info-item > div:last-child, .k-feature > div:last-child { min-width:0 !important; overflow:hidden !important; }

    @media (max-width: 800px) {
        .block-container {
            padding: 18px 14px 40px;
        }
        .brand-title {
            font-size: 24px;
        }
        .hero-copy {
            font-size: 14px;
        }
        .k-showcase-head {
            flex-direction: column;
        }
        .k-feature-grid, .k-info-grid {
            grid-template-columns: 1fr !important;
        }
        .k-home-showcase {
            padding: 20px;
        }
    }
    </style>
    """

CSS = CSS.replace("__LOCAL_FONT_CSS__", LOCAL_FONT_CSS)
st.markdown(
    CSS,
    unsafe_allow_html=True,
)


# =========================================================
# LOGIN
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.write("")
    st.write("")
    st.title("KONUHA")
    st.caption("لوحة إدارة الأعضاء والمشرفين")

    with st.form("login"):
        password = st.text_input("كلمة المرور", type="password")
        enter = st.form_submit_button("دخول", use_container_width=True)

    if enter:
        if SITE_PASSWORD and password == SITE_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة.")
    st.stop()


# =========================================================
# DATA / NAV
# =========================================================

members = members_data()
supervisors = supervisors_data()
db_ok = online()

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"


# Header
left, mid, right = st.columns([3.5, 3, 1.2])

with left:
    st.markdown("KONUHA", unsafe_allow_html=False)
    st.caption("CONTROL CENTER")

with mid:
    st.write("")

with right:
    if db_ok:
        st.success("متصل")
    else:
        st.error("غير متصل")


# Main navigation: compact, not a stack of giant buttons
nav_items = [
    ("🏠", "الرئيسية"),
    ("👥", "الأعضاء"),
    ("➕", "الإضافة"),
    ("🛡️", "المشرفين"),
    ("✏️", "التعديل"),
    ("📊", "الإحصائيات"),
    ("🗑️", "الحذف"),
]
nav_labels = [f"{emoji}  {label}" for emoji, label in nav_items]
label_to_page = {f"{emoji}  {label}": label for emoji, label in nav_items}
current_label = next((f"{e}  {l}" for e, l in nav_items if l == st.session_state.page), nav_labels[0])
current_index = nav_labels.index(current_label)

choice_label = st.radio(
    "التنقل",
    nav_labels,
    index=current_index,
    horizontal=True,
    label_visibility="collapsed",
)

choice = label_to_page[choice_label]
if choice != st.session_state.page:
    st.session_state.page = choice
    st.rerun()

st.divider()

show_flash()

# =========================================================
# Decorative section helpers
# =========================================================

def section_info(title, subtitle, items, badge="KONUHA ✦"):
    cards = "".join(
        '<div class="k-info-item"><div class="k-info-emoji">' + emoji + '</div><div><div class="k-info-title">' + label + '</div><div class="k-info-text">' + text + '</div></div></div>'
        for emoji, label, text in items
    )
    html = (
        '<div class="k-section-info">'
        '<div class="k-section-top"><div><div class="k-eyebrow">' + badge + '</div>'
        '<div class="k-section-title">' + title + '</div><div class="k-section-sub">' + subtitle + '</div></div>'
        '<div class="k-section-badge">✦ مرتب • واضح • سريع</div></div>'
        '<div class="k-info-grid">' + cards + '</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.markdown("KONUHA", unsafe_allow_html=False)
    st.title("لوحة التحكم")
    st.write("إدارة الأعضاء والمشرفين والإحصائيات من مكان واحد.")

    section_info("نظرة سريعة على KONUHA", "واجهة واحدة تجمع بياناتك الأساسية وتخلي المتابعة أسرع وأوضح.", [("👥", "الأعضاء", "تابع عدد الأعضاء وآخر الإضافات بسرعة."), ("🛡️", "المشرفون", "اعرف المشرفين وحالتهم ومهامهم."), ("📊", "الإحصائيات", "راجع النشاط حسب المشرف والفترة."), ("⚡", "سرعة الاستخدام", "تنقل واضح ووصول مباشر لكل قسم."), ("🔒", "بيانات منظمة", "المعلومات تُقرأ من قاعدة KONUHA مباشرة.")])

    today = date.today()
    today_count = sum(
        as_date(m.get("created_at")) == today
        for m in members
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الأعضاء", len(members))
    c2.metric("المشرفون", len(supervisors))
    c3.metric("إضافات اليوم", today_count)
    c4.metric("قاعدة البيانات", "متصلة" if db_ok else "غير متصلة")

    st.subheader("آخر الأعضاء")

    rows = []
    for m in members[:8]:
        rows.append({
            "اللقب": m.get("nickname", ""),
            "الرقم": m.get("phone", ""),
            "من طرف": (supervisor_by_id(supervisors, m.get("referrer_id")) or {}).get("name", "-"),
            "استقبله": (supervisor_by_id(supervisors, m.get("receiver_id")) or {}).get("name", "-"),
            "تاريخ الإضافة": fmt_dt(m.get("created_at")),
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد أعضاء بعد.")

    st.markdown("""
    <div class="k-home-showcase">
        <div class="k-showcase-head">
            <div>
                <div class="k-eyebrow">KONUHA • CONTROL CENTER</div>
                <div class="k-showcase-title">كل شيء مرتب، واضح، وبمكان واحد ✦</div>
                <div class="k-showcase-sub">لوحة KONUHA تساعدك على إدارة الأعضاء والمشرفين ومراجعة الإحصائيات بسرعة، مع واجهة هادئة ومباشرة.</div>
            </div>
            <div class="k-showcase-badge">⚡ إدارة أسرع</div>
        </div>
        <div class="k-feature-grid">
            <div class="k-feature"><div class="k-feature-icon">👥</div><div><b>إدارة الأعضاء</b><span>إضافة، تعديل، فحص، وحذف بيانات الأعضاء من مكان واحد.</span></div></div>
            <div class="k-feature"><div class="k-feature-icon">🛡️</div><div><b>إدارة المشرفين</b><span>متابعة المشرفين ورتبهم وحالة كل مشرف بسهولة.</span></div></div>
            <div class="k-feature"><div class="k-feature-icon">📊</div><div><b>إحصائيات واضحة</b><span>أرقام وتقارير تساعدك على متابعة النشاط حسب الفترة والمشرف.</span></div></div>
            <div class="k-feature"><div class="k-feature-icon">✨</div><div><b>هوية KONUHA</b><span>تصميم موحد وسريع ومخصص ليبقى استخدام النظام مريحًا.</span></div></div>
        </div>
        <div class="k-home-note">© KONUHA — نظام إدارة الأعضاء والمشرفين • صُمم ليبقى بسيطًا ومرتبًا.</div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":

    st.title("الأعضاء")

    section_info("قسم الأعضاء", "راجع السجلات وابحث عن لقب أو رقم واستعرض البيانات بشكل مرتب.", [("🔎", "البحث", "اكتب اللقب أو الرقم للوصول للعضو."), ("🧾", "السجل", "يعرض الرقم والمشرفين وتاريخ الإضافة."), ("✨", "عرض واضح", "البيانات تظهر في جدول واحد سهل القراءة.")])

    search = st.text_input("بحث", placeholder="اللقب أو الرقم")

    q = norm(search)
    rows = []

    for m in members:
        nickname = m.get("nickname", "")
        phone = str(m.get("phone", ""))

        if search and q not in norm(nickname) and search not in phone:
            continue

        rows.append({
            "اللقب": nickname,
            "الرقم": phone,
            "من طرف": (supervisor_by_id(supervisors, m.get("referrer_id")) or {}).get("name", "-"),
            "استقبله": (supervisor_by_id(supervisors, m.get("receiver_id")) or {}).get("name", "-"),
            "تاريخ الإضافة": fmt_dt(m.get("created_at")),
        })

    st.metric("عدد النتائج", len(rows))

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد نتائج.")


# =========================================================
# ADDITION - MEMBER + SUPERVISOR IN SAME PAGE
# =========================================================

elif st.session_state.page == "الإضافة":

    st.title("الإضافة")

    section_info("قسم الإضافة", "اختر نوع السجل ثم عبّي الحقول المطلوبة. النظام يفحص التكرار قبل الحفظ.", [("➕", "إضافة عضو", "اللقب والرقم والمشرفون المرتبطون بالعضو."), ("⚠️", "التكرار", "اللقب الموجود مسبقًا يحتاج إضافة إجبارية عند كونه شخصًا مختلفًا."), ("🛡️", "إضافة مشرف", "أضف اسم المشرف ولقبه ليظهر لاحقًا في الاختيارات.")])

    add_type = st.radio(
        "نوع الإضافة",
        ["عضو", "مشرف"],
        horizontal=True,
    )

    st.divider()

    # ---------- ADD MEMBER ----------
    if add_type == "عضو":

        st.subheader("إضافة عضو")

        if not supervisors:
            st.warning("أضف مشرفاً أولاً قبل إضافة الأعضاء.")
        else:

            active = [
                s for s in supervisors
                if s.get("is_active", True)
            ]

            names = [s.get("name", "") for s in active]

            with st.form("add_member"):

                a, b = st.columns(2)

                with a:
                    nickname = st.text_input("اللقب")
                    phone = st.text_input("الرقم")

                with b:
                    referrer = st.selectbox("من طرف", names)
                    receiver = st.selectbox("استقبله", names)

                force = st.checkbox("إضافة إجبارية عند وجود لقب مشابه")

                submit = st.form_submit_button(
                    "إضافة العضو",
                    use_container_width=True,
                )

            if submit:

                nickname = nickname.strip()
                phone = phone_clean(phone)

                if not nickname or not phone:
                    st.error("اللقب والرقم مطلوبان.")

                elif not db_ok:
                    st.error("قاعدة البيانات غير متصلة.")

                elif any(str(m.get("phone", "")) == phone for m in members):
                    st.error("هذا الرقم مسجل مسبقاً.")

                else:

                    nickname_norm = norm(nickname)
                    exact_nickname = [
                        x for x in members
                        if norm(x.get("nickname", "")) == nickname_norm
                    ]
                    similar = [
                        x for x in members
                        if norm(x.get("nickname", "")) != nickname_norm
                        and similarity(x.get("nickname", ""), nickname) >= 0.82
                    ]

                    # Exact nickname duplicates are blocked too. The force
                    # option is the explicit override, while duplicate phone
                    # numbers remain blocked above.
                    if (exact_nickname or similar) and not force:

                        if exact_nickname:
                            names_found = ", ".join(
                                x.get("nickname", "")
                                for x in exact_nickname
                            )
                            st.warning(
                                f"اللقب {names_found} موجود مسبقاً. "
                                "إذا كان هذا شخصاً مختلفاً، فعّل الإضافة الإجبارية حتى تتم إضافته."
                            )
                        else:
                            names_found = ", ".join(
                                x.get("nickname", "")
                                for x in similar
                            )
                            st.warning(
                                f"يوجد لقب مشابه: {names_found}. "
                                "فعّل الإضافة الإجبارية إذا كان مختلفاً."
                            )

                    else:

                        r = supervisor_by_name(supervisors, referrer)
                        receiver_obj = supervisor_by_name(supervisors, receiver)

                        try:
                            db.table("members").insert({
                                "nickname": nickname,
                                "normalized_nickname": norm(nickname),
                                "phone": phone,
                                "referrer_id": r["id"],
                                "receiver_id": receiver_obj["id"],
                            }).execute()

                            refresh()
                            set_flash("تمت إضافة العضو بنجاح ✓")
                            st.rerun()

                        except Exception as e:
                            st.error(f"تعذر الإضافة: {e}")

    # ---------- ADD SUPERVISOR ----------
    else:

        st.subheader("إضافة مشرف")

        with st.form("add_supervisor"):

            a, b = st.columns(2)

            with a:
                name = st.text_input("اسم المشرف")

            with b:
                nickname = st.text_input("اللقب / الرتبة")

            submit = st.form_submit_button(
                "إضافة المشرف",
                use_container_width=True,
            )

        if submit:

            name = name.strip()
            nickname = nickname.strip()

            if not name or not nickname:
                st.error("الاسم واللقب مطلوبان.")

            elif not db_ok:
                st.error("قاعدة البيانات غير متصلة.")

            elif any(norm(s.get("name", "")) == norm(name) for s in supervisors):
                st.error("هذا المشرف موجود مسبقاً.")

            else:

                try:

                    db.table("supervisors").insert({
                        "name": name,
                        "nickname": nickname,
                        "normalized_name": norm(name),
                        "normalized_nickname": norm(nickname),
                        "is_active": True,
                    }).execute()

                    refresh()
                    set_flash("تمت إضافة المشرف بنجاح ✓")
                    st.rerun()

                except Exception as e:
                    st.error(f"تعذر إضافة المشرف: {e}")


# =========================================================
# SUPERVISORS - WITH RECEIVED / REFERRED COUNTS
# =========================================================

elif st.session_state.page == "المشرفين":

    st.title("المشرفون")

    section_info("قسم المشرفين", "متابعة أسماء المشرفين ورتبهم وعدد السجلات المرتبطة بكل مشرف.", [("🛡️", "الحالة", "فعال أو غير فعال حسب إعداد المشرف."), ("📥", "الاستقبال", "عدد الأعضاء الذين استقبلهم المشرف."), ("📤", "الإحالات", "عدد الأعضاء المسجلين من طرف المشرف.")])

    rows = []

    for s in supervisors:

        sid = str(s.get("id"))

        referred = sum(
            str(m.get("referrer_id")) == sid
            for m in members
        )

        received = sum(
            str(m.get("receiver_id")) == sid
            for m in members
        )

        rows.append({
            "الاسم": s.get("name", ""),
            "الرتبة / اللقب": s.get("nickname", ""),
            "من طرفه": referred,
            "استقبل": received,
            "الإجمالي": referred + received,
            "الحالة": "فعال" if s.get("is_active", True) else "غير فعال",
        })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("لا يوجد مشرفون.")


# =========================================================
# EDIT SUPERVISOR
# =========================================================

elif st.session_state.page == "التعديل":

    st.title("تعديل البيانات")

    section_info("قسم التعديل", "غيّر بيانات المشرف أو العضو مع الحفاظ على الربط مع قاعدة البيانات.", [("✏️", "تحديث", "عدّل الاسم أو اللقب أو البيانات المرتبطة."), ("🔁", "الربط", "حدّد من طرفه واستقبله عند تعديل العضو."), ("✅", "حفظ", "يتم تحديث السجل مباشرة بعد الحفظ.")])

    edit_type = st.radio(
        "ماذا تريد تعديل؟",
        ["مشرف", "عضو"],
        horizontal=True,
    )

    st.divider()

    # ---------- EDIT SUPERVISOR ----------
    if edit_type == "مشرف":

        if not supervisors:
            st.info("لا يوجد مشرفون.")
        else:

            options = {
                f'{s.get("name", "")} — {s.get("nickname", "")}': s
                for s in supervisors
            }

            selected = st.selectbox(
                "اختر المشرف",
                list(options.keys()),
            )

            selected_supervisor = options[selected]

            with st.form("edit_supervisor"):

                name = st.text_input(
                    "اسم المشرف",
                    value=selected_supervisor.get("name", ""),
                )

                nickname = st.text_input(
                    "اللقب / الرتبة",
                    value=selected_supervisor.get("nickname", ""),
                )

                active = st.checkbox(
                    "المشرف فعال",
                    value=selected_supervisor.get("is_active", True),
                )

                save = st.form_submit_button(
                    "حفظ التعديلات",
                    use_container_width=True,
                )

            if save:

                name = name.strip()
                nickname = nickname.strip()

                if not name or not nickname:
                    st.error("الاسم واللقب مطلوبان.")

                elif not db_ok:
                    st.error("قاعدة البيانات غير متصلة.")

                else:

                    try:

                        db.table("supervisors").update({
                            "name": name,
                            "nickname": nickname,
                            "normalized_name": norm(name),
                            "normalized_nickname": norm(nickname),
                            "is_active": active,
                        }).eq(
                            "id",
                            selected_supervisor["id"],
                        ).execute()

                        refresh()
                        set_flash("تم تحديث معلومات المشرف بنجاح ✓")
                        st.rerun()

                    except Exception as e:
                        st.error(f"تعذر التعديل: {e}")

    # ---------- EDIT MEMBER ----------
    else:

        if not members:
            st.info("لا يوجد أعضاء.")
        else:

            options = {
                f'{m.get("nickname", "")} — {m.get("phone", "")}': m
                for m in members
            }

            selected = st.selectbox(
                "اختر العضو",
                list(options.keys()),
            )

            member = options[selected]

            active = [
                s for s in supervisors
                if s.get("is_active", True)
            ]

            names = [s.get("name", "") for s in active]

            current_ref = (supervisor_by_id(supervisors, member.get("referrer_id")) or {}).get("name", "")
            current_receiver = (supervisor_by_id(supervisors, member.get("receiver_id")) or {}).get("name", "")

            with st.form("edit_member"):

                nickname = st.text_input(
                    "اللقب",
                    value=member.get("nickname", ""),
                )

                phone = st.text_input(
                    "الرقم",
                    value=member.get("phone", ""),
                )

                ref_index = names.index(current_ref) if current_ref in names else 0
                receiver_index = names.index(current_receiver) if current_receiver in names else 0

                referrer = st.selectbox(
                    "من طرف",
                    names,
                    index=ref_index,
                )

                receiver = st.selectbox(
                    "استقبله",
                    names,
                    index=receiver_index,
                )

                save = st.form_submit_button(
                    "حفظ التعديلات",
                    use_container_width=True,
                )

            if save:

                nickname = nickname.strip()
                phone = phone_clean(phone)

                if not nickname or not phone:
                    st.error("اللقب والرقم مطلوبان.")

                else:

                    ref = supervisor_by_name(supervisors, referrer)
                    rec = supervisor_by_name(supervisors, receiver)

                    try:

                        db.table("members").update({
                            "nickname": nickname,
                            "normalized_nickname": norm(nickname),
                            "phone": phone,
                            "referrer_id": ref["id"],
                            "receiver_id": rec["id"],
                        }).eq(
                            "id",
                            member["id"],
                        ).execute()

                        refresh()
                        set_flash("تم تحديث معلومات العضو بنجاح ✓")
                        st.rerun()

                    except Exception as e:
                        st.error(f"تعذر التعديل: {e}")


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":

    st.title("الإحصائيات")

    section_info("قسم الإحصائيات", "حدد المشرف والفترة للحصول على أرقام أقرب لما تحتاجه.", [("📅", "الفترة", "كل الوقت أو اليوم أو أمس أو الشهر الحالي."), ("🧑‍💼", "المشرف", "فلترة النتائج حسب المشرف."), ("📈", "قراءة سريعة", "يعرض العدد والإجماليات بطريقة مباشرة.")])

    c1, c2 = st.columns(2)

    with c1:
        selected_supervisor = st.selectbox(
            "المشرف",
            ["الكل"] + [s.get("name", "") for s in supervisors],
        )

    with c2:
        period = st.selectbox(
            "الفترة",
            ["كل الوقت", "اليوم", "امس", "هذا_الشهر", "تاريخ محدد"],
        )

    chosen_date = None

    if period == "تاريخ محدد":
        chosen_date = st.date_input(
            "التاريخ",
            value=date.today(),
        )

    filtered = []

    for m in members:

        if selected_supervisor != "الكل":

            s = supervisor_by_id(
                supervisors,
                m.get("referrer_id"),
            )

            if not s or s.get("name") != selected_supervisor:
                continue

        d = as_date(m.get("created_at"))

        keep = True

        if period == "اليوم":
            keep = d == date.today()

        elif period == "امس":
            keep = d == date.today() - timedelta(days=1)

        elif period == "هذا_الشهر":
            keep = (
                d is not None
                and d.year == date.today().year
                and d.month == date.today().month
            )

        elif period == "تاريخ محدد":
            keep = d == chosen_date

        if keep:
            filtered.append(m)

    st.metric("الأعضاء ضمن الاختيار", len(filtered))

    rows = []

    for s in supervisors:

        sid = str(s.get("id"))

        referred = sum(
            str(m.get("referrer_id")) == sid
            for m in filtered
        )

        received = sum(
            str(m.get("receiver_id")) == sid
            for m in filtered
        )

        rows.append({
            "المشرف": s.get("name", ""),
            "الرتبة / اللقب": s.get("nickname", ""),
            "من طرفه": referred,
            "استقبل": received,
            "الإجمالي": referred + received,
        })

    if rows:
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":

    st.title("التصدير")

    section_info("قسم التصدير", "صدّر بيانات KONUHA بصيغ عملية بدون تقارير صور أو PDF.", [("📊", "Excel", "ملف مرتب لفتح البيانات وتعديلها."), ("🧾", "CSV", "نسخة خفيفة مناسبة للحفظ والاستيراد."), ("🚫", "PNG / PDF", "تم إلغاء تقارير الصور وPDF حتى يبقى النظام أبسط.")])

    rows = []

    for m in members:

        rows.append({
            "اللقب": m.get("nickname", ""),
            "الرقم": m.get("phone", ""),
            "من طرف": (supervisor_by_id(supervisors, m.get("referrer_id")) or {}).get("name", "-"),
            "استقبله": (supervisor_by_id(supervisors, m.get("receiver_id")) or {}).get("name", "-"),
            "تاريخ الإضافة": fmt_dt(m.get("created_at")),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        st.info("لا توجد بيانات.")
    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "تحميل CSV",
            csv_data,
            "konuha_members.csv",
            "text/csv",
            use_container_width=True,
        )

        excel = io.BytesIO()

        with pd.ExcelWriter(
            excel,
            engine="openpyxl",
        ) as writer:
            df.to_excel(
                writer,
                index=False,
                sheet_name="Members",
            )

        st.download_button(
            "تحميل Excel",
            excel.getvalue(),
            "konuha_members.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.info("تم إلغاء تصدير PNG وPDF. المتاح هنا حاليًا: CSV وExcel.")


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":

    st.title("حذف عضو")

    section_info("قسم الحذف", "الحذف نهائي، لذلك يظهر لك العضو والرقم قبل تنفيذ العملية.", [("🗑️", "اختيار", "حدد السجل الذي تريد حذفه."), ("⚠️", "تأكيد", "يجب تفعيل تأكيد الحذف قبل التنفيذ."), ("🔒", "نهائي", "بعد التنفيذ يُحذف السجل من قاعدة البيانات.")])

    if not members:

        st.info("لا توجد أعضاء.")

    else:

        options = {
            f'{m.get("nickname", "")} — {m.get("phone", "")}': m
            for m in members
        }

        selected = st.selectbox(
            "اختر العضو",
            list(options.keys()),
        )

        member = options[selected]

        st.warning(
            f"سيتم حذف: {member.get('nickname', '')} — {member.get('phone', '')}"
        )

        confirm = st.checkbox(
            "أؤكد الحذف النهائي"
        )

        if st.button(
            "حذف العضو",
            use_container_width=True,
            disabled=not confirm,
        ):

            try:

                db.table("members").delete().eq(
                    "id",
                    member["id"],
                ).execute()

                refresh()
                set_flash("تم حذف العضو بنجاح ✓")
                st.rerun()

            except Exception as e:
                st.error(f"تعذر الحذف: {e}")
