import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import requests
import json

# ==========================================
# 1. 全局配置与 Ins 风多主题切换系统
# ==========================================
st.set_page_config(page_title="足迹 · 个人文娱看板", page_icon="📓", layout="wide")

st.sidebar.write("### 🎛️ 空间控制台")
theme_mode = st.sidebar.selectbox("🌓 视觉主题", ["明亮白天 (Ins Light)", "暗黑静谧 (Ins Dark)"])

current_year_default = datetime.date.today().year
selected_year = st.sidebar.selectbox("📅 统计年份筛选", [2026, 2025, 2024, 2023, 2022], index=0)

if st.sidebar.button("🔄 强制同步最新数据", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("已清除缓存，最新数据加载中...")

if theme_mode == "明亮白天 (Ins Light)":
    bg_color, card_bg, text_color, sub_text, border_color = "#fafafa", "#ffffff", "#262626", "#8e8e8e", "#dbdbdb"
else:
    bg_color, card_bg, text_color, sub_text, border_color = "#121212", "#1c1c1e", "#f5f5f5", "#767676", "#262626"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    h1 {{ color: {text_color} !important; font-weight: 700 !important; font-size: 28px !important; padding-bottom: 10px; }}
    h2, h3 {{ color: {text_color} !important; font-weight: 600 !important; font-size: 18px !important; }}
    .ins-card {{ background-color: {card_bg}; border: 1px solid {border_color}; padding: 18px; border-radius: 4px; margin-bottom: 12px; }}
    .ins-tag {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 3px; background-color: {border_color}; color: {text_color}; margin-right: 6px; }}
</style>
""", unsafe_allow_html=True)

st.title("📓 足迹 · 个人文娱日志")
st.caption(f"当前视窗：{selected_year} 年 | 极简主义数据看板")

# ==========================================
# 2. 核心数据同步连接
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

CATEGORY_MAP = {
    "🎙️ 单口喜剧": "Standup",
    "🎭 其他喜剧": "Comedy",
    "🎬 电影纪录": "Movies",
    "🎸 Live/音乐节": "Live_Music",
    "🏛️ 音乐剧/舞台剧": "Theater"
}

@st.cache_data(ttl=10)
def load_all_data():
    data_dict = {}
    for name, sheet_id in CATEGORY_MAP.items():
        try:
            df = conn.read(worksheet=sheet_id)
            if not df.empty and 'Date' in df.columns:
                df = df.dropna(subset=['Title'])
                df['Date'] = pd.to_datetime(df['Date']).dt.date
                df['Year'] = pd.to_datetime(df['Date']).dt.year
                df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)
                df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(5).astype(int)
            data_dict[name] = df
        except Exception:
            data_dict[name] = pd.DataFrame(columns=['Date', 'Title', 'Artist', 'Venue', 'Price', 'Rating', 'Review', 'Year'])
            
    # 新增专场数据的读取，包含 Type 和 Format 字段
    try:
        df_specials = conn.read(worksheet="Standup_Specials")
        if not df_specials.empty:
            df_specials = df_specials.dropna(subset=['Special_Name'])
            df_specials['Year'] = pd.to_numeric(df_specials['Year'], errors='coerce').fillna(current_year_default).astype(int)
        data_dict["Specials"] = df_specials
    except Exception:
        data_dict["Specials"] = pd.DataFrame(columns=['Comedian', 'Special_Name', 'Year', 'Type', 'Format', 'Note'])
        
    return data_dict

all_data = load_all_data()
menu = st.sidebar.radio("导航", ["📅 当月日程 & 流水", "📊 类别数据统计", "🎤 单口专场全景统计", "📝 手动录入", "🤖 AI 智能解析录入"])

# ----------------- 模块 1：当月日程 & 流水 -----------------
if menu == "📅 当月日程 & 流水":
    st.write(f"### 🗓️ {selected_year} 年流动档案")
    df_list = [df.assign(Category=cat) for cat, df in all_data.items() if cat != "Specials" and not df.empty]
    if df_list:
        total_df = pd.concat(df_list, ignore_index=True)
        total_df = total_df[total_df['Year'] == selected_year].sort_values(by='Date', ascending=False)
        current_month, current_year = datetime.date.today().month, datetime.date.today().year
        
        if selected_year == current_year:
            month_df = total_df[pd.to_datetime(total_df['Date']).dt.month == current_month]
            st.write(f"📊 **本月 ({current_month}月) 闪回**")
            if not month_df.empty:
                for _, row in month_df.iterrows():
                    st.markdown(f"""
                    <div class="ins-card">
                        <span class="ins-tag">{row['Category']}</span>
                        <strong style="font-size:15px; color:{text_color};">{row['Title']}</strong>
                        <span style="color:{sub_text}; font-size:13px; float:right;">{row['Date']} @ {row['Venue']}</span>
                        <div style="margin-top: 8px; font-size: 13px; color:{sub_text};">评分: <span style="color:#ffcc00;">{"★"*int(row['Rating'])}</span> | 花费: ¥{row['Price']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("本月还没有留下足迹。")
            st.write("---")
        st.write(f"### 📚 {selected_year} 年全局足迹流")
        if not total_df.empty:
            st.dataframe(total_df[['Date', 'Category', 'Title', 'Artist', 'Venue', 'Price', 'Rating', 'Review']], use_container_width=True)
        else:
            st.info(f"{selected_year} 年暂无数据记录。")
    else:
        st.info("暂无历史数据。")

# ----------------- 模块 2：类别数据统计 -----------------
elif menu == "📊 类别数据统计":
    st.write(f"### 📈 {selected_year} 年数据深度解构")
    selected_cat = st.selectbox("选择看板分类", list(CATEGORY_MAP.keys()))
    raw_df = all_data[selected_cat]
    df = raw_df[raw_df['Year'] == selected_year] if "Year" in raw_df.columns else raw_df
    
    if df.empty:
        st.warning(f"该分类在 {selected_year} 年暂无数据。")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{selected_year} 累计频次", f"{len(df)} 次")
        c2.metric(f"{selected_year} 合计开销", f"¥{df['Price'].sum():,}")
        c3.metric(f"{selected_year} 平均评分", f"{df['Rating'].mean():.1f} ★")
        st.line_chart(df.copy().sort_values('Date').set_index('Date')['Price'], color="#8e8e8e")

# ----------------- 模块 3：🎤 单口专场全景统计 -----------------
elif menu == "🎤 单口专场全景统计":
    st.write("### 🎤 个人喜剧演艺全景")
    df_specials = all_data["Specials"]
    year_specials = df_specials[df_specials['Year'] == selected_year] if not df_specials.empty else pd.DataFrame()
    
    c1, c2 = st.columns(2)
    c1.metric(f"{selected_year} 年斩获演艺", f"{len(year_specials)} 个" if not year_specials.empty else "0 个")
    c2.metric("生涯累计解锁演艺", f"{len(df_specials)} 个" if not df_specials.empty else "0 个")
    
    left_col, right_col = st.columns([5, 2])
    with left_col:
        st.write(f"📋 **{selected_year} 年清单**")
        if not year_specials.empty:
            st.dataframe(year_specials[['Comedian', 'Special_Name', 'Type', 'Format', 'Note']], use_container_width=True)
            st.write("🔥 **高频捕获排行 (包含单口/新喜剧)**")
            st.bar_chart(year_specials['Comedian'].value_counts(), color="#22c55e")
        else:
            st.info(f"{selected_year} 年还没有登记专场。")
            
    with right_col:
        st.write("➕ **快捷登记新记录**")
        with st.form("special_form", clear_on_submit=True):
            sp_type = st.radio("演艺类型", ["单口喜剧", "新喜剧/即兴"], horizontal=True)
            sp_format = st.selectbox("演出形式", ["专场", "主打秀", "双拼", "其他"])
            sp_comedian = st.text_input("演员/厂牌名字", placeholder="多演员用/隔开")
            sp_name = st.text_input("作品/专场名称")
            sp_year = st.number_input("观看年份", min_value=2020, max_value=2030, value=selected_year)
            sp_note = st.text_input("备注/标签")
            
            if st.form_submit_button("归档成就"):
                if not sp_comedian or not sp_name:
                    st.error("名字和名称不能留空。")
                else:
                    new_sp_row = pd.DataFrame([{"Comedian": sp_comedian, "Special_Name": sp_name, "Year": int(sp_year), "Type": sp_type, "Format": sp_format, "Note": sp_note}])
                    try:
                        existing_sp = conn.read(worksheet="Standup_Specials").dropna(how='all')
                    except Exception:
                        existing_sp = pd.DataFrame(columns=['Comedian', 'Special_Name', 'Year', 'Type', 'Format', 'Note'])
                    conn.update(worksheet="Standup_Specials", data=pd.concat([existing_sp, new_sp_row], ignore_index=True))
                    st.success("🎉 成就在线解锁！")
                    st.cache_data.clear()

# ----------------- 模块 4 & 5 保持不变 (缩略) -----------------
elif menu == "📝 手动录入":
    st.write("请在常规流水页进行录入...")
elif menu == "🤖 AI 智能解析录入":
    st.write("AI 智能录入模块请参考上一版本的完整实现...")
