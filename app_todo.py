# app_todo.py
import streamlit as st
from pyrebase import pyrebase                       # client-side Auth
import firebase_admin                               # admin SDK (Firestore)
from firebase_admin import credentials, firestore
from datetime import datetime

# ---------- Firebase 초기화 (한 번만) ----------
@st.cache_resource
def init_firebase():
    # secrets.toml에 다음 두 블록을 준비해 두세요.
    # [firebase]           # pyrebase용
    # apiKey = "..."
    # authDomain = "..."
    # ...
    #
    # [firebase_admin]     # admin SDK 서비스 계정 JSON
    # type = "service_account"
    # project_id = "..."
    # ...
    pb = pyrebase.initialize_app(st.secrets["firebase"])
    pb_auth = pb.auth()

    if not firebase_admin._apps:
        cred = credentials.Certificate(st.secrets["firebase_admin"])
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    return pb_auth, db

pb_auth, db = init_firebase()

# ---------- 페이지 ----------

def home_page():
    st.title("📝 할일관리 앱 개요")
    st.markdown("""
    - Firebase Email/Password 인증  
    - Firestore 에 개인 TODO 저장  
    - Streamlit **st.navigation** 멀티페이지 구조  
    """)

def login_page():
    st.title("🔑 로그인")
    email = st.text_input("이메일")
    pw    = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        try:
            user = pb_auth.sign_in_with_email_and_password(email, pw)
            st.session_state.user = user  # 토큰·UID 저장
            st.success("로그인 성공")
            st.rerun()
        except Exception as e:
            st.error(f"로그인 실패: {e}")

def signup_page():
    st.title("🆕 회원가입")
    email = st.text_input("이메일")
    pw1   = st.text_input("비밀번호", type="password")
    pw2   = st.text_input("비밀번호 확인", type="password")
    if st.button("가입"):
        if pw1 != pw2:
            st.warning("비밀번호가 일치하지 않습니다.")
        else:
            try:
                pb_auth.create_user_with_email_and_password(email, pw1)
                st.success("가입 완료! 로그인 해 주세요.")
            except Exception as e:
                st.error(f"가입 실패: {e}")

def reset_page():
    st.title("🔒 비밀번호 재설정")
    email = st.text_input("가입한 이메일")
    if st.button("재설정 메일 발송"):
        try:
            pb_auth.send_password_reset_email(email)
            st.success("메일이 발송되었습니다.")
        except Exception as e:
            st.error(f"실패: {e}")

def logout_page():
    st.session_state.clear()
    st.success("로그아웃 되었습니다.")
    st.switch_page("app_todo.py")      # 메인으로 복귀:contentReference[oaicite:2]{index=2}

def profile_page():
    user = st.session_state.get("user")
    st.title("🙋‍♂️ 사용자 정보")
    if user:
        info = pb_auth.get_account_info(user["idToken"])
        st.json(info)
    else:
        st.info("로그인이 필요합니다.")

def todo_page():
    st.title("✅ 내 할일 관리")
    user = st.session_state.get("user")
    if not user:
        st.warning("로그인 후 이용하세요.")
        return
    uid = user["localId"]
    todos_ref = db.collection("users").document(uid).collection("todos")

    # 새 할일 추가 ----------------------------
    with st.form(key="add_todo", clear_on_submit=True):
        text = st.text_input("할일 내용")
        submitted = st.form_submit_button("추가")
        if submitted and text:
            todos_ref.add({"text": text,
                           "done": False,
                           "created": datetime.utcnow()})

    st.divider()

    # 목록 표시 & 상태 변경 --------------------
    docs = list(todos_ref.stream())
    for d in docs:
        data = d.to_dict()
        col1, col2 = st.columns([8,1])
        with col1:
            st.checkbox(data["text"], value=data["done"],
                        key=d.id,
                        on_change=lambda doc=d.id, val=not data["done"]:
                            todos_ref.document(doc).update({"done": val}))
        with col2:
            if st.button("🗑️", key=f"del_{d.id}"):
                todos_ref.document(d.id).delete()
                st.experimental_rerun()

# ---------- st.Page 래핑 ----------
home       = st.Page(home_page,   title="홈",        icon=":material/home:",  default=True)
login_pg   = st.Page(login_page,  title="로그인",    icon=":material/login:")
signup_pg  = st.Page(signup_page, title="회원가입",  icon=":material/person_add:")
reset_pg   = st.Page(reset_page,  title="비밀번호 찾기", icon=":material/password:")
logout_pg  = st.Page(logout_page, title="로그아웃",  icon=":material/logout:")
profile_pg = st.Page(profile_page,title="사용자정보", icon=":material/account_circle:")
todo_pg    = st.Page(todo_page,   title="할일관리",  icon=":material/checklist:")

# ---------- Navigation ----------
logged_in = "user" in st.session_state
if logged_in:
    current = st.navigation(
        {"계정":  [logout_pg, profile_pg],
         "기능":  [todo_pg]},
        position="sidebar", expanded=True
    )                                 # 섹션별 메뉴 그룹화
else:
    current = st.navigation(
        [home, login_pg, signup_pg, reset_pg],
        position="sidebar"
    )
current.run()                         # 선택된 페이지 실행  :contentReference[oaicite:3]{index=3}
