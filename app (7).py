import json
from datetime import datetime
from io import StringIO

import streamlit as st

st.set_page_config(page_title="우리집 장바구니", page_icon="🛒", layout="centered")

# Simple green theme
st.markdown("""
<style>
    .stApp { background: #f3f7f1; }
    .block-container { max-width: 920px; padding-top: 2rem; }
    h1, h2, h3, p, label { color: #123f31; }
    div.stButton > button[kind="primary"] {
        background: #216344; border: 0; color: white; border-radius: 12px;
        min-height: 3rem; font-weight: 700;
    }
    div.stButton > button { border-radius: 10px; }
    div[data-testid="stAlert"] { border-radius: 14px; }
    .intro { color: #45665a; font-size: 1.15rem; }
</style>
""", unsafe_allow_html=True)

if "items" not in st.session_state:
    st.session_state.items = []
if "purchased" not in st.session_state:
    st.session_state.purchased = []

st.caption("설치 없이 쓰는 · 내 기기용")
st.title("🛒 우리집 장바구니")
st.markdown('<p class="intro">필요한 물건을 적고, 장볼 때 하나씩 체크해요.</p>', unsafe_allow_html=True)

st.info(
    "**이 버전은 현재 실행 중인 기기에 목록을 관리합니다.** "
    "아래에서 목록 파일을 내려받아 백업하거나 다른 기기에 전달할 수 있어요. "
    "브라우저/서버 환경에 따라 데이터가 유지되지 않을 수 있으니 파일로 백업해 주세요."
)

with st.container(border=True):
    st.subheader("＋ 필요한 물건 추가")
    with st.form("add_item", clear_on_submit=True):
        name = st.text_input("물건 이름", placeholder="예: 우유")
        c1, c2 = st.columns(2)
        with c1:
            quantity = st.text_input("수량 (선택)", placeholder="예: 2개")
        with c2:
            memo = st.text_input("메모 (선택)", placeholder="예: 작은 팩")
        submitted = st.form_submit_button("장보기 목록에 추가", type="primary", use_container_width=True)
        if submitted:
            if name.strip():
                st.session_state.items.append({
                    "id": f"{datetime.now().timestamp()}",
                    "name": name.strip(),
                    "quantity": quantity.strip(),
                    "memo": memo.strip(),
                    "added": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"'{name.strip()}'을(를) 추가했어요.")
                st.rerun()
            else:
                st.warning("물건 이름을 입력해 주세요.")

tab_list, tab_done = st.tabs([
    f"📝 살 물건 {len(st.session_state.items)}",
    f"☑️ 구매 내역 {len(st.session_state.purchased)}"
])

with tab_list:
    st.caption(f"살 물건 {len(st.session_state.items)}개 · 구매 내역 {len(st.session_state.purchased)}개")
    if not st.session_state.items:
        st.markdown("<div style='text-align:center;padding:2.8rem 0;color:#58766a;font-size:1.2rem;'>장바구니가 비었어요. 필요한 물건을 추가해 보세요!</div>", unsafe_allow_html=True)
    else:
        for item in st.session_state.items[:]:
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f"**{item['name']}**")
                    details = " · ".join(x for x in [item["quantity"], item["memo"]] if x)
                    if details:
                        st.caption(details)
                with right:
                    if st.button("구매 완료", key=f"buy_{item['id']}", use_container_width=True):
                        st.session_state.items.remove(item)
                        item["purchased"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.session_state.purchased.insert(0, item)
                        st.rerun()
                    if st.button("삭제", key=f"del_{item['id']}", use_container_width=True):
                        st.session_state.items.remove(item)
                        st.rerun()

with tab_done:
    if not st.session_state.purchased:
        st.markdown("<div style='text-align:center;padding:2.8rem 0;color:#58766a;'>아직 구매한 물건이 없어요.</div>", unsafe_allow_html=True)
    else:
        for item in st.session_state.purchased[:]:
            with st.container(border=True):
                left, right = st.columns([5, 1])
                with left:
                    st.markdown(f"~~{item['name']}~~")
                    details = " · ".join(x for x in [item["quantity"], item["memo"]] if x)
                    if details:
                        st.caption(details)
                    st.caption(f"구매 완료: {item.get('purchased', '-')}")
                with right:
                    if st.button("목록 복원", key=f"restore_{item['id']}", use_container_width=True):
                        st.session_state.purchased.remove(item)
                        item.pop("purchased", None)
                        st.session_state.items.append(item)
                        st.rerun()
                    if st.button("삭제", key=f"del_done_{item['id']}", use_container_width=True):
                        st.session_state.purchased.remove(item)
                        st.rerun()

st.divider()
st.subheader("📦 목록 백업 및 불러오기")
payload = {
    "items": st.session_state.items,
    "purchased": st.session_state.purchased,
    "exported_at": datetime.now().isoformat(timespec="seconds")
}
st.download_button(
    "목록 파일 다운로드 (JSON)",
    data=json.dumps(payload, ensure_ascii=False, indent=2),
    file_name="우리집_장바구니_백업.json",
    mime="application/json",
    use_container_width=True
)

uploaded = st.file_uploader("이전에 저장한 백업 파일 불러오기", type=["json"])
if uploaded is not None:
    if st.button("백업 파일 적용", type="primary"):
        try:
            data = json.load(uploaded)
            if not isinstance(data.get("items", []), list) or not isinstance(data.get("purchased", []), list):
                raise ValueError("올바른 장바구니 백업 파일이 아닙니다.")
            st.session_state.items = data.get("items", [])
            st.session_state.purchased = data.get("purchased", [])
            st.success("백업 파일을 불러왔어요.")
            st.rerun()
        except (json.JSONDecodeError, ValueError, TypeError):
            st.error("파일을 읽을 수 없어요. 올바른 백업 파일인지 확인해 주세요.")

st.caption("※ 가족 간 실시간 자동 공유 기능은 포함되어 있지 않습니다. 백업 파일을 전달해 목록을 공유할 수 있어요.")
