import streamlit as st
from supabase import create_client, Client
from pathlib import Path


# =========================================================
# KONUHA - Basic Configuration
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"


# =========================================================
# Supabase Connection
# =========================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

supabase: Client | None = None
supabase_connected = False

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # اختبار الاتصال بجدول المشرفين
        supabase.table("supervisors").select("id").limit(1).execute()

        supabase_connected = True

except Exception:
    supabase_connected = False


# =========================================================
# Fonts
# =========================================================

def load_font(filename: str) -> str:
    """
    Reads a font from the fonts folder and converts it
    to Base64 so it can be used directly in CSS.
    """
    import base64

    font_path = FONTS_DIR / filename

    if not font_path.exists():
        return ""

    try:
        encoded = base64.b64encode(
            font_path.read_bytes()
        ).decode("utf-8")

        return encoded

    except Exception:
        return ""


cairo_regular = load_font("Cairo-Regular.ttf")
cairo_medium = load_font("Cairo-Medium.ttf")
cairo_semibold = load_font("Cairo-SemiBold.ttf")
cairo_bold = load_font("Cairo-Bold.ttf")

inter_regular = load_font("Inter-Regular.ttf")
inter_medium = load_font("Inter-Medium.ttf")
inter_semibold = load_font("Inter-SemiBold.ttf")
inter_bold = load_font("Inter-Bold.ttf")

readex_regular = load_font("ReadexPro-Regular.ttf")
readex_medium = load_font("ReadexPro-Medium.ttf")
readex_semibold = load_font("ReadexPro-SemiBold.ttf")
readex_bold = load_font("ReadexPro-Bold.ttf")


# =========================================================
# CSS
# =========================================================

font_css = ""

if cairo_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_regular}) format('truetype');
        font-weight: 400;
    }}
    """

if cairo_medium:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_medium}) format('truetype');
        font-weight: 500;
    }}
    """

if cairo_semibold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_semibold}) format('truetype');
        font-weight: 600;
    }}
    """

if cairo_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_bold}) format('truetype');
        font-weight: 700;
    }}
    """


if inter_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_regular}) format('truetype');
        font-weight: 400;
    }}
    """

if inter_medium:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_medium}) format('truetype');
        font-weight: 500;
    }}
    """

if inter_semibold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_semibold}) format('truetype');
        font-weight: 600;
    }}
    """

if inter_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_bold}) format('truetype');
        font-weight: 700;
    }}
    """


if readex_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Readex';
        src: url(data:font/ttf;base64,{readex_regular}) format('truetype');
        font-weight: 400;
    }}
    """

if readex_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Readex';
        src: url(data:font/ttf;base64,{readex_bold}) format('truetype');
        font-weight: 700;
    }}
    """


st.markdown(
    f"""
    <style>

    {font_css}

    /* =========================================
       Hide Streamlit UI
       ========================================= */

    #MainMenu {{
        visibility: hidden;
    }}

    [data-testid="stToolbar"] {{
        visibility: hidden;
    }}

    header {{
        visibility: hidden;
    }}

    footer {{
        visibility: hidden;
    }}


    /* =========================================
       Main Application
       ========================================= */

    html, body, [class*="css"] {{
        font-family: 'KONUHA Cairo', 'KONUHA Inter', sans-serif;
    }}

    .stApp {{
        direction: rtl;
    }}

    .konuha-wrapper {{
        padding: 20px 10px;
    }}

    .konuha-title {{
        font-family: 'KONUHA Readex', 'KONUHA Cairo', sans-serif;
        font-size: 42px;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 0;
    }}

    .konuha-subtitle {{
        font-family: 'KONUHA Cairo', sans-serif;
        font-size: 16px;
        opacity: 0.65;
        margin-top: 4px;
    }}

    .status-card {{
        padding: 14px 18px;
        border-radius: 14px;
        margin-top: 20px;
        font-family: 'KONUHA Cairo', sans-serif;
        font-weight: 600;
    }}

    .status-online {{
        border: 1px solid rgba(46, 204, 113, 0.35);
        background: rgba(46, 204, 113, 0.08);
    }}

    .status-offline {{
        border: 1px solid rgba(231, 76, 60, 0.35);
        background: rgba(231, 76, 60, 0.08);
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center; padding:10px 0 25px 0;">
            <div style="
                font-family:'KONUHA Readex';
                font-size:30px;
                font-weight:700;
            ">
                KONUHA
            </div>

            <div style="opacity:.55; font-size:13px;">
                Work Management
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    page = st.radio(
        "القائمة",
        [
            "الرئيسية",
            "الأعضاء",
            "إضافة عضو",
            "المشرفين",
            "الإحصائيات",
            "التصدير",
            "الحذف",
        ],
    )


# =========================================================
# Main Header
# =========================================================

st.markdown(
    """
    <div class="konuha-wrapper">

        <div class="konuha-title">
            KONUHA
        </div>

        <div class="konuha-subtitle">
            نظام إدارة العمل
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Supabase Status
# =========================================================

if supabase_connected:

    st.markdown(
        """
        <div class="status-card status-online">
            🟢 قاعدة البيانات متصلة بـ Supabase
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    st.markdown(
        """
        <div class="status-card status-offline">
            🔴 قاعدة البيانات غير متصلة بـ Supabase
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Temporary Page Content
# =========================================================

if page == "الرئيسية":

    st.markdown("## مرحباً بك في KONUHA")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("الأعضاء", "—")

    with col2:
        st.metric("المشرفين", "—")

    with col3:
        st.metric("أعضاء اليوم", "—")


elif page == "الأعضاء":

    st.title("الأعضاء")
    st.info("قسم الأعضاء سيتم ربطه بقاعدة البيانات في الخطوة التالية.")


elif page == "إضافة عضو":

    st.title("إضافة عضو")
    st.info("نموذج إضافة العضو سيتم بناؤه بعد تثبيت الاتصال.")


elif page == "المشرفين":

    st.title("المشرفين")
    st.info("قسم المشرفين سيتم ربطه بجدول supervisors.")


elif page == "الإحصائيات":

    st.title("الإحصائيات")
    st.info("الإحصائيات سيتم بناؤها بعد ربط بيانات الأعضاء.")


elif page == "التصدير":

    st.title("التصدير")
    st.info("قسم التصدير سيتم تجهيزه لاحقًا.")


elif page == "الحذف":

    st.title("حذف عضو")
    st.info("قسم الحذف سيتم تجهيزه لاحقًا.")
