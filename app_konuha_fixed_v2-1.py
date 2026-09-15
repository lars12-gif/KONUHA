
import io
import re
import unicodedata
from datetime import date, datetime, timedelta

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


# ---------- CSS only; no HTML UI wrappers ----------
st.markdown(
    """
    <style>
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

    .stApp {
        background:
            radial-gradient(900px 500px at 90% -10%, rgba(139,92,246,.12), transparent 60%),
            radial-gradient(700px 450px at -10% 100%, rgba(217,70,239,.07), transparent 60%),
            var(--bg);
        color: var(--text);
    }

    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    #MainMenu,
    footer {
        visibility: hidden;
        height: 0;
    }

    .block-container {
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
    }
    </style>
    """,
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
nav = [
    "الرئيسية",
    "الأعضاء",
    "الإضافة",
    "المشرفين",
    "التعديل",
    "الإحصائيات",
    "التصدير",
    "الحذف",
]

current_index = nav.index(st.session_state.page) if st.session_state.page in nav else 0

choice = st.radio(
    "التنقل",
    nav,
    index=current_index,
    horizontal=True,
    label_visibility="collapsed",
)

if choice != st.session_state.page:
    st.session_state.page = choice
    st.rerun()

st.divider()

show_flash()

# =========================================================
# HOME
# =========================================================

if st.session_state.page == "الرئيسية":

    st.markdown("KONUHA", unsafe_allow_html=False)
    st.title("لوحة التحكم")
    st.write("إدارة الأعضاء والمشرفين والإحصائيات من مكان واحد.")

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


# =========================================================
# MEMBERS
# =========================================================

elif st.session_state.page == "الأعضاء":

    st.title("الأعضاء")

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

                    similar = [
                        x for x in members
                        if similarity(x.get("nickname", ""), nickname) >= 0.82
                        and norm(x.get("nickname", "")) != norm(nickname)
                    ]

                    if similar and not force:

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


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":

    st.title("حذف عضو")

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
