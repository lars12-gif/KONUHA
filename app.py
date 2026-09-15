import streamlit as st
import pandas as pd
import base64
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime, date, timedelta

from supabase import create_client, Client


# =========================================================
# KONUHA
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"


# =========================================================
# Session State
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"


# =========================================================
# Secrets
# =========================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
SITE_PASSWORD = st.secrets.get("SITE_PASSWORD", "")


# =========================================================
# Supabase Client
# =========================================================

@st.cache_resource
def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )
    except Exception:
        return None


supabase: Client | None = get_supabase()


# =========================================================
# Connection Check
# =========================================================

@st.cache_data(ttl=20)
def check_connection():
    if supabase is None:
        return False

    try:
        supabase.table("supervisors").select("id").limit(1).execute()
        return True
    except Exception:
        return False


supabase_connected = check_connection()


# =========================================================
# Arabic Normalization
# =========================================================

def normalize_text(value: str) -> str:
    if not value:
        return ""

    value = str(value).strip().lower()

    # Remove Arabic diacritics
    value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    # Remove spaces and symbols
    value = re.sub(r"[\s\-_]+", "", value)
    value = re.sub(r"[^\w\u0600-\u06FF]", "", value)

    return value


# =========================================================
# Similarity
# =========================================================

def similarity(a: str, b: str) -> float:
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0

    return SequenceMatcher(None, a, b).ratio()


def find_similar_members(nickname: str, threshold: float = 0.82):
    if not supabase:
        return []

    try:
        response = (
            supabase
            .table("members")
            .select("id,nickname,phone,created_at")
            .execute()
        )

        results = []

        for member in response.data or []:
            score = similarity(
                nickname,
                member.get("nickname", "")
            )

            if score >= threshold:
                results.append({
                    "member": member,
                    "score": score
                })

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results[:5]

    except Exception:
        return []


# =========================================================
# Font Loader
# =========================================================

def find_font(keyword: str, weight: str):
    if not FONTS_DIR.exists():
        return None

    files = list(FONTS_DIR.glob("*.ttf"))

    keyword = keyword.lower()
    weight = weight.lower()

    # Exact-ish matching
    for file in files:
        name = file.name.lower().replace("_", "").replace("-", "")

        if keyword.replace(" ", "").lower() in name:
            if weight in name:
                return file

    return None


def font_to_base64(path):
    if not path or not path.exists():
        return ""

    try:
        return base64.b64encode(
            path.read_bytes()
        ).decode("utf-8")
    except Exception:
        return ""


cairo_regular = font_to_base64(
    find_font("Cairo", "regular")
)

cairo_medium = font_to_base64(
    find_font("Cairo", "medium")
)

cairo_bold = font_to_base64(
    find_font("Cairo", "bold")
)

inter_regular = font_to_base64(
    find_font("Inter", "regular")
)

inter_medium = font_to_base64(
    find_font("Inter", "medium")
)

inter_bold = font_to_base64(
    find_font("Inter", "bold")
)

readex_regular = font_to_base64(
    find_font("ReadexPro", "regular")
)

readex_medium = font_to_base64(
    find_font("ReadexPro", "medium")
)

readex_bold = font_to_base64(
    find_font("ReadexPro", "bold")
)


# =========================================================
# CSS
# =========================================================

font_css = ""

if cairo_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_regular});
        font-weight: 400;
    }}
    """

if cairo_medium:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_medium});
        font-weight: 500;
    }}
    """

if cairo_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Cairo';
        src: url(data:font/ttf;base64,{cairo_bold});
        font-weight: 700;
    }}
    """

if inter_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_regular});
        font-weight: 400;
    }}
    """

if inter_medium:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_medium});
        font-weight: 500;
    }}
    """

if inter_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Inter';
        src: url(data:font/ttf;base64,{inter_bold});
        font-weight: 700;
    }}
    """

if readex_regular:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Readex';
        src: url(data:font/ttf;base64,{readex_regular});
        font-weight: 400;
    }}
    """

if readex_medium:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Readex';
        src: url(data:font/ttf;base64,{readex_medium});
        font-weight: 500;
    }}
    """

if readex_bold:
    font_css += f"""
    @font-face {{
        font-family: 'KONUHA Readex';
        src: url(data:font/ttf;base64,{readex_bold});
        font-weight: 700;
    }}
    """


st.markdown(
    f"""
    <style>

    {font_css}

    /* ==============================
       Hide Streamlit Interface
       ============================== */

    #MainMenu {{
        visibility: hidden;
    }}

    [data-testid="stToolbar"] {{
        display: none;
    }}

    header {{
        display: none;
    }}

    footer {{
        display: none;
    }}

    [data-testid="stSidebar"] {{
        display: none;
    }}

    /* ==============================
       General
       ============================== */

    .stApp {{
        direction: rtl;
    }}

    html, body, [class*="css"] {{
        font-family:
            'KONUHA Cairo',
            'KONUHA Inter',
            sans-serif;
    }}

    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }}

    /* ==============================
       Header
       ============================== */

    .konuha-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 5px 20px 5px;
    }}

    .brand {{
        font-family: 'KONUHA Readex', sans-serif;
        font-size: 34px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    .brand-sub {{
        font-size: 13px;
        opacity: .55;
        margin-top: -5px;
    }}

    .connection {{
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }}

    .online {{
        background: rgba(46, 204, 113, .10);
        border: 1px solid rgba(46, 204, 113, .30);
    }}

    .offline {{
        background: rgba(231, 76, 60, .10);
        border: 1px solid rgba(231, 76, 60, .30);
    }}

    /* ==============================
       Navigation
       ============================== */

    div[data-testid="stHorizontalBlock"] {{
        gap: .45rem;
    }}

    .nav-label {{
        text-align: center;
        font-size: 12px;
        opacity: .5;
        margin-bottom: 7px;
    }}

    /* ==============================
       Cards
       ============================== */

    .card {{
        padding: 22px;
        border-radius: 18px;
        border: 1px solid rgba(128,128,128,.18);
        background: rgba(128,128,128,.035);
        margin-bottom: 15px;
    }}

    .card-title {{
        font-size: 14px;
        opacity: .65;
        margin-bottom: 8px;
    }}

    .card-value {{
        font-family: 'KONUHA Inter', sans-serif;
        font-size: 30px;
        font-weight: 700;
    }}

    /* ==============================
       Login
       ============================== */

    .login-box {{
        max-width: 430px;
        margin: 80px auto;
        text-align: center;
    }}

    .login-logo {{
        font-family: 'KONUHA Readex';
        font-size: 48px;
        font-weight: 700;
        margin-bottom: 5px;
    }}

    .login-text {{
        opacity: .55;
        margin-bottom: 25px;
    }}

    /* ==============================
       Tables
       ============================== */

    [data-testid="stDataFrame"] {{
        border-radius: 14px;
        overflow: hidden;
    }}

    /* ==============================
       Buttons
       ============================== */

    .stButton > button {{
        border-radius: 11px;
        font-family: 'KONUHA Cairo', sans-serif;
        font-weight: 600;
        min-height: 42px;
    }}

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Login
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        """
        <div class="login-box">
            <div class="login-logo">KONUHA</div>
            <div class="login-text">
                نظام إدارة العمل
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    password = st.text_input(
        "كلمة المرور",
        type="password",
        placeholder="أدخل كلمة المرور"
    )

    if st.button(
        "دخول",
        use_container_width=True
    ):

        if SITE_PASSWORD and password == SITE_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()

        else:
            st.error("كلمة المرور غير صحيحة.")

    st.stop()


# =========================================================
# Header
# =========================================================

connection_text = (
    "🟢 متصل بـ Supabase"
    if supabase_connected
    else
    "🔴 غير متصل بـ Supabase"
)

connection_class = (
    "online"
    if supabase_connected
    else
    "offline"
)

st.markdown(
    f"""
    <div class="konuha-header">

        <div>
            <div class="brand">KONUHA</div>
        </div>

        <div class="connection {connection_class}">
            {connection_text}
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Navigation
# =========================================================

pages = [
    "الرئيسية",
    "الأعضاء",
    "إضافة عضو",
    "المشرفين",
    "الإحصائيات",
    "التصدير",
    "الحذف",
]

nav_columns = st.columns(len(pages) + 1)

for index, page_name in enumerate(pages):

    with nav_columns[index]:

        if st.button(
            page_name,
            key=f"nav_{index}",
            use_container_width=True
        ):
            st.session_state.page = page_name
            st.rerun()

with nav_columns[-1]:

    if st.button(
        "خروج",
        key="logout",
        use_container_width=True
    ):
        st.session_state.logged_in = False
        st.rerun()


st.divider()


# =========================================================
# Data Helpers
# =========================================================

@st.cache_data(ttl=20)
def get_supervisors():
    if not supabase:
        return []

    try:
        response = (
            supabase
            .table("supervisors")
            .select("*")
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )

        return response.data or []

    except Exception:
        return []


@st.cache_data(ttl=20)
def get_members():
    if not supabase:
        return []

    try:
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


def clear_cache():
    get_members.clear()
    get_supervisors.clear()
    check_connection.clear()


def supervisor_map():
    supervisors = get_supervisors()

    return {
        item["id"]: item
        for item in supervisors
    }


def member_dataframe():
    members = get_members()
    supervisors = supervisor_map()

    rows = []

    for member in members:

        referrer = supervisors.get(
            member.get("referrer_id")
        )

        receiver = supervisors.get(
            member.get("receiver_id")
        )

        rows.append({
            "اللقب": member.get("nickname", ""),
            "الرقم": member.get("phone", ""),
            "من طرف": (
                referrer.get("nickname", "")
                if referrer else "—"
            ),
            "استقبله": (
                receiver.get("nickname", "")
                if receiver else "—"
            ),
            "تاريخ الإضافة": format_datetime(
                member.get("created_at")
            ),
            "_id": member.get("id")
        })

    return pd.DataFrame(rows)


def format_datetime(value):
    if not value:
        return "—"

    try:
        dt = pd.to_datetime(value)

        return dt.strftime(
            "%Y-%m-%d %H:%M"
        )

    except Exception:
        return str(value)


def get_date_from_timestamp(value):
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.title("لوحة التحكم")

    members = get_members()
    supervisors = get_supervisors()

    today = date.today()

    today_members = [
        m for m in members
        if get_date_from_timestamp(
            m.get("created_at")
        ) == today
    ]

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">إجمالي الأعضاء</div>
                <div class="card-value">{len(members)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">المشرفين</div>
                <div class="card-value">{len(supervisors)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">أعضاء اليوم</div>
                <div class="card-value">{len(today_members)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">حالة النظام</div>
                <div class="card-value">
                    {"متصل" if supabase_connected else "غير متصل"}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("آخر الأعضاء")

    df = member_dataframe()

    if df.empty:
        st.info("لا توجد أعضاء مسجلين حاليًا.")

    else:
        st.dataframe(
            df.drop(columns=["_id"]).head(10),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":

    st.title("الأعضاء")

    df = member_dataframe()

    if df.empty:
        st.info("لا توجد أعضاء.")

    else:

        search = st.text_input(
            "بحث داخل الأعضاء",
            placeholder="اكتب اللقب أو الرقم..."
        )

        if search:
            mask = (
                df["اللقب"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
                |
                df["الرقم"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            )

            df = df[mask]

        st.dataframe(
            df.drop(columns=["_id"]),
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# ADD MEMBER
# =========================================================

elif st.session_state.page == "إضافة عضو":

    st.title("إضافة عضو")

    supervisors = get_supervisors()

    if not supervisors:
        st.warning(
            "لا توجد مشرفين حاليًا. أضف مشرفًا أولاً."
        )

    else:

        supervisor_names = [
            s["nickname"]
            for s in supervisors
        ]

        nickname = st.text_input(
            "لقب العضو",
            placeholder="مثال: ارين"
        )

        phone = st.text_input(
            "الرقم",
            placeholder="مثال: 9647812345678"
        )

        referrer = st.selectbox(
            "من طرف",
            supervisor_names
        )

        receiver = st.selectbox(
            "استقبله",
            supervisor_names
        )

        force_add = st.checkbox(
            "إضافة إجبارية"
        )

        if st.button(
            "إضافة العضو",
            use_container_width=True
        ):

            if not nickname.strip():
                st.error("اكتب لقب العضو.")

            elif not phone.strip():
                st.error("اكتب رقم العضو.")

            else:

                normalized_phone = re.sub(
                    r"\D",
                    "",
                    phone
                )

                existing_phone = [
                    m for m in get_members()
                    if re.sub(
                        r"\D",
                        "",
                        str(m.get("phone", ""))
                    ) == normalized_phone
                ]

                if existing_phone:

                    st.error(
                        "هذا الرقم موجود مسبقًا في النظام."
                    )

                else:

                    similar = find_similar_members(
                        nickname
                    )

                    if similar and not force_add:

                        best = similar[0]

                        st.warning(
                            f"⚠️ يوجد لقب مشابه: "
                            f"{best['member']['nickname']} "
                            f"({best['score'] * 100:.0f}%)"
                        )

                        st.info(
                            "إذا كنت متأكدًا أن الشخص مختلف، "
                            "فعّل خيار «إضافة إجبارية»."
                        )

                    else:

                        referrer_obj = next(
                            (
                                s for s in supervisors
                                if s["nickname"] == referrer
                            ),
                            None
                        )

                        receiver_obj = next(
                            (
                                s for s in supervisors
                                if s["nickname"] == receiver
                            ),
                            None
                        )

                        if not referrer_obj or not receiver_obj:

                            st.error(
                                "المشرف غير موجود."
                            )

                        else:

                            try:

                                supabase.table(
                                    "members"
                                ).insert({
                                    "nickname": nickname.strip(),
                                    "normalized_nickname":
                                        normalize_text(nickname),
                                    "phone":
                                        normalized_phone,
                                    "referrer_id":
                                        referrer_obj["id"],
                                    "receiver_id":
                                        receiver_obj["id"],
                                }).execute()

                                clear_cache()

                                st.success(
                                    "✅ تم إضافة العضو بنجاح."
                                )

                                st.rerun()

                            except Exception as e:

                                st.error(
                                    f"حدث خطأ أثناء الإضافة: {e}"
                                )


# =========================================================
# SUPERVISORS
# =========================================================

elif st.session_state.page == "المشرفين":

    st.title("المشرفين")

    supervisors = get_supervisors()

    tab1, tab2 = st.tabs(
        ["قائمة المشرفين", "إضافة مشرف"]
    )

    with tab1:

        if not supervisors:
            st.info("لا توجد مشرفين.")

        else:

            rows = []

            for supervisor in supervisors:

                rows.append({
                    "الاسم": supervisor.get(
                        "name", ""
                    ),
                    "اللقب": supervisor.get(
                        "nickname", ""
                    ),
                    "تاريخ الإضافة":
                        format_datetime(
                            supervisor.get(
                                "created_at"
                            )
                        )
                })

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True
            )

    with tab2:

        name = st.text_input(
            "اسم المشرف"
        )

        nickname = st.text_input(
            "لقب المشرف"
        )

        if st.button(
            "إضافة المشرف",
            use_container_width=True
        ):

            if not name.strip():
                st.error("اكتب اسم المشرف.")

            elif not nickname.strip():
                st.error("اكتب لقب المشرف.")

            else:

                normalized_name = normalize_text(
                    name
                )

                normalized_nickname = normalize_text(
                    nickname
                )

                duplicate = any(
                    s.get(
                        "normalized_nickname"
                    ) == normalized_nickname
                    for s in supervisors
                )

                if duplicate:

                    st.error(
                        "هذا اللقب موجود مسبقًا."
                    )

                else:

                    try:

                        supabase.table(
                            "supervisors"
                        ).insert({
                            "name": name.strip(),
                            "nickname": nickname.strip(),
                            "normalized_name":
                                normalized_name,
                            "normalized_nickname":
                                normalized_nickname,
                            "is_active": True
                        }).execute()

                        clear_cache()

                        st.success(
                            "✅ تم إضافة المشرف."
                        )

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"حدث خطأ: {e}"
                        )


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":

    st.title("الإحصائيات")

    supervisors = get_supervisors()
    members = get_members()

    if not supervisors:

        st.info("لا توجد مشرفين.")

    else:

        supervisor_names = [
            s["nickname"]
            for s in supervisors
        ]

        selected = st.selectbox(
            "اختر المشرف",
            supervisor_names
        )

        selected_supervisor = next(
            (
                s for s in supervisors
                if s["nickname"] == selected
            ),
            None
        )

        if selected_supervisor:

            sid = selected_supervisor["id"]

            referred = [
                m for m in members
                if m.get("referrer_id") == sid
            ]

            received = [
                m for m in members
                if m.get("receiver_id") == sid
            ]

            st.subheader(
                f"إحصائيات {selected}"
            )

            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "من طرفه",
                    len(referred)
                )

            with c2:
                st.metric(
                    "استقبلهم",
                    len(received)
                )

            st.divider()

            mode = st.radio(
                "الفترة",
                [
                    "اليوم",
                    "أمس",
                    "هذا الشهر",
                    "تاريخ محدد"
                ],
                horizontal=True
            )

            target_date = None

            if mode == "اليوم":

                target_date = date.today()

            elif mode == "أمس":

                target_date = (
                    date.today()
                    - timedelta(days=1)
                )

            elif mode == "تاريخ محدد":

                target_date = st.date_input(
                    "اختر التاريخ",
                    value=date.today()
                )

            if mode == "هذا الشهر":

                month_start = date.today().replace(
                    day=1
                )

                referred_period = [
                    m for m in referred
                    if (
                        get_date_from_timestamp(
                            m.get("created_at")
                        )
                        and
                        get_date_from_timestamp(
                            m.get("created_at")
                        ) >= month_start
                    )
                ]

                received_period = [
                    m for m in received
                    if (
                        get_date_from_timestamp(
                            m.get("created_at")
                        )
                        and
                        get_date_from_timestamp(
                            m.get("created_at")
                        ) >= month_start
                    )
                ]

            else:

                referred_period = [
                    m for m in referred
                    if get_date_from_timestamp(
                        m.get("created_at")
                    ) == target_date
                ]

                received_period = [
                    m for m in received
                    if get_date_from_timestamp(
                        m.get("created_at")
                    ) == target_date
                ]

            c1, c2 = st.columns(2)

            with c1:
                st.metric(
                    "من طرفه في الفترة",
                    len(referred_period)
                )

            with c2:
                st.metric(
                    "استقبلهم في الفترة",
                    len(received_period)
                )


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":

    st.title("التصدير")

    df = member_dataframe()

    if df.empty:

        st.info("لا توجد بيانات للتصدير.")

    else:

        export_df = df.drop(
            columns=["_id"]
        )

        csv_data = export_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "تحميل CSV",
            data=csv_data,
            file_name="KONUHA_members.csv",
            mime="text/csv",
            use_container_width=True
        )

        excel_buffer = None

        try:

            import io

            excel_buffer = io.BytesIO()

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl"
            ) as writer:

                export_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Members"
                )

            excel_buffer.seek(0)

            st.download_button(
                "تحميل Excel",
                data=excel_buffer,
                file_name="KONUHA_members.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True
            )

        except Exception as e:

            st.error(
                f"تعذر تجهيز ملف Excel: {e}"
            )


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":

    st.title("حذف عضو")

    members = get_members()

    if not members:

        st.info("لا توجد أعضاء.")

    else:

        member_options = {
            f"{m.get('nickname', '')} — {m.get('phone', '')}":
                m
            for m in members
        }

        selected_label = st.selectbox(
            "اختر العضو",
            list(member_options.keys())
        )

        selected_member = member_options[
            selected_label
        ]

        st.warning(
            "⚠️ الحذف نهائي وسيزيل العضو من النظام."
        )

        confirm = st.checkbox(
            "أؤكد أنني أريد حذف هذا العضو"
        )

        if st.button(
            "حذف العضو نهائيًا",
            use_container_width=True
        ):

            if not confirm:

                st.error(
                    "يجب تأكيد عملية الحذف."
                )

            else:

                try:

                    supabase.table(
                        "members"
                    ).delete().eq(
                        "id",
                        selected_member["id"]
                    ).execute()

                    clear_cache()

                    st.success(
                        "✅ تم حذف العضو."
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"حدث خطأ أثناء الحذف: {e}"
                    )
