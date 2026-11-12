import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta

st.set_page_config(
    page_title="스마트팜 작물 성장 모니터링",
    page_icon="🌱",
    layout="wide",
)

# -----------------------------
# 기본 설정 및 샘플 데이터
# -----------------------------
CROP_INFO = {
    "토마토": {"temp": (18, 28), "humidity": (55, 75), "light": (6, 10), "days": 90},
    "딸기": {"temp": (15, 25), "humidity": (60, 80), "light": (6, 10), "days": 120},
    "상추": {"temp": (15, 22), "humidity": (50, 70), "light": (4, 8), "days": 45},
    "파프리카": {"temp": (20, 28), "humidity": (60, 80), "light": (6, 10), "days": 100},
}

STAGES = {
    "토마토": [(0, "정식/활착"), (15, "생장기"), (40, "개화기"), (55, "착과기"), (75, "수확기")],
    "딸기": [(0, "정식/활착"), (20, "생장기"), (50, "개화기"), (70, "착과기"), (95, "수확기")],
    "상추": [(0, "정식/활착"), (7, "생장기"), (25, "결구기"), (35, "수확 준비")],
    "파프리카": [(0, "정식/활착"), (20, "생장기"), (45, "개화기"), (65, "착과기"), (85, "수확기")],
}


def stage_for(crop, elapsed_days):
    stage = STAGES[crop][0][1]
    for day_mark, name in STAGES[crop]:
        if elapsed_days >= day_mark:
            stage = name
    return stage


def make_sample_data():
    now = datetime.now()
    dates = pd.date_range(end=now, periods=24, freq="h")
    rows = []
    for i, ts in enumerate(dates):
        # 화면 시연을 위한 예시 센서 데이터입니다.
        rows.append({
            "측정 시각": ts,
            "온도(℃)": round(22 + 3 * __import__("math").sin(i / 3.5), 1),
            "습도(%)": round(66 + 8 * __import__("math").sin(i / 4.2 + 1), 1),
            "조도(시간)": round(7.5 + 1.2 * __import__("math").sin(i / 5), 1),
            "토양 수분(%)": round(48 + 6 * __import__("math").sin(i / 4 + 2), 1),
        })
    return pd.DataFrame(rows)


if "sensor_data" not in st.session_state:
    st.session_state.sensor_data = make_sample_data()
if "growth_log" not in st.session_state:
    st.session_state.growth_log = []

# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.title("🌿 스마트팜 관리")
st.sidebar.caption("작물 생육 및 환경 모니터링")

farm_name = st.sidebar.text_input("농장 이름", "우리 스마트팜")
crop = st.sidebar.selectbox("재배 작물", list(CROP_INFO.keys()))
planting_date = st.sidebar.date_input("정식일", date.today() - timedelta(days=35))
area = st.sidebar.number_input("재배 면적 (㎡)", min_value=1.0, value=100.0, step=10.0)

elapsed_days = max(0, (date.today() - planting_date).days)
crop_info = CROP_INFO[crop]
growth_stage = stage_for(crop, elapsed_days)
progress = min(100, int(elapsed_days / crop_info["days"] * 100))

st.title("🌱 작물 성장 상태 모니터링")
st.caption(f"{farm_name} · {date.today().strftime('%Y년 %m월 %d일')} 기준")
st.info("현재 화면은 예시 데이터로 작동합니다. 실제 온습도·조도 센서와 연결하려면 센서 또는 서버에서 받은 값을 입력/연동해야 합니다.")

# -----------------------------
# 현재 센서 상태
# -----------------------------
latest = st.session_state.sensor_data.iloc[-1]
temp = float(latest["온도(℃)"])
humidity = float(latest["습도(%)"])
light = float(latest["조도(시간)"])
soil = float(latest["토양 수분(%)"])

temp_ok = crop_info["temp"][0] <= temp <= crop_info["temp"][1]
humidity_ok = crop_info["humidity"][0] <= humidity <= crop_info["humidity"][1]
light_ok = crop_info["light"][0] <= light <= crop_info["light"][1]
soil_ok = 35 <= soil <= 65
ok_count = sum([temp_ok, humidity_ok, light_ok, soil_ok])
if ok_count == 4:
    overall = "양호"
    status_color = "green"
elif ok_count >= 2:
    overall = "주의"
    status_color = "orange"
else:
    overall = "점검 필요"
    status_color = "red"

m1, m2, m3, m4 = st.columns(4)
m1.metric("현재 온도", f"{temp:.1f} ℃", "적정" if temp_ok else "확인 필요")
m2.metric("현재 습도", f"{humidity:.1f} %", "적정" if humidity_ok else "확인 필요")
m3.metric("일일 조도", f"{light:.1f} 시간", "적정" if light_ok else "확인 필요")
m4.metric("토양 수분", f"{soil:.1f} %", "적정" if soil_ok else "확인 필요")

left, right = st.columns([1.3, 1])
with left:
    st.subheader("작물 성장 정보")
    st.markdown(f"### {crop} · {growth_stage}")
    st.progress(progress / 100, text=f"예상 재배 기간 진행률 {progress}%")
    st.write(f"- 정식 후 경과: **{elapsed_days}일**")
    st.write(f"- 참고 재배 기간: **약 {crop_info['days']}일**")
    st.write(f"- 재배 면적: **{area:,.1f}㎡**")
    st.write(f"- 생육 상태 종합: **:{status_color}[{overall}]**")
with right:
    st.subheader("생육 환경 적정 범위")
    ranges = pd.DataFrame([
        ["온도", f"{crop_info['temp'][0]}~{crop_info['temp'][1]} ℃", "적정" if temp_ok else "확인 필요"],
        ["습도", f"{crop_info['humidity'][0]}~{crop_info['humidity'][1]} %", "적정" if humidity_ok else "확인 필요"],
        ["조도", f"{crop_info['light'][0]}~{crop_info['light'][1]} 시간", "적정" if light_ok else "확인 필요"],
        ["토양 수분", "35~65 % (기본 참고값)", "적정" if soil_ok else "확인 필요"],
    ], columns=["항목", "참고 범위", "현재 판정"])
    st.dataframe(ranges, hide_index=True, use_container_width=True)

if overall != "양호":
    st.warning("일부 환경 값이 작물별 참고 범위를 벗어났습니다. 센서 측정값과 재배 환경을 확인하세요.")
else:
    st.success("현재 입력된 환경 값은 설정한 참고 범위 안에 있습니다.")

st.divider()

# -----------------------------
# 그래프
# -----------------------------
st.subheader("📈 최근 24시간 환경 변화")
data = st.session_state.sensor_data.copy()
selected_metric = st.selectbox(
    "그래프로 확인할 항목",
    ["온도(℃)", "습도(%)", "조도(시간)", "토양 수분(%)"],
)
fig = px.line(data, x="측정 시각", y=selected_metric, markers=True,
              title=f"최근 측정 기록 - {selected_metric}")
fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=330)
st.plotly_chart(fig, use_container_width=True)

with st.expander("센서 측정 기록 보기"):
    st.dataframe(data.sort_values("측정 시각", ascending=False), hide_index=True, use_container_width=True)
    csv = data.to_csv(index=False).encode("utf-8-sig")
    st.download_button("측정 기록 CSV 다운로드", csv, "smartfarm_sensor_data.csv", "text/csv")

# -----------------------------
# 직접 센서값 입력 및 생육 일지
# -----------------------------
st.divider()
st.subheader("🧪 센서값 직접 입력")
st.caption("센서가 아직 연결되지 않았다면 아래에 측정값을 입력해 대시보드를 갱신할 수 있습니다.")
with st.form("sensor_form"):
    c1, c2, c3, c4 = st.columns(4)
    new_temp = c1.number_input("온도 (℃)", min_value=-10.0, max_value=60.0, value=temp, step=0.1)
    new_humidity = c2.number_input("습도 (%)", min_value=0.0, max_value=100.0, value=humidity, step=0.5)
    new_light = c3.number_input("조도 (시간)", min_value=0.0, max_value=24.0, value=light, step=0.5)
    new_soil = c4.number_input("토양 수분 (%)", min_value=0.0, max_value=100.0, value=soil, step=0.5)
    submitted = st.form_submit_button("측정값 저장", type="primary")
    if submitted:
        new_row = pd.DataFrame([{
            "측정 시각": datetime.now(),
            "온도(℃)": new_temp,
            "습도(%)": new_humidity,
            "조도(시간)": new_light,
            "토양 수분(%)": new_soil,
        }])
        st.session_state.sensor_data = pd.concat(
            [st.session_state.sensor_data, new_row], ignore_index=True
        ).tail(200)
        st.success("새 측정값을 저장했습니다. 화면을 갱신해 확인하세요.")

st.subheader("📝 생육 관찰 일지")
with st.form("growth_form", clear_on_submit=True):
    log_date = st.date_input("관찰 날짜", date.today(), key="log_date")
    observation = st.text_area("관찰 내용", placeholder="예: 잎의 색이 진해짐, 꽃이 피기 시작함 등")
    memo = st.text_input("메모 (선택)")
    log_submitted = st.form_submit_button("일지 등록")
    if log_submitted:
        if observation.strip():
            st.session_state.growth_log.append({
                "날짜": log_date,
                "작물": crop,
                "생육 단계": growth_stage,
                "관찰 내용": observation.strip(),
                "메모": memo.strip(),
            })
            st.success("생육 관찰 일지를 등록했습니다.")
        else:
            st.error("관찰 내용을 입력해 주세요.")

if st.session_state.growth_log:
    logs = pd.DataFrame(st.session_state.growth_log)
    st.dataframe(logs.sort_values("날짜", ascending=False), hide_index=True, use_container_width=True)
    log_csv = logs.to_csv(index=False).encode("utf-8-sig")
    st.download_button("생육 일지 CSV 다운로드", log_csv, "smartfarm_growth_log.csv", "text/csv")
else:
    st.caption("아직 등록된 생육 관찰 일지가 없습니다.")

st.divider()
st.caption("※ 작물별 적정 환경과 재배 기간은 품종·시설·지역·생육 단계에 따라 달라질 수 있습니다. 본 앱의 수치는 시연용 참고값이며 농업 전문가의 재배 지침을 대체하지 않습니다.")
