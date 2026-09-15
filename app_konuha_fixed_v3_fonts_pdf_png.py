
import io
import re
import unicodedata
import base64
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from supabase import create_client
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4


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



# =========================================================
# LOCAL FONTS + REPORT EXPORTS
# =========================================================

APP_DIR = Path(__file__).resolve().parent
FONT_DIR = APP_DIR / "fonts"


def find_font(family, weight=None):
    if not FONT_DIR.exists():
        return None

    family = family.lower()
    weight = weight.lower() if weight else None

    files = list(FONT_DIR.glob("*.ttf"))

    for f in files:
        name = f.name.lower()
        if family in name and (not weight or weight in name):
            return f

    for f in files:
        if family in f.name.lower():
            return f

    return None


CAIRO_REGULAR = find_font("cairo", "regular") or find_font("cairo")
CAIRO_BOLD = (
    find_font("cairo", "bold")
    or find_font("cairo", "700")
    or CAIRO_REGULAR
)
READEX_REGULAR = find_font("readex", "regular") or find_font("readex")
INTER_REGULAR = find_font("inter", "regular") or find_font("inter")


def font_face_css(name, path, weights="400"):
    if not path or not path.exists():
        return ""

    try:
        encoded = base64.b64encode(
            path.read_bytes()
        ).decode("ascii")

        return f"""
        @font-face {{
            font-family: '{name}';
            src: url(data:font/ttf;base64,{encoded}) format('truetype');
            font-weight: {weights};
            font-style: normal;
            font-display: swap;
        }}
        """
    except Exception:
        return ""


LOCAL_FONT_CSS = (
    font_face_css("KONUHA Cairo", CAIRO_REGULAR, "400 500 600")
    + font_face_css("KONUHA Cairo", CAIRO_BOLD, "700 800 900")
    + font_face_css("KONUHA Readex", READEX_REGULAR, "400 500 600 700")
    + font_face_css("KONUHA Inter", INTER_REGULAR, "400 500 600 700 800")
)


def get_export_font(size, bold=False):
    path = CAIRO_BOLD if bold else CAIRO_REGULAR

    if path and path.exists():
        return ImageFont.truetype(str(path), size)

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)

    return ImageFont.load_default()


def draw_rtl(draw, position, value, font, fill):
    value = str(value or "")

    try:
        draw.text(
            position,
            value,
            font=font,
            fill=fill,
            anchor="ra",
            direction="rtl",
        )
    except Exception:
        draw.text(
            position,
            value,
            font=font,
            fill=fill,
            anchor="ra",
        )


def make_konuha_report_png(rows):
    width = 1800
    row_height = 76
    data_rows = rows or []

    height = max(
        1120,
        660 + row_height * min(len(data_rows), 12),
    )

    image = Image.new(
        "RGB",
        (width, height),
        "#080910",
    )

    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (45, 45, width - 45, height - 45),
        radius=36,
        fill="#11131f",
        outline="#2b2f42",
        width=2,
    )

    draw.rounded_rectangle(
        (75, 75, width - 75, 285),
        radius=30,
        fill="#171a2a",
    )

    title_font = get_export_font(78, True)
    heading_font = get_export_font(35, True)
    body_font = get_export_font(25)
    small_font = get_export_font(21)

    draw.text(
        (120, 110),
        "KONUHA",
        font=title_font,
        fill="#f7f4ff",
    )

    draw_rtl(
        draw,
        (width - 120, 130),
        "تقرير إدارة الأعضاء",
        heading_font,
        "#d7d1e4",
    )

    draw_rtl(
        draw,
        (width - 120, 185),
        "بيانات منظمة وجاهزة للمشاركة",
        small_font,
        "#8e93a6",
    )

    draw.rounded_rectangle(
        (120, 225, 390, 255),
        radius=15,
        fill="#8b5cf6",
    )

    draw.text(
        (145, 228),
        "KONUHA CONTROL",
        font=small_font,
        fill="#ffffff",
    )

    total = len(data_rows)

    referred = sum(
        1 for r in data_rows
        if r.get("من طرف", "-") not in ("-", "", None)
    )

    received = sum(
        1 for r in data_rows
        if r.get("استقبله", "-") not in ("-", "", None)
    )

    cards = [
        ("إجمالي الأعضاء", total),
        ("السجلات المرتبطة", referred),
        ("الاستقبالات", received),
        ("تاريخ التقرير", date.today().strftime("%Y-%m-%d")),
    ]

    card_top = 330
    card_w = 385
    gap = 25

    for i, (label, value) in enumerate(cards):
        x1 = 100 + i * (card_w + gap)
        x2 = x1 + card_w

        draw.rounded_rectangle(
            (x1, card_top, x2, card_top + 145),
            radius=22,
            fill="#0c0f18",
            outline="#292d3d",
            width=2,
        )

        draw_rtl(
            draw,
            (x2 - 22, card_top + 42),
            label,
            small_font,
            "#969caf",
        )

        draw.text(
            (x1 + 22, card_top + 78),
            str(value),
            font=heading_font,
            fill="#f4f2f9",
        )

    table_top = 535

    draw_rtl(
        draw,
        (width - 110, table_top),
        "سجل الأعضاء",
        heading_font,
        "#f5f2fb",
    )

    columns = [
        ("اللقب", 280),
        ("الرقم", 340),
        ("من طرف", 260),
        ("استقبله", 260),
        ("تاريخ الإضافة", 410),
    ]

    left = 110
    right = width - 110
    header_y = table_top + 65

    draw.rounded_rectangle(
        (left, header_y, right, header_y + 64),
        radius=15,
        fill="#1b1f2d",
    )

    x = left

    for label, col_width in columns:
        draw_rtl(
            draw,
            (x + col_width - 18, header_y + 32),
            label,
            small_font,
            "#c7c3d3",
        )
        x += col_width

    y = header_y + 80

    for row in data_rows[:12]:

        draw.line(
            (left, y - 10, right, y - 10),
            fill="#252938",
            width=1,
        )

        values = [
            row.get("اللقب", "-"),
            row.get("الرقم", "-"),
            row.get("من طرف", "-"),
            row.get("استقبله", "-"),
            row.get("تاريخ الإضافة", "-"),
        ]

        x = left

        for value, (_, col_width) in zip(values, columns):
            draw_rtl(
                draw,
                (x + col_width - 18, y + 25),
                value,
                small_font,
                "#e7e3ef",
            )
            x += col_width

        y += row_height

    draw_rtl(
        draw,
        (width - 110, height - 70),
        "KONUHA • تقرير مولّد من لوحة التحكم",
        small_font,
        "#72788a",
    )

    output = io.BytesIO()

    image.save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)
    return output


def make_pdf_from_png(png_bytes):
    output = io.BytesIO()

    page_width, page_height = landscape(A4)

    pdf = canvas.Canvas(
        output,
        pagesize=(page_width, page_height),
    )

    image_stream = io.BytesIO(png_bytes)

    pdf.drawImage(
        image_stream,
        0,
        0,
        width=page_width,
        height=page_height,
        preserveAspectRatio=True,
        anchor="c",
        mask="auto",
    )

    pdf.showPage()
    pdf.save()

    output.seek(0)
    return output



# ---------- CSS only; no HTML UI wrappers ----------
st.markdown(
    """
    <style>
""" + LOCAL_FONT_CSS + """

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
    
    .stApp,
    .stApp p,
    .stApp label,
    .stApp button,
    .stApp input,
    .stApp textarea,
    .stApp [data-baseweb="select"] {
        font-family: 'KONUHA Cairo', 'Cairo', sans-serif !important;
    }

    h1, h2, h3 {
        font-family: 'KONUHA Readex', 'KONUHA Cairo', sans-serif !important;
    }

    [data-testid="stMetricValue"] {
        font-family: 'KONUHA Inter', 'KONUHA Cairo', sans-serif !important;
    }
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

    st.write(
        "صدّر بياناتك كـ CSV أو Excel، "
        "أو أنشئ تقرير KONUHA مصمم بصيغة PNG و PDF."
    )

    rows = []

    for m in members:

        rows.append({
            "اللقب": m.get("nickname", ""),
            "الرقم": m.get("phone", ""),
            "من طرف": (
                supervisor_by_id(
                    supervisors,
                    m.get("referrer_id"),
                ) or {}
            ).get("name", "-"),
            "استقبله": (
                supervisor_by_id(
                    supervisors,
                    m.get("receiver_id"),
                ) or {}
            ).get("name", "-"),
            "تاريخ الإضافة": fmt_dt(
                m.get("created_at")
            ),
        })

    df = pd.DataFrame(rows)

    if df.empty:

        st.info("لا توجد بيانات للتصدير.")

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader("تقرير KONUHA")

        report_png = make_konuha_report_png(rows)
        png_bytes = report_png.getvalue()
        report_pdf = make_pdf_from_png(png_bytes)

        col_png, col_pdf = st.columns(2)

        with col_png:

            st.download_button(
                "تحميل التقرير PNG",
                data=png_bytes,
                file_name="KONUHA_report.png",
                mime="image/png",
                use_container_width=True,
            )

        with col_pdf:

            st.download_button(
                "تحميل التقرير PDF",
                data=report_pdf.getvalue(),
                file_name="KONUHA_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.caption(
            "الـ PNG والـ PDF يستخدمان نفس تصميم التقرير، "
            "حتى تبقى الكتابة العربية مرتبة عند المشاركة والطباعة."
        )

        st.divider()

        st.subheader("تصدير البيانات الخام")

        csv_data = df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            "تحميل CSV",
            data=csv_data,
            file_name="konuha_members.csv",
            mime="text/csv",
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
            data=excel.getvalue(),
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
