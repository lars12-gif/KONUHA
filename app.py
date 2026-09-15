
import streamlit as st
import pandas as pd
import base64, io, re, unicodedata
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime, date, timedelta
from supabase import create_client

st.set_page_config(page_title="KONUHA", page_icon="K", layout="wide", initial_sidebar_state="expanded")

URL = st.secrets.get("SUPABASE_URL", "")
KEY = st.secrets.get("SUPABASE_KEY", "")
PASSWORD = st.secrets.get("SITE_PASSWORD", "")
BASE = Path(__file__).parent
ASSET = BASE / "assets" / "naruto_leaf.png"

@st.cache_resource
def db():
    if not URL or not KEY:
        return None
    try:
        return create_client(URL, KEY)
    except Exception:
        return None

supabase = db()

@st.cache_data(ttl=20)
def connected():
    try:
        if supabase is None:
            return False
        supabase.table("supervisors").select("id").limit(1).execute()
        return True
    except Exception:
        return False

def norm(s):
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    for a,b in {"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي","ـ":""}.items():
        s=s.replace(a,b)
    s=re.sub(r"[\s_\-\.]+","",s)
    return re.sub(r"[^\w\u0600-\u06ff]+","",s)

def sim(a,b):
    return SequenceMatcher(None,norm(a),norm(b)).ratio()

def img64(path):
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode()

LEAF = img64(ASSET)

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("""
    <style>
    [data-testid="stHeader"],footer,#MainMenu{display:none!important}
    .stApp{background:#070914}
    .login{width:min(430px,90vw);margin:13vh auto 0;padding:42px 38px;border-radius:28px;
    background:linear-gradient(145deg,#11142a,#0a0d1c);border:1px solid #8c52d933;
    box-shadow:0 25px 80px #0008;text-align:center}
    .login h1{font:800 48px Inter,sans-serif;letter-spacing:4px;margin:0;
    background:linear-gradient(90deg,#fff,#ad6dff,#ed5ab8);-webkit-background-clip:text;color:transparent}
    .login p{font-family:Arial;color:#8e91ad;margin:8px 0 28px}
    </style>
    <div class="login"><h1>KONUHA</h1><p>نظام إدارة الأعضاء</p></div>
    """, unsafe_allow_html=True)
    with st.form("login"):
        pw=st.text_input("كلمة المرور",type="password")
        ok=st.form_submit_button("دخول",use_container_width=True)
    if ok:
        if PASSWORD and pw == PASSWORD:
            st.session_state.auth=True
            st.rerun()
        else:
            st.error("كلمة المرور غير صحيحة.")
    st.stop()

@st.cache_data(ttl=15)
def get_members():
    try:
        return supabase.table("members").select("*").order("created_at",desc=True).execute().data or []
    except Exception:
        return []

@st.cache_data(ttl=15)
def get_supervisors():
    try:
        return supabase.table("supervisors").select("*").order("created_at").execute().data or []
    except Exception:
        return []

def clear():
    get_members.clear()
    get_supervisors.clear()
    connected.clear()

def sup_name(sups,sid):
    for s in sups:
        if str(s["id"]) == str(sid):
            return s["name"]
    return "-"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=Inter:wght@400;600;700;800&family=Readex+Pro:wght@400;500;600;700&display=swap');
*{{box-sizing:border-box}}
html,body,[data-testid="stAppViewContainer"]{{
background:radial-gradient(900px 500px at 70% 0%,#56308018,transparent 65%),
radial-gradient(700px 500px at 0% 100%,#b82e8e0d,transparent 65%),#070a16!important;
color:#f5f2ff!important}}
[data-testid="stHeader"],footer,#MainMenu{{display:none!important}}
[data-testid="stSidebar"]{{width:280px!important;min-width:280px!important;
background:linear-gradient(180deg,#0c1020,#080b17)!important;border-right:1px solid #9d5cff1b!important}}
[data-testid="stSidebar"]>div:first-child{{padding:0 0 18px!important}}
.block-container{{max-width:1500px!important;padding:18px 22px 40px!important}}
.stButton>button{{font-family:Cairo,sans-serif!important;color:#b6b5ce!important;
background:transparent!important;border:1px solid transparent!important;border-radius:13px!important;
min-height:44px!important;text-align:right!important}}
.stButton>button:hover{{background:#a05cff12!important;color:#fff!important;border-color:#a05cff22!important}}
[data-testid="stSidebar"] .stButton>button{{padding-right:24px!important}}
input,textarea,[data-baseweb="select"]>div{{background:#0e1225!important;color:#fff!important;
border-color:#a35bff24!important;border-radius:12px!important}}
label{{font-family:Cairo!important;color:#b8b8ca!important}}

.brand-area{{padding:25px 15px 22px;border-bottom:1px solid #9b60ff16;margin-bottom:12px}}
.brand{{display:flex;justify-content:center;align-items:center;gap:1px;font:800 37px Inter,sans-serif;
letter-spacing:1px;color:#fff;text-shadow:0 0 25px #d76bff80}}
.brand .leaf{{width:39px;height:39px;object-fit:contain;filter:drop-shadow(0 0 9px #c65dff99)}}
.brand-sub{{text-align:center;color:#737792;font:12px Cairo;margin-top:4px}}
.side-label{{font:11px Cairo;color:#62667f;padding:10px 18px 6px}}
.nav-on button{{background:linear-gradient(90deg,#9958ff38,#d750af16)!important;color:#fff!important;
border-color:#b66aff2b!important;box-shadow:inset 4px 0 #c25cff}}
.logout button{{margin-top:18px!important;color:#cf8ed2!important}}

.top{{height:48px;display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-bottom:10px}}
.online,.offline{{padding:8px 16px;border-radius:999px;font:12px Cairo}}
.online{{border:1px solid #48e49b66;color:#64e9a8;background:#48e49b09}}
.offline{{border:1px solid #ff658266;color:#ff7f9a;background:#ff658209}}
.logout-top{{padding:8px 17px;border:1px solid #b66aff1e;border-radius:999px;color:#c7b6db;font:12px Cairo}}

.hero{{min-height:218px;border-radius:23px;border:1px solid #b66aff1b;position:relative;overflow:hidden;
padding:37px 42px;display:flex;align-items:center;
background:radial-gradient(ellipse at 78% 30%,#c55a9b33,transparent 30%),
radial-gradient(ellipse at 62% 100%,#7149c622,transparent 36%),
linear-gradient(115deg,#0a0d1c,#11152b 55%,#171126);box-shadow:0 22px 65px #0005}}
.hero:before{{content:"";position:absolute;inset:0;opacity:.18;
background:radial-gradient(circle at 72% 35%,#fff 0 1px,transparent 2px),
radial-gradient(circle at 80% 55%,#fff 0 1px,transparent 2px);
background-size:130px 100px,170px 140px}}
.hero-title{{position:relative;z-index:2;font:800 66px Inter,sans-serif;letter-spacing:2px;
background:linear-gradient(90deg,#fff,#b874ff 53%,#ec5cb8);-webkit-background-clip:text;color:transparent}}
.hero-sub{{position:relative;z-index:2;font:16px Cairo;color:#ddd9e8;margin-top:10px}}
.quote{{position:absolute;right:38px;top:68px;text-align:right;font:600 15px Cairo;color:#e9e4f0;z-index:2}}
.quote i{{display:block;width:40px;height:3px;background:#d95bc9;border-radius:9px;margin:15px 0 0 auto}}

.card{{height:138px;border-radius:20px;border:1px solid #a867ff20;padding:20px;
background:linear-gradient(145deg,#151936e8,#0d1125e8);box-shadow:0 15px 40px #0003}}
.card .ico{{float:left;width:46px;height:46px;border-radius:15px;background:#9b5cff18;
display:flex;align-items:center;justify-content:center;font-size:21px}}
.card .lbl{{font:13px Cairo;color:#b7b4c9;text-align:right}}
.card .num{{font:800 34px Inter;color:#fff;text-align:right;margin-top:9px}}
.card.green{{border-color:#49e59c28}} .card.green .num{{color:#55e4a4;font-size:27px}}
.card.blue{{border-color:#38c9df25}} .card.pink{{border-color:#ed59bd28}}

.panel{{border:1px solid #a867ff18;border-radius:22px;background:#0c1020c9;padding:20px;
box-shadow:0 18px 50px #0003;min-height:430px}}
.panel-title{{font:600 18px 'Readex Pro',Cairo;color:#eee;margin-bottom:15px}}
.empty{{height:320px;display:flex;flex-direction:column;justify-content:center;align-items:center;
color:#7f829f;font:14px Cairo;text-align:center}}
.info{{border:1px solid #e65bbf52;border-radius:22px;padding:25px;min-height:430px;
background:radial-gradient(circle at 50% 0%,#bd4d9d18,transparent 35%),#0d1021}}
.info-logo{{font:800 34px Inter;text-align:center;background:linear-gradient(90deg,#fff,#b66fff,#ec5ab7);
-webkit-background-clip:text;color:transparent}}
.info h3{{font:600 15px Cairo;text-align:center;color:#eee;margin:8px 0 20px}}
.badge{{display:flex;gap:12px;align-items:center;margin:17px 0}}
.badge .bicon{{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#aaa6ff12}}
.badge b{{color:#f0edf7;font:600 13px Cairo}}
.badge span{{display:block;color:#8589a3;font:11px Cairo}}
.cloud{{text-align:center;font-size:42px;margin-top:20px;opacity:.65}}
.section-head{{font:700 24px 'Readex Pro',Cairo;color:#fff;margin:8px 0 18px}}
</style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page="الرئيسية"

nav=[("⌂","الرئيسية"),("♟","الأعضاء"),("＋","إضافة عضو"),("⬡","المشرفين"),
     ("✚","إضافة مشرف"),("▥","الإحصائيات"),("⇩","التصدير"),("⌫","الحذف")]

with st.sidebar:
    leaf_html=f'<img class="leaf" src="data:image/png;base64,{LEAF}">' if LEAF else "<span>O</span>"
    st.markdown(f"""
    <div class="brand-area">
      <div class="brand">K{leaf_html}NUHA</div>
      <div class="brand-sub">نظام إدارة الأعضاء</div>
    </div>
    <div class="side-label">القائمة الرئيسية</div>
    """,unsafe_allow_html=True)
    for icon,label in nav:
        active=st.session_state.page==label
        if active: st.markdown('<div class="nav-on">',unsafe_allow_html=True)
        if st.button(f"{icon}   {label}",key="nav_"+label,use_container_width=True):
            st.session_state.page=label
            st.rerun()
        if active: st.markdown('</div>',unsafe_allow_html=True)
    st.markdown('<div class="logout">',unsafe_allow_html=True)
    if st.button("↪   تسجيل الخروج",use_container_width=True):
        st.session_state.auth=False
        st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)

ok=connected()
status="online" if ok else "offline"
status_text="🟢 متصل بـ Supabase" if ok else "🔴 غير متصل بـ Supabase"
st.markdown(f'<div class="top"><div class="{status}">{status_text}</div><div class="logout-top">KONUHA</div></div>',unsafe_allow_html=True)

ms=get_members()
ss=get_supervisors()

if st.session_state.page=="الرئيسية":
    st.markdown("""
    <div class="hero">
      <div><div class="hero-title">KONUHA</div><div class="hero-sub">نظام إدارة الأعضاء والمشرفين</div></div>
      <div class="quote">"الأشياء العظيمة<br>تبدأ بخطوة صغيرة"<i></i></div>
    </div>
    """,unsafe_allow_html=True)

    today_count=0
    for m in ms:
        try:
            if datetime.fromisoformat(m["created_at"].replace("Z","+00:00")).date()==date.today():
                today_count+=1
        except: pass

    a,b,c,d=st.columns(4)
    vals=[("👥","إجمالي الأعضاء",len(ms),""),("🛡️","المشرفين",len(ss),"pink"),
          ("▣","أعضاء اليوم",today_count,"blue"),("🔗","حالة النظام","متصل" if ok else "غير متصل","green")]
    for col,(ico,lbl,num,cl) in zip([a,b,c,d],vals):
        with col:
            st.markdown(f'<div class="card {cl}"><div class="ico">{ico}</div><div class="lbl">{lbl}</div><div class="num">{num}</div></div>',unsafe_allow_html=True)

    st.write("")
    left,right=st.columns([2.25,.78],gap="large")
    with left:
        st.markdown('<div class="panel"><div class="panel-title">♟ آخر الأعضاء</div>',unsafe_allow_html=True)
        if ms:
            rows=[{"اللقب":m.get("nickname",""),"الرقم":m.get("phone",""),
                   "من طرف":sup_name(ss,m.get("referrer_id")),"استقبله":sup_name(ss,m.get("receiver_id")),
                   "تاريخ الإضافة":m.get("created_at","")} for m in ms[:10]]
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=315)
        else:
            st.markdown('<div class="empty"><div style="font-size:30px">♙</div><br>لا توجد أعضاء مسجلين حالياً</div>',unsafe_allow_html=True)
        st.markdown('</div>',unsafe_allow_html=True)
    with right:
        st.markdown("""
        <div class="info">
          <div class="info-logo">KONUHA</div>
          <h3>معاً نصنع مجتمعاً أفضل</h3><hr>
          <div class="badge"><div class="bicon">👥</div><div><b>إدارة الأعضاء بسهولة</b><span>نظام متكامل لإدارة أعضائك</span></div></div>
          <div class="badge"><div class="bicon">🛡️</div><div><b>أمان ومرونة</b><span>بياناتك في بيئة آمنة</span></div></div>
          <div class="badge"><div class="bicon">⚡</div><div><b>بسرعة وكفاءة</b><span>لجميع احتياجاتك الإدارية</span></div></div>
          <div class="cloud">☁️</div>
        </div>
        """,unsafe_allow_html=True)

elif st.session_state.page=="الأعضاء":
    st.markdown('<div class="section-head">الأعضاء</div>',unsafe_allow_html=True)
    q=st.text_input("بحث داخل الأعضاء",placeholder="اكتب اللقب أو الرقم...")
    rows=[]
    for m in ms:
        if q and norm(q) not in norm(m.get("nickname","")) and q not in m.get("phone",""): continue
        rows.append({"اللقب":m.get("nickname",""),"الرقم":m.get("phone",""),
                     "من طرف":sup_name(ss,m.get("referrer_id")),"استقبله":sup_name(ss,m.get("receiver_id")),
                     "تاريخ الإضافة":m.get("created_at","")})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

elif st.session_state.page=="إضافة عضو":
    st.markdown('<div class="section-head">إضافة عضو</div>',unsafe_allow_html=True)
    if not ss:
        st.warning("أضف مشرفاً أولاً.")
    else:
        with st.form("add_member"):
            nick=st.text_input("اللقب"); phone=st.text_input("الرقم")
            rn=st.selectbox("من طرف",[s["name"] for s in ss]); rv=st.selectbox("استقبله",[s["name"] for s in ss])
            force=st.checkbox("إضافة إجبارية عند وجود لقب مشابه")
            send=st.form_submit_button("إضافة العضو",use_container_width=True)
        if send:
            if not nick.strip() or not phone.strip(): st.error("أكمل البيانات.")
            else:
                dup=supabase.table("members").select("id").eq("phone",phone.strip()).limit(1).execute().data
                similar=[m for m in ms if sim(m.get("nickname",""),nick)>=.82]
                if dup: st.error("هذا الرقم مسجل مسبقاً.")
                elif similar and not force: st.warning("يوجد لقب مشابه: "+", ".join(x["nickname"] for x in similar[:5]))
                else:
                    r=next(x for x in ss if x["name"]==rn); v=next(x for x in ss if x["name"]==rv)
                    supabase.table("members").insert({"nickname":nick.strip(),"normalized_nickname":norm(nick),
                    "phone":phone.strip(),"referrer_id":r["id"],"receiver_id":v["id"]}).execute()
                    clear(); st.success("تمت إضافة العضو بنجاح.")

elif st.session_state.page=="المشرفين":
    st.markdown('<div class="section-head">المشرفين</div>',unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{"الاسم":s["name"],"اللقب":s["nickname"],"الحالة":"فعال" if s.get("is_active",True) else "متوقف",
    "تاريخ الإضافة":s["created_at"]} for s in ss]),use_container_width=True,hide_index=True)

elif st.session_state.page=="إضافة مشرف":
    st.markdown('<div class="section-head">إضافة مشرف</div>',unsafe_allow_html=True)
    with st.form("add_supervisor"):
        n=st.text_input("اسم المشرف"); nick=st.text_input("لقب المشرف")
        send=st.form_submit_button("إضافة المشرف",use_container_width=True)
    if send:
        if n.strip() and nick.strip():
            supabase.table("supervisors").insert({"name":n.strip(),"nickname":nick.strip(),
            "normalized_name":norm(n),"normalized_nickname":norm(nick),"is_active":True}).execute()
            clear(); st.success("تمت إضافة المشرف.")
        else: st.error("أكمل البيانات.")

elif st.session_state.page=="الإحصائيات":
    st.markdown('<div class="section-head">الإحصائيات</div>',unsafe_allow_html=True)
    who=st.selectbox("المشرف",["الكل"]+[s["name"] for s in ss])
    per=st.selectbox("الفترة",["الكل","اليوم","امس","هذا_الشهر","تاريخ محدد"])
    sd=st.date_input("التاريخ",date.today()) if per=="تاريخ محدد" else None
    filt=[]
    for m in ms:
        if who!="الكل" and sup_name(ss,m.get("referrer_id"))!=who: continue
        try: dt=datetime.fromisoformat(m["created_at"].replace("Z","+00:00")).date()
        except: continue
        if per=="اليوم" and dt!=date.today(): continue
        if per=="امس" and dt!=date.today()-timedelta(days=1): continue
        if per=="هذا_الشهر" and (dt.year,dt.month)!=(date.today().year,date.today().month): continue
        if per=="تاريخ محدد" and dt!=sd: continue
        filt.append(m)
    x,y,z=st.columns(3)
    for col,title,val in [(x,"النتيجة",len(filt)),(y,"المشرف",who),(z,"الفترة",per)]:
        with col: st.markdown(f'<div class="card"><div class="lbl">{title}</div><div class="num">{val}</div></div>',unsafe_allow_html=True)

elif st.session_state.page=="التصدير":
    st.markdown('<div class="section-head">التصدير</div>',unsafe_allow_html=True)
    rows=[{"اللقب":m.get("nickname",""),"الرقم":m.get("phone",""),"من طرف":sup_name(ss,m.get("referrer_id")),
    "استقبله":sup_name(ss,m.get("receiver_id")),"تاريخ الإضافة":m.get("created_at","")} for m in ms]
    df=pd.DataFrame(rows)
    st.download_button("⇩ تحميل CSV",df.to_csv(index=False).encode("utf-8-sig"),"konuha_members.csv","text/csv",use_container_width=True)
    buf=io.BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w: df.to_excel(w,index=False,sheet_name="Members")
    st.download_button("⇩ تحميل Excel",buf.getvalue(),"konuha_members.xlsx",use_container_width=True)

elif st.session_state.page=="الحذف":
    st.markdown('<div class="section-head">الحذف</div>',unsafe_allow_html=True)
    if not ms: st.info("لا توجد أعضاء للحذف.")
    else:
        target=st.selectbox("اختر العضو",[m["nickname"] for m in ms])
        confirm=st.checkbox("أؤكد أنني أريد حذف هذا العضو نهائياً")
        if st.button("حذف العضو نهائياً",use_container_width=True):
            if not confirm: st.warning("فعّل التأكيد أولاً.")
            else:
                m=next(x for x in ms if x["nickname"]==target)
                supabase.table("members").delete().eq("id",m["id"]).execute()
                clear(); st.success("تم الحذف."); st.rerun()
