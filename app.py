import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

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


# =========================================================
# SETTINGS
# =========================================================

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
SITE_PASSWORD = st.secrets.get("SITE_PASSWORD", "")


# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def get_db():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


db = get_db()


@st.cache_data(ttl=15)
def get_members():
    if db is None:
        return []

    try:
        response = (
            db.table("members")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return response.data or []
    except Exception:
        return []


@st.cache_data(ttl=15)
def get_supervisors():
    if db is None:
        return []

    try:
        response = (
            db.table("supervisors")
            .select("*")
            .order("created_at")
            .execute()
        )
        return response.data or []
    except Exception:
        return []


@st.cache_data(ttl=15)
def check_database_connection():
    if db is None:
        return False

    try:
        db.table("supervisors").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def clear_cache():
    get_members.clear()
    get_supervisors.clear()
    check_database_connection.clear()


# =========================================================
# TEXT HELPERS
# =========================================================

def normalize_arabic(text):
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

    return re.sub(r"[^\w\u0600-\u06ff]+", "", text)


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_arabic(a),
        normalize_arabic(b),
    ).ratio()


def parse_date(value):
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def get_supervisor_by_name(supervisors, name):
    target = normalize_arabic(name)

    for supervisor in supervisors:
        if normalize_arabic(
            supervisor.get("name", "")
        ) == target:
            return supervisor

    return None


def get_supervisor_name(supervisors, supervisor_id):
    for supervisor in supervisors:
        if str(supervisor.get("id")) == str(supervisor_id):
            return supervisor.get("name", "-")

    return "-"


def find_similar_members(members, nickname):
    normalized = normalize_arabic(nickname)

    matches = []

    for member in members:
        existing = normalize_arabic(
            member.get("nickname", "")
        )

        if not existing:
            continue

        score = similarity(normalized, existing)

        if (
            score >= 0.82
            and normalized != existing
        ):
            matches.append(member)

    return matches


# =========================================================
# CSS
# IMPORTANT:
# CSS فقط - بدون HTML wrappers حول Streamlit widgets
# =========================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800'
        '&family=Inter:wght@500;600;700;800'
        '&family=Readex+Pro:wght@500;600;700&display=swap'
    );

    :root {
        --bg: #070812;
        --panel: #101326;
        --panel2: #14182f;
        --line: rgba(177, 91, 255, 0.18);
        --purple: #a85cff;
        --pink: #ec59b8;
        --text: #f7f4ff;
        --muted: #9b9ab0;
        --green: #55e5a0;
        --red: #ff7187;
    }

    * {
        box-sizing: border-box;
    }

    html,
    body,
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(
                900px 500px at 85% -10%,
                rgba(168, 92, 255, 0.16),
                transparent 65%
            ),
            radial-gradient(
                700px 450px at 0% 100%,
                rgba(236, 89, 184, 0.08),
                transparent 65%
            ),
            var(--bg) !important;
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

    [data-testid="stToolbar"] {
        display: none !important;
    }

    [data-testid="stDecoration"] {
        display: none !important;
    }

    .block-container {
        max-width: 1450px !important;
        padding: 25px 28px 55px !important;
    }

    body,
    .stApp {
        color: var(--text) !important;
        font-family: Cairo, sans-serif !important;
    }

    .stButton > button {
        min-height: 44px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(168, 92, 255, 0.22) !important;
        background: rgba(18, 21, 42, 0.9) !important;
        color: #e9e5f5 !important;
        font-family: Cairo, sans-serif !important;
        transition: 0.2s ease !important;
    }

    .stButton > button:hover {
        border-color: rgba(236, 89, 184, 0.5) !important;
        background:
            linear-gradient(
                135deg,
                rgba(168, 92, 255, 0.18),
                rgba(236, 89, 184, 0.10)
            ) !important;
        transform: translateY(-1px);
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: #0d1020 !important;
        border: 1px solid rgba(168, 92, 255, 0.18) !important;
        color: white !important;
        border-radius: 13px !important;
        font-family: Cairo, sans-serif !important;
    }

    div[data-baseweb="select"] {
        background: #0d1020 !important;
        border-radius: 13px !important;
        font-family: Cairo, sans-serif !important;
    }

    div[data-baseweb="select"] * {
        color: white !important;
    }

    [data-testid="stMetric"] {
        background:
            linear-gradient(
                145deg,
                #12162c,
                #0c0f20
            ) !important;
        border: 1px solid var(--line) !important;
        border-radius: 20px !important;
        padding: 18px !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted) !important;
        font-family: Cairo !important;
    }

    [data-testid="stMetricValue"] {
        color: white !important;
        font-family: Inter !important;
    }

    .stDataFrame {
        border: 1px solid var(--line);
        border-radius: 16px;
        overflow: hidden;
    }

    hr {
        border-color: rgba(168, 92, 255, 0.14) !important;
    }

    h1,
    h2,
    h3 {
        font-family: Readex Pro, Cairo, sans-serif !important;
    }

    .konuha-login-title {
        text-align: center;
        font-family: Readex Pro, Cairo, sans-serif;
        font-size: 52px;
        font-weight: 800;
        margin-bottom: 8px;
        background: linear-gradient(
            90deg,
            #ffffff,
            #c48cff,
            #ef6abd
        );
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
    }

    .konuha-hero {
        padding: 42px;
        border: 1px solid var(--line);
        border-radius: 28px;
        background:
            radial-gradient(
                circle at 78% 25%,
                rgba(236, 89, 184, 0.16),
                transparent 30%
            ),
            radial-gradient(
                circle at 60% 100%,
                rgba(100, 75, 255, 0.13),
                transparent 45%
            ),
            linear-gradient(
                135deg,
                #0d1023,
                #17122b
            );
        box-shadow: 0 25px 70px rgba(0, 0, 0, 0.28);
        margin-bottom: 20px;
    }

    .konuha-hero-title {
        font-family: Inter, sans-serif;
        font-size: 72px;
        font-weight: 800;
        letter-spacing: 2px;
        background: linear-gradient(
            90deg,
            #ffffff,
            #bb79ff,
            #ed63ba
        );
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        line-height: 1;
    }

    .konuha-hero-sub {
        margin-top: 14px;
        color: #d6d2e0;
        font-size: 17px;
    }

    .konuha-hero-line {
        width: 65px;
        height: 4px;
        border-radius: 20px;
        background: linear-gradient(
            90deg,
            var(--purple),
            var(--pink)
        );
        margin-top: 22px;
    }

    .konuha-status-online {
        color: var(--green);
        text-align: center;
        font-size: 14px;
        font-weight: 600;
        padding-top: 10px;
    }

    .konuha-status-offline {
        color: var(--red);
        text-align: center;
        font-size: 14px;
        font-weight: 600;
        padding-top: 10px;
    }

    @media (max-width: 800px) {

        .block-container {
            padding: 16px 12px 35px !important;
        }

        .konuha-hero {
            padding: 26px 20px;
        }

        .konuha-hero-title {
            font-size: 45px;
        }

        .stButton > button {
            min-height: 42px !important;
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
        "<div style='height:10vh'></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='konuha-login-title'>KONUHA</div>",
        unsafe_allow_html=True,
    )

    st.caption("نظام إدارة الأعضاء والمشرفين")

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

        else:
            st.error("كلمة المرور غير صحيحة.")

    st.stop()


# =========================================================
# LOAD DATA
# =========================================================

members = get_members()
supervisors = get_supervisors()

database_status = check_database_connection()


# =========================================================
# SESSION PAGE
# =========================================================

if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"


# =========================================================
# TOP BAR
# =========================================================

top1, top2, top3 = st.columns([1, 1, 2])

with top1:

    if st.button(
        "KONUHA",
        use_container_width=True,
    ):
        st.session_state.page = "الرئيسية"
        st.rerun()


with top2:

    if st.button(
        "↪ تسجيل الخروج",
        use_container_width=True,
    ):
        st.session_state.authenticated = False
        st.rerun()


with top3:

    if database_status:

        st.markdown(
            "<div class='konuha-status-online'>"
            "🟢 متصل بـ Supabase"
            "</div>",
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            "<div class='konuha-status-offline'>"
            "🔴 غير متصل بـ Supabase"
            "</div>",
            unsafe_allow_html=True,
        )


# =========================================================
# NAVIGATION
# =========================================================

navigation = [
    ("⌂", "الرئيسية"),
    ("♟", "الأعضاء"),
    ("＋", "إضافة عضو"),
    ("◈", "المشرفين"),
    ("＋", "إضافة مشرف"),
    ("▥", "الإحصائيات"),
    ("⇩", "التصدير"),
    ("⌫", "الحذف"),
]


nav_columns = st.columns(4)

for index, (icon, label) in enumerate(navigation):

    with nav_columns[index % 4]:

        if st.button(
            f"{icon}  {label}",
            key=f"navigation_{index}",
            use_container_width=True,
        ):

            st.session_state.page = label
            st.rerun()


st.divider()


# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.markdown(
        """
        <div class="konuha-hero">
            <div class="konuha-hero-title">
                KONUHA
            </div>

            <div class="konuha-hero-sub">
                نظام إدارة الأعضاء والمشرفين — كل بياناتك بمكان واحد
            </div>

            <div class="konuha-hero-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    today_members = 0

    for member in members:

        created = parse_date(
            member.get("created_at")
        )

        if created == date.today():
            today_members += 1


    stat1, stat2, stat3, stat4 = st.columns(4)

    with stat1:
        st.metric(
            "إجمالي الأعضاء",
            len(members),
        )

    with stat2:
        st.metric(
            "المشرفين",
            len(supervisors),
        )

    with stat3:
        st.metric(
            "أعضاء اليوم",
            today_members,
        )

    with stat4:
        st.metric(
            "حالة النظام",
            "متصل" if database_status else "غير متصل",
        )


    st.subheader("آخر الأعضاء")


    latest_rows = []

    for member in members[:10]:

        latest_rows.append(
            {
                "اللقب": member.get("nickname", ""),
                "الرقم": member.get("phone", ""),
                "من طرف": get_supervisor_name(
                    supervisors,
                    member.get("referrer_id"),
                ),
                "استقبله": get_supervisor_name(
                    supervisors,
                    member.get("receiver_id"),
                ),
                "تاريخ الإضافة": member.get(
                    "created_at",
                    "",
                ),
            }
        )


    if latest_rows:

        st.dataframe(
            pd.DataFrame(latest_rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "لا توجد أعضاء مسجلين حالياً."
        )


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":

    st.title("الأعضاء")

    search = st.text_input(
        "البحث",
        placeholder="اللقب أو الرقم...",
    )

    member_rows = []

    normalized_search = normalize_arabic(search)


    for member in members:

        nickname = member.get(
            "nickname",
            "",
        )

        phone = str(
            member.get(
                "phone",
                "",
            )
        )


        if search:

            nickname_match = (
                normalized_search
                in normalize_arabic(nickname)
            )

            phone_match = (
                search in phone
            )

            if not nickname_match and not phone_match:
                continue


        member_rows.append(
            {
                "اللقب": nickname,
                "الرقم": phone,
                "من طرف": get_supervisor_name(
                    supervisors,
                    member.get("referrer_id"),
                ),
                "استقبله": get_supervisor_name(
                    supervisors,
                    member.get("receiver_id"),
                ),
                "تاريخ الإضافة": member.get(
                    "created_at",
                    "",
                ),
            }
        )


    if member_rows:

        st.dataframe(
            pd.DataFrame(member_rows),
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

    st.title("إضافة عضو")

    active_supervisors = [
        supervisor
        for supervisor in supervisors
        if supervisor.get(
            "is_active",
            True,
        )
    ]


    if not active_supervisors:

        st.warning(
            "لا يوجد مشرفون. أضف مشرفاً أولاً."
        )

    else:

        supervisor_names = [
            supervisor.get(
                "name",
                "",
            )
            for supervisor in active_supervisors
        ]


        with st.form("add_member_form"):

            nickname = st.text_input(
                "اللقب",
                placeholder="مثال: ايرن",
            )

            phone = st.text_input(
                "الرقم",
                placeholder="9647XXXXXXXX",
            )

            referrer = st.selectbox(
                "من طرف",
                supervisor_names,
            )

            receiver = st.selectbox(
                "استقبله",
                supervisor_names,
            )

            force_add = st.checkbox(
                "إضافة إجبارية عند وجود لقب مشابه",
            )

            submit_member = st.form_submit_button(
                "إضافة العضو",
                use_container_width=True,
            )


        if submit_member:

            nickname = nickname.strip()

            phone = re.sub(
                r"\D",
                "",
                phone,
            )


            if not nickname or not phone:

                st.error(
                    "أدخل اللقب والرقم."
                )


            elif any(
                str(member.get("phone", "")) == phone
                for member in members
            ):

                st.error(
                    "هذا الرقم مسجل مسبقاً."
                )


            else:

                similar_results = find_similar_members(
                    members,
                    nickname,
                )


                if similar_results and not force_add:

                    similar_names = ", ".join(
                        member.get(
                            "nickname",
                            "",
                        )
                        for member in similar_results
                    )

                    st.warning(
                        "يوجد لقب مشابه: "
                        + similar_names
                        + " — فعّل الإضافة الإجبارية "
                        "إذا كان العضو مختلفاً."
                    )

                else:

                    referrer_obj = get_supervisor_by_name(
                        supervisors,
                        referrer,
                    )

                    receiver_obj = get_supervisor_by_name(
                        supervisors,
                        receiver,
                    )


                    if db is None:

                        st.error(
                            "قاعدة البيانات غير متصلة."
                        )

                    elif not referrer_obj or not receiver_obj:

                        st.error(
                            "تعذر العثور على المشرف."
                        )

                    else:

                        try:

                            db.table(
                                "members"
                            ).insert(
                                {
                                    "nickname": nickname,
                                    "normalized_nickname":
                                        normalize_arabic(
                                            nickname
                                        ),
                                    "phone": phone,
                                    "referrer_id":
                                        referrer_obj["id"],
                                    "receiver_id":
                                        receiver_obj["id"],
                                }
                            ).execute()


                            clear_cache()

                            st.success(
                                "تمت إضافة العضو بنجاح."
                            )

                            st.rerun()


                        except Exception as error:

                            st.error(
                                f"تعذر إضافة العضو: {error}"
                            )


# =========================================================
# SUPERVISORS
# =========================================================

elif st.session_state.page == "المشرفين":

    st.title("المشرفين")


    supervisor_rows = []

    for supervisor in supervisors:

        supervisor_rows.append(
            {
                "الاسم": supervisor.get(
                    "name",
                    "",
                ),
                "اللقب": supervisor.get(
                    "nickname",
                    "",
                ),
                "الحالة":
                    "فعال"
                    if supervisor.get(
                        "is_active",
                        True,
                    )
                    else "غير فعال",
                "تاريخ الإضافة": supervisor.get(
                    "created_at",
                    "",
                ),
            }
        )


    if supervisor_rows:

        st.dataframe(
            pd.DataFrame(supervisor_rows),
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

    st.title("إضافة مشرف")


    with st.form("add_supervisor_form"):

        supervisor_name = st.text_input(
            "اسم المشرف",
        )

        supervisor_nickname = st.text_input(
            "لقب المشرف",
        )

        submit_supervisor = st.form_submit_button(
            "إضافة المشرف",
            use_container_width=True,
        )


    if submit_supervisor:

        supervisor_name = supervisor_name.strip()
        supervisor_nickname = supervisor_nickname.strip()


        if not supervisor_name or not supervisor_nickname:

            st.error(
                "أدخل الاسم واللقب."
            )


        elif any(
            normalize_arabic(
                supervisor_name
            )
            ==
            normalize_arabic(
                supervisor.get(
                    "name",
                    "",
                )
            )
            for supervisor in supervisors
        ):

            st.error(
                "هذا المشرف موجود مسبقاً."
            )


        elif db is None:

            st.error(
                "قاعدة البيانات غير متصلة."
            )


        else:

            try:

                db.table(
                    "supervisors"
                ).insert(
                    {
                        "name": supervisor_name,
                        "nickname": supervisor_nickname,
                        "normalized_name":
                            normalize_arabic(
                                supervisor_name
                            ),
                        "normalized_nickname":
                            normalize_arabic(
                                supervisor_nickname
                            ),
                        "is_active": True,
                    }
                ).execute()


                clear_cache()

                st.success(
                    "تمت إضافة المشرف."
                )

                st.rerun()


            except Exception as error:

                st.error(
                    f"تعذر إضافة المشرف: {error}"
                )


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":

    st.title("الإحصائيات")


    supervisor_options = [
        "الكل"
    ] + [
        supervisor.get(
            "name",
            "",
        )
        for supervisor in supervisors
    ]


    selected_supervisor = st.selectbox(
        "المشرف",
        supervisor_options,
    )


    period = st.selectbox(
        "الفترة",
        [
            "كل الوقت",
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
            value=date.today(),
        )


    filtered_members = []


    for member in members:

        if (
            selected_supervisor != "الكل"
            and get_supervisor_name(
                supervisors,
                member.get("referrer_id"),
            )
            != selected_supervisor
        ):
            continue


        member_date = parse_date(
            member.get("created_at")
        )


        keep = True


        if period == "اليوم":

            keep = (
                member_date
                == date.today()
            )


        elif period == "امس":

            keep = (
                member_date
                == date.today()
                - timedelta(days=1)
            )


        elif period == "هذا_الشهر":

            keep = (
                member_date is not None
                and member_date.year
                == date.today().year
                and member_date.month
                == date.today().month
            )


        elif period == "تاريخ محدد":

            keep = (
                member_date
                == selected_date
            )


        if keep:

            filtered_members.append(
                member
            )


    st.metric(
        "عدد الأعضاء",
        len(filtered_members),
    )


    breakdown = []


    for supervisor in supervisors:

        count = sum(
            str(member.get("referrer_id"))
            == str(supervisor.get("id"))
            for member in filtered_members
        )


        breakdown.append(
            {
                "المشرف": supervisor.get(
                    "name",
                    "",
                ),
                "اللقب": supervisor.get(
                    "nickname",
                    "",
                ),
                "عدد الأعضاء": count,
            }
        )


    if breakdown:

        st.dataframe(
            pd.DataFrame(breakdown),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":

    st.title("التصدير")


    export_rows = []


    for member in members:

        export_rows.append(
            {
                "اللقب": member.get(
                    "nickname",
                    "",
                ),
                "الرقم": member.get(
                    "phone",
                    "",
                ),
                "من طرف": get_supervisor_name(
                    supervisors,
                    member.get(
                        "referrer_id"
                    ),
                ),
                "استقبله": get_supervisor_name(
                    supervisors,
                    member.get(
                        "receiver_id"
                    ),
                ),
                "تاريخ الإضافة": member.get(
                    "created_at",
                    "",
                ),
            }
        )


    export_df = pd.DataFrame(
        export_rows
    )


    if not export_df.empty:

        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "لا توجد بيانات للتصدير."
        )


    csv_data = export_df.to_csv(
        index=False
    ).encode("utf-8-sig")


    st.download_button(
        "⇩ تحميل CSV",
        data=csv_data,
        file_name="konuha_members.csv",
        mime="text/csv",
        use_container_width=True,
    )


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


# =========================================================
# DELETE MEMBER
# =========================================================

elif st.session_state.page == "الحذف":

    st.title("حذف عضو")


    if not members:

        st.info(
            "لا توجد أعضاء للحذف."
        )

    else:

        member_options = [
            (
                member.get(
                    "nickname",
                    "",
                ),
                member.get(
                    "phone",
                    "",
                ),
            )
            for member in members
        ]


        selected_member = st.selectbox(
            "اختر العضو",
            member_options,
            format_func=lambda item:
                f"{item[0]} — {item[1]}",
        )


        selected_nickname = selected_member[0]
        selected_phone = selected_member[1]


        member = next(
            (
                item
                for item in members
                if item.get(
                    "nickname",
                    "",
                )
                == selected_nickname
                and str(
                    item.get(
                        "phone",
                        "",
                    )
                )
                == str(selected_phone)
            ),
            None,
        )


        if member:

            st.warning(
                "سيتم حذف العضو: "
                f"{selected_nickname} — "
                f"{selected_phone}"
            )


            confirm_delete = st.checkbox(
                "أؤكد أنني أريد حذف هذا العضو نهائياً"
            )


            if st.button(
                "حذف نهائياً",
                use_container_width=True,
                disabled=not confirm_delete,
            ):

                if db is None:

                    st.error(
                        "قاعدة البيانات غير متصلة."
                    )

                else:

                    try:

                        db.table(
                            "members"
                        ).delete().eq(
                            "id",
                            member["id"],
                        ).execute()


                        clear_cache()

                        st.success(
                            "تم حذف العضو بنجاح."
                        )

                        st.rerun()


                    except Exception as error:

                        st.error(
                            f"تعذر الحذف: {error}"
                        )
