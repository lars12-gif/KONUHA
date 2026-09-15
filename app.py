import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

import pandas as pd
import streamlit as st
from supabase import create_client


# =========================================================
# KONUHA - CONFIG
# =========================================================

st.set_page_config(
    page_title="KONUHA",
    page_icon="K",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# SECRETS
# =========================================================

SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL",
    "",
)

SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY",
    "",
)

SITE_PASSWORD = st.secrets.get(
    "SITE_PASSWORD",
    "",
)


# =========================================================
# DATABASE
# =========================================================

@st.cache_resource
def create_database():

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )
    except Exception:
        return None


db = create_database()


@st.cache_data(ttl=15)
def database_is_online():

    if db is None:
        return False

    try:
        db.table(
            "supervisors"
        ).select(
            "id"
        ).limit(1).execute()

        return True

    except Exception:
        return False


@st.cache_data(ttl=15)
def load_members():

    if db is None:
        return []

    try:

        result = (
            db.table("members")
            .select("*")
            .order(
                "created_at",
                desc=True,
            )
            .execute()
        )

        return result.data or []

    except Exception:
        return []


@st.cache_data(ttl=15)
def load_supervisors():

    if db is None:
        return []

    try:

        result = (
            db.table("supervisors")
            .select("*")
            .order("created_at")
            .execute()
        )

        return result.data or []

    except Exception:
        return []


def refresh_data():

    load_members.clear()
    load_supervisors.clear()
    database_is_online.clear()


members = load_members()
supervisors = load_supervisors()
db_online = database_is_online()


# =========================================================
# TEXT FUNCTIONS
# =========================================================

def normalize_arabic(text):

    text = str(text or "").strip().lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
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
        text = text.replace(
            old,
            new,
        )

    text = re.sub(
        r"[^\w\u0600-\u06ff]+",
        "",
        text,
    )

    return text


def similarity(a, b):

    return SequenceMatcher(
        None,
        normalize_arabic(a),
        normalize_arabic(b),
    ).ratio()


def parse_date(value):

    try:

        return datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        ).date()

    except Exception:

        return None


def supervisor_by_name(name):

    target = normalize_arabic(name)

    for supervisor in supervisors:

        if normalize_arabic(
            supervisor.get(
                "name",
                "",
            )
        ) == target:

            return supervisor

    return None


def supervisor_name(supervisor_id):

    for supervisor in supervisors:

        if str(
            supervisor.get("id")
        ) == str(supervisor_id):

            return supervisor.get(
                "name",
                "-",
            )

    return "-"


def similar_members(nickname):

    target = normalize_arabic(
        nickname
    )

    result = []

    for member in members:

        existing = normalize_arabic(
            member.get(
                "nickname",
                "",
            )
        )

        if not existing:
            continue

        score = similarity(
            target,
            existing,
        )

        if (
            score >= 0.82
            and target != existing
        ):

            result.append(
                {
                    "member": member,
                    "score": score,
                }
            )

    return result


# =========================================================
# SESSION
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


if "page" not in st.session_state:
    st.session_state.page = "الرئيسية"


# =========================================================
# LOGIN
# =========================================================

if not st.session_state.logged_in:

    st.write("")
    st.write("")
    st.write("")

    st.title("KONUHA")

    st.subheader(
        "نظام إدارة الأعضاء والمشرفين"
    )

    st.write(
        "سجّل الدخول للوصول إلى لوحة التحكم."
    )

    password = st.text_input(
        "كلمة المرور",
        type="password",
        placeholder="أدخل كلمة المرور",
    )

    if st.button(
        "دخول",
        use_container_width=True,
    ):

        if (
            SITE_PASSWORD
            and password == SITE_PASSWORD
        ):

            st.session_state.logged_in = True
            st.rerun()

        else:

            st.error(
                "كلمة المرور غير صحيحة."
            )

    st.stop()


# =========================================================
# HEADER
# =========================================================

header_left, header_right = st.columns(
    [4, 1]
)

with header_left:

    st.title("KONUHA")

    st.caption(
        "إدارة الأعضاء والمشرفين والبيانات"
    )


with header_right:

    if db_online:

        st.success(
            "🟢 متصل بـ Supabase"
        )

    else:

        st.error(
            "🔴 غير متصل"
        )


st.divider()


# =========================================================
# NAVIGATION
# =========================================================

pages = [
    "الرئيسية",
    "الأعضاء",
    "إضافة عضو",
    "المشرفين",
    "إضافة مشرف",
    "الإحصائيات",
    "التصدير",
    "الحذف",
]


selected_page = st.radio(
    "القائمة",
    pages,
    index=pages.index(
        st.session_state.page
    ),
    horizontal=True,
    label_visibility="collapsed",
)


if selected_page != st.session_state.page:

    st.session_state.page = selected_page
    st.rerun()


# =========================================================
# LOGOUT
# =========================================================

if st.button(
    "تسجيل الخروج",
):

    st.session_state.logged_in = False
    st.rerun()


st.divider()


# =========================================================
# DASHBOARD
# =========================================================

if st.session_state.page == "الرئيسية":

    st.header("لوحة التحكم")

    st.write(
        "نظرة سريعة على بيانات KONUHA."
    )

    today = date.today()

    today_count = 0

    for member in members:

        created = parse_date(
            member.get(
                "created_at"
            )
        )

        if created == today:
            today_count += 1


    total_members = len(members)
    total_supervisors = len(supervisors)


    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "الأعضاء",
            total_members,
        )

    with col2:

        st.metric(
            "المشرفين",
            total_supervisors,
        )

    with col3:

        st.metric(
            "أعضاء اليوم",
            today_count,
        )

    with col4:

        st.metric(
            "حالة الاتصال",
            "متصل" if db_online else "غير متصل",
        )


    st.subheader(
        "آخر الأعضاء"
    )


    recent = []


    for member in members[:10]:

        recent.append(
            {
                "اللقب": member.get(
                    "nickname",
                    "",
                ),
                "الرقم": member.get(
                    "phone",
                    "",
                ),
                "من طرف": supervisor_name(
                    member.get(
                        "referrer_id"
                    )
                ),
                "استقبله": supervisor_name(
                    member.get(
                        "receiver_id"
                    )
                ),
                "تاريخ الإضافة": member.get(
                    "created_at",
                    "",
                ),
            }
        )


    if recent:

        st.dataframe(
            pd.DataFrame(recent),
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

    st.header("الأعضاء")

    search = st.text_input(
        "بحث عن عضو",
        placeholder="اكتب اللقب أو الرقم",
    )


    rows = []

    normalized_search = normalize_arabic(
        search
    )


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
                in normalize_arabic(
                    nickname
                )
            )

            phone_match = (
                search in phone
            )

            if (
                not nickname_match
                and not phone_match
            ):
                continue


        rows.append(
            {
                "اللقب": nickname,
                "الرقم": phone,
                "من طرف": supervisor_name(
                    member.get(
                        "referrer_id"
                    )
                ),
                "استقبله": supervisor_name(
                    member.get(
                        "receiver_id"
                    )
                ),
                "تاريخ الإضافة": member.get(
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

    st.header("إضافة عضو")

    if not supervisors:

        st.warning(
            "لا يوجد مشرفون حالياً."
        )

        st.info(
            "أضف مشرفاً أولاً من صفحة إضافة مشرف."
        )

    else:

        supervisor_names = [
            supervisor.get(
                "name",
                "",
            )
            for supervisor in supervisors
            if supervisor.get(
                "is_active",
                True,
            )
        ]


        with st.form(
            "member_form"
        ):

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

            force = st.checkbox(
                "إضافة إجبارية إذا وجد لقب مشابه",
            )

            submit = st.form_submit_button(
                "إضافة العضو",
                use_container_width=True,
            )


        if submit:

            nickname = nickname.strip()

            phone = re.sub(
                r"\D",
                "",
                phone,
            )


            if not nickname:

                st.error(
                    "أدخل اللقب."
                )

            elif not phone:

                st.error(
                    "أدخل الرقم."
                )

            elif not db_online:

                st.error(
                    "قاعدة البيانات غير متصلة."
                )

            else:

                duplicate_phone = False

                for member in members:

                    if str(
                        member.get(
                            "phone",
                            "",
                        )
                    ) == phone:

                        duplicate_phone = True
                        break


                if duplicate_phone:

                    st.error(
                        "هذا الرقم مسجل مسبقاً."
                    )

                else:

                    similar = similar_members(
                        nickname
                    )


                    if similar and not force:

                        names = ", ".join(
                            item[
                                "member"
                            ].get(
                                "nickname",
                                "",
                            )
                            for item in similar
                        )

                        st.warning(
                            "يوجد لقب مشابه: "
                            + names
                            + ". "
                            "إذا كان العضو مختلفاً، "
                            "فعّل الإضافة الإجبارية."
                        )

                    else:

                        referrer_obj = supervisor_by_name(
                            referrer
                        )

                        receiver_obj = supervisor_by_name(
                            receiver
                        )


                        if (
                            not referrer_obj
                            or not receiver_obj
                        ):

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
                                            referrer_obj[
                                                "id"
                                            ],
                                        "receiver_id":
                                            receiver_obj[
                                                "id"
                                            ],
                                    }
                                ).execute()


                                refresh_data()

                                st.success(
                                    "تمت إضافة العضو بنجاح."
                                )

                                st.rerun()


                            except Exception as error:

                                st.error(
                                    "حدث خطأ أثناء الإضافة: "
                                    + str(error)
                                )


# =========================================================
# SUPERVISORS
# =========================================================

elif st.session_state.page == "المشرفين":

    st.header("المشرفين")


    rows = []


    for supervisor in supervisors:

        rows.append(
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


    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "لا يوجد مشرفون."
        )


# =========================================================
# ADD SUPERVISOR
# =========================================================

elif st.session_state.page == "إضافة مشرف":

    st.header("إضافة مشرف")


    with st.form(
        "supervisor_form"
    ):

        name = st.text_input(
            "اسم المشرف",
            placeholder="مثال: احمد",
        )

        nickname = st.text_input(
            "لقب المشرف",
            placeholder="مثال: المدير",
        )

        submit = st.form_submit_button(
            "إضافة المشرف",
            use_container_width=True,
        )


    if submit:

        name = name.strip()
        nickname = nickname.strip()


        if not name:

            st.error(
                "أدخل اسم المشرف."
            )

        elif not nickname:

            st.error(
                "أدخل لقب المشرف."
            )

        elif not db_online:

            st.error(
                "قاعدة البيانات غير متصلة."
            )

        else:

            duplicate = False


            for supervisor in supervisors:

                if (
                    normalize_arabic(
                        supervisor.get(
                            "name",
                            "",
                        )
                    )
                    ==
                    normalize_arabic(
                        name
                    )
                ):

                    duplicate = True
                    break


            if duplicate:

                st.error(
                    "هذا المشرف موجود مسبقاً."
                )

            else:

                try:

                    db.table(
                        "supervisors"
                    ).insert(
                        {
                            "name": name,
                            "nickname": nickname,
                            "normalized_name":
                                normalize_arabic(
                                    name
                                ),
                            "normalized_nickname":
                                normalize_arabic(
                                    nickname
                                ),
                            "is_active": True,
                        }
                    ).execute()


                    refresh_data()

                    st.success(
                        "تمت إضافة المشرف بنجاح."
                    )

                    st.rerun()


                except Exception as error:

                    st.error(
                        "حدث خطأ أثناء الإضافة: "
                        + str(error)
                    )


# =========================================================
# STATISTICS
# =========================================================

elif st.session_state.page == "الإحصائيات":

    st.header("الإحصائيات")


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
            "اختر التاريخ",
            value=date.today(),
        )


    filtered = []


    for member in members:

        if (
            selected_supervisor != "الكل"
            and supervisor_name(
                member.get(
                    "referrer_id"
                )
            )
            != selected_supervisor
        ):

            continue


        member_date = parse_date(
            member.get(
                "created_at"
            )
        )


        include = True


        if period == "اليوم":

            include = (
                member_date
                == date.today()
            )


        elif period == "امس":

            include = (
                member_date
                == date.today()
                - timedelta(days=1)
            )


        elif period == "هذا_الشهر":

            include = (
                member_date is not None
                and member_date.year
                == date.today().year
                and member_date.month
                == date.today().month
            )


        elif period == "تاريخ محدد":

            include = (
                member_date
                == selected_date
            )


        if include:

            filtered.append(
                member
            )


    st.metric(
        "عدد الأعضاء",
        len(filtered),
    )


    statistics = []


    for supervisor in supervisors:

        count = 0


        for member in filtered:

            if (
                str(
                    member.get(
                        "referrer_id"
                    )
                )
                ==
                str(
                    supervisor.get(
                        "id"
                    )
                )
            ):

                count += 1


        statistics.append(
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


    if statistics:

        st.dataframe(
            pd.DataFrame(statistics),
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# EXPORT
# =========================================================

elif st.session_state.page == "التصدير":

    st.header("التصدير")


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
                "من طرف": supervisor_name(
                    member.get(
                        "referrer_id"
                    )
                ),
                "استقبله": supervisor_name(
                    member.get(
                        "receiver_id"
                    )
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


    if export_df.empty:

        st.info(
            "لا توجد بيانات للتصدير."
        )

    else:

        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True,
        )


        csv_file = export_df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )


        st.download_button(
            "تحميل CSV",
            data=csv_file,
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
            "تحميل Excel",
            data=excel_buffer.getvalue(),
            file_name="konuha_members.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )


# =========================================================
# DELETE
# =========================================================

elif st.session_state.page == "الحذف":

    st.header("حذف عضو")


    if not members:

        st.info(
            "لا توجد أعضاء حالياً."
        )

    else:

        member_options = []


        for member in members:

            label = (
                str(
                    member.get(
                        "nickname",
                        "",
                    )
                )
                + " — "
                + str(
                    member.get(
                        "phone",
                        "",
                    )
                )
            )

            member_options.append(
                (
                    label,
                    member,
                )
            )


        selected_label = st.selectbox(
            "اختر العضو",
            [
                item[0]
                for item in member_options
            ],
        )


        selected_member = None


        for label, member in member_options:

            if label == selected_label:

                selected_member = member
                break


        if selected_member:

            st.warning(
                "سيتم حذف العضو نهائياً:"
            )

            st.write(
                "اللقب:",
                selected_member.get(
                    "nickname",
                    "",
                ),
            )

            st.write(
                "الرقم:",
                selected_member.get(
                    "phone",
                    "",
                ),
            )


            confirm = st.checkbox(
                "أؤكد حذف هذا العضو نهائياً."
            )


            if st.button(
                "حذف العضو",
                use_container_width=True,
                disabled=not confirm,
            ):

                if not db_online:

                    st.error(
                        "قاعدة البيانات غير متصلة."
                    )

                else:

                    try:

                        db.table(
                            "members"
                        ).delete().eq(
                            "id",
                            selected_member[
                                "id"
                            ],
                        ).execute()


                        refresh_data()

                        st.success(
                            "تم حذف العضو بنجاح."
                        )

                        st.rerun()


                    except Exception as error:

                        st.error(
                            "حدث خطأ أثناء الحذف: "
                            + str(error)
                        )
