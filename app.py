"""우리 둘의 하루 — Streamlit 커플 다이어리.
실행: streamlit run app.py
Streamlit Cloud Secrets 설정 예시는 함께 제공된 안내를 참고하세요.
데이터는 GITHUB_DATA_REPO(반드시 비공개)의 DATA_PATH에 자동 생성됩니다.
"""
import base64
import copy
import hmac
import io
import json
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import qrcode
import requests
import streamlit as st

st.set_page_config(page_title="우리 둘의 하루", page_icon="💌", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>
.block-container{max-width:460px;padding:1rem .9rem .5rem!important;}
header[data-testid="stHeader"]{display:none;}
[data-testid="stVerticalBlock"]{gap:.38rem;}
[data-testid="stHeadingWithActionElements"]{margin:0;}
h3{padding:.15rem 0!important;font-size:1.3rem!important;}
p{margin-bottom:.25rem!important;}
[data-testid="stCaptionContainer"]{font-size:.75rem;}
.stButton button,.stDownloadButton button{min-height:2.25rem;}
[data-testid="stTextArea"] textarea{font-size:16px;}
[data-testid="stSelectbox"] input,[data-testid="stTextInput"] input{font-size:16px;}
.stApp{background:linear-gradient(160deg,#fff8fa,#faf8ff);}
[data-testid="stForm"]{border:1px solid #f0dce5;border-radius:16px;padding:.65rem;}
@media(max-width:480px){.block-container{padding-top:.6rem!important;} [data-testid="stHorizontalBlock"]{gap:.4rem;}}
</style>""", unsafe_allow_html=True)

KST = ZoneInfo("Asia/Seoul")
MOODS = ["😊 행복", "🥰 설렘", "😌 평온", "😢 슬픔", "😮‍💨 지침", "😤 속상"]


def setting(key, default=""):
    return str(st.secrets.get(key, default)).strip()


try:
    TOKEN = setting("GITHUB_TOKEN")
    REPO = setting("GITHUB_DATA_REPO")
    PATH = setting("DATA_PATH", "couple_diary.json").strip("/")
    PUBLIC_URL = setting("APP_URL")
    NAMES = {"a": setting("PARTNER_1_NAME", "나무"), "b": setting("PARTNER_2_NAME", "하늘")}
    PASSWORDS = {"a": setting("PARTNER_1_PASSWORD"), "b": setting("PARTNER_2_PASSWORD")}
except Exception:
    st.error("먼저 Streamlit 앱 설정의 Secrets를 입력해 주세요. 제공된 설치 안내를 확인하세요.")
    st.stop()

if not TOKEN or REPO.count("/") != 1 or not all(PASSWORDS.values()):
    st.error("Secrets에 GITHUB_TOKEN, GITHUB_DATA_REPO, 두 사람의 비밀번호가 필요합니다.")
    st.stop()
if PASSWORDS["a"] == PASSWORDS["b"] or min(map(len, PASSWORDS.values())) < 12:
    st.error("각자의 비밀번호를 서로 다르게, 각각 12자 이상으로 설정하세요.")
    st.stop()

HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
API = f"https://api.github.com/repos/{REPO}"


class StorageError(Exception):
    pass


def api(method, url, **kwargs):
    try:
        return requests.request(method, url, headers=HEADERS, timeout=20, **kwargs)
    except requests.RequestException:
        raise StorageError("저장소에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.") from None


@st.cache_data(ttl=300, show_spinner=False)
def check_private(repo, _token):
    # 공개 저장소에 개인 일기를 실수로 저장하지 못하도록 차단합니다.
    response = api("GET", f"https://api.github.com/repos/{repo}")
    if response.status_code != 200:
        raise StorageError("저장소 접근 실패: 저장소 이름과 토큰의 Contents 읽기/쓰기 권한을 확인하세요.")
    if not response.json().get("private"):
        raise StorageError("일기는 반드시 비공개(Private) 저장소에 저장해야 합니다.")
    return True


def read_data():
    response = api("GET", f"{API}/contents/{PATH}", params={"_": time.time_ns()})
    if response.status_code == 404:
        return {"version": 1, "entries": []}, None
    if response.status_code != 200:
        raise StorageError("일기를 불러오지 못했어요. 토큰 권한 또는 GitHub 사용 제한을 확인하세요.")
    try:
        body = response.json()
        data = json.loads(base64.b64decode(body["content"]).decode("utf-8"))
        if data.get("version") != 1 or not isinstance(data.get("entries"), list):
            raise ValueError
        return data, body["sha"]
    except (ValueError, KeyError, TypeError):
        raise StorageError("저장 파일 형식을 읽을 수 없어요. 기존 데이터는 덮어쓰지 않았습니다.") from None


def update_data(transform):
    # 매 시도마다 최신 내용을 읽고 병합합니다. SHA 충돌 시 다시 시도합니다.
    for attempt in range(4):
        current, sha = read_data()
        updated = transform(copy.deepcopy(current))
        if updated == current:
            return
        content = base64.b64encode(json.dumps(updated, ensure_ascii=False, indent=2).encode()).decode()
        payload = {"message": "Update shared diary", "content": content}
        if sha:
            payload["sha"] = sha
        response = api("PUT", f"{API}/contents/{PATH}", json=payload)
        if response.status_code in (200, 201):
            return
        if response.status_code in (409, 422):
            time.sleep(.3 * (attempt + 1))
            continue
        raise StorageError("저장하지 못했어요. 토큰의 Contents 쓰기 권한을 확인하고 다시 시도하세요.")
    raise StorageError("두 사람이 동시에 저장 중이에요. 잠시 후 다시 눌러 주세요.")


def timestamp():
    return datetime.now(KST).isoformat(timespec="seconds")


def short_date(value):
    return datetime.fromisoformat(value).astimezone(KST).strftime("%m/%d %H:%M")


st.markdown("### 💌 우리 둘의 하루")

if "who" not in st.session_state:
    st.caption("오늘의 기분과 짧은 마음을, 가장 가까운 사람에게.")
    with st.form("login"):
        person = st.selectbox("나는", ["a", "b"], format_func=lambda x: NAMES[x])
        password = st.text_input("내 비밀번호", type="password")
        enter = st.form_submit_button("우리 공간 열기", use_container_width=True)
    if enter:
        if hmac.compare_digest(password.encode(), PASSWORDS[person].encode()):
            try:
                check_private(REPO, TOKEN)
            except StorageError as exc:
                st.error(str(exc))
            else:
                st.session_state.who = person
                st.rerun()
        else:
            st.error("이름 또는 비밀번호를 확인해 주세요.")
    st.caption("비밀번호는 주소나 QR에 포함되지 않아요.")
    st.stop()

ME = st.session_state.who
OTHER = "b" if ME == "a" else "a"


@st.fragment(run_every="30s")
def diary():
    try:
        check_private(REPO, TOKEN)
        data, _ = read_data()
    except StorageError as exc:
        st.error(str(exc))
        st.button("다시 연결", on_click=st.rerun)
        return

    top = st.columns([6, 1, 1])
    top[0].caption(f"{NAMES[ME]} → {NAMES[OTHER]} · 30초마다 새로고침")
    if top[1].button("↻", help="지금 새로고침"):
        st.rerun(scope="fragment")
    with top[2].popover("⋯"):
        st.caption("QR은 앱 주소만 담습니다. 상대방도 자신의 비밀번호로 로그인하세요.")
        if PUBLIC_URL.startswith("https://"):
            image = qrcode.make(PUBLIC_URL)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            st.image(buffer.getvalue(), width=180)
            st.download_button("QR 다운로드", buffer.getvalue(), "couple-diary-qr.png", "image/png")
        else:
            st.caption("배포 후 Secrets의 APP_URL에 https://로 시작하는 앱 주소를 입력하면 QR이 표시됩니다.")
        if st.button("로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    notice = st.session_state.pop("notice", None)
    if notice:
        st.caption(notice)

    with st.form("write", clear_on_submit=True):
        mood = st.selectbox("오늘 기분", MOODS, label_visibility="collapsed")
        text = st.text_area("오늘의 마음", placeholder="오늘 너에게 전하고 싶은 이야기… (240자)", height=90, max_chars=240, label_visibility="collapsed")
        send = st.form_submit_button("💌 마음 보내기", use_container_width=True)
    if send:
        if not text.strip():
            st.warning("마음을 한 줄 적어 주세요.")
        else:
            # 세션에서 재시도할 때에도 동일한 ID를 사용해 중복 생성을 막습니다.
            signature = (mood, text.strip())
            pending = st.session_state.get("pending")
            if not pending or pending["signature"] != signature:
                pending = {"signature": signature, "entry": {"id": str(uuid.uuid4()), "author": ME, "mood": mood, "text": text.strip(), "created_at": timestamp(), "read_at": None}}
                st.session_state.pending = pending
            entry = pending["entry"]

            def add(document):
                if not any(x["id"] == entry["id"] for x in document["entries"]):
                    document["entries"].append(entry)
                return document

            try:
                update_data(add)
            except StorageError as exc:
                st.error(str(exc))
            else:
                st.session_state.pop("pending", None)
                st.session_state.notice = "보냈어요 💗"
                st.rerun(scope="fragment")

    entries = sorted(data["entries"], key=lambda x: x["created_at"], reverse=True)
    unread = sum(x["author"] == OTHER and not x.get("read_at") for x in entries)
    st.caption(f"📬 우리 기록 · 안 읽은 마음 {unread}개")
    if not entries:
        st.info("아직 일기가 없어요. 첫 마음을 보내 보세요 💗")
        return

    def label(entry_id):
        entry = next(x for x in entries if x["id"] == entry_id)
        badge = "✓" if entry.get("read_at") else "●"
        return f"{badge} {short_date(entry['created_at'])} · {NAMES[entry['author']]} · {entry['mood']}"

    selected = st.selectbox("기록 선택", [x["id"] for x in entries], format_func=label, label_visibility="collapsed", key="selected_entry")
    entry = next(x for x in entries if x["id"] == selected)
    # 고정 높이로 긴 글이 화면 전체를 밀어내지 않습니다.
    st.text_area("선택한 일기", value=entry["text"], height=105, disabled=True, label_visibility="collapsed", key=f"body_{selected}")
    if entry["author"] == ME:
        st.caption(f"✓ {NAMES[OTHER]} 확인 · {short_date(entry['read_at'])}" if entry.get("read_at") else f"아직 {NAMES[OTHER]}의 확인 전이에요 🌙")
    elif entry.get("read_at"):
        st.caption(f"✓ 내가 확인한 마음 · {short_date(entry['read_at'])}")
    else:
        if st.button("✓ 읽었어요 — 상대에게 알리기", use_container_width=True):
            def mark(document):
                for item in document["entries"]:
                    if item["id"] == selected and item["author"] != ME and not item.get("read_at"):
                        item["read_at"] = timestamp()
                return document
            try:
                update_data(mark)
            except StorageError as exc:
                st.error(str(exc))
            else:
                st.rerun(scope="fragment")


diary()
