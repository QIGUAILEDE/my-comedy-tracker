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
selected_year = st.sidebar.selectbox("📅 统计年份筛选", [2026, 2025, 2024, 2023, 2022], index=0)
current_year_default = datetime.date.today().year

if st.sidebar.button("🔄 强制同步最新数据", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("已穿透缓存，正在从云端拉取最新数据...")

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

@st.cache_data(ttl=15)
def load_all_data():
    data_dict = {}
    for name, sheet_id in CATEGORY_MAP.items():
        try:
            df = conn.read(worksheet=sheet_id, ttl=0)
            if not df.empty:
                df.columns = df.columns.str.strip()
                if 'Title' in df.columns and 'Date' in df.columns:
                    df = df.dropna(subset=['Title']) 
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
                    df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year.fillna(current_year_default).astype(int)
                    df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)
                    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce').fillna(5).astype(int)
                    data_dict[name] = df
                else:
                    st.warning(f"⚠️ 警告：Google Sheet 中的【{sheet_id}】表缺少 'Title' 或 'Date' 列名，请检查第一行表头！")
                    data_dict[name] = pd.DataFrame()
            else:
                data_dict[name] = pd.DataFrame()
        except Exception as e:
            st.error(f"❌ 读取【{sheet_id}】表时发生错误: {e}")
            data_dict[name] = pd.DataFrame()
            
    try:
        df_specials = conn.read(worksheet="Standup_Specials", ttl=0)
        if not df_specials.empty:
            df_specials.columns = df_specials.columns.str.strip()
            if 'Special_Name' in df_specials.columns:
                df_specials = df_specials.dropna(subset=['Special_Name'])
                df_specials['Year'] = pd.to_numeric(df_specials['Year'], errors='coerce').fillna(current_year_default).astype(int)
                data_dict["Specials"] = df_specials
            else:
                st.warning("⚠️ 警告：【Standup_Specials】表缺少 'Special_Name' 列名，请检查表头！")
                data_dict["Specials"] = pd.DataFrame()
        else:
            data_dict["Specials"] = pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 读取【Standup_Specials】表时发生错误: {e}")
        data_dict["Specials"] = pd.DataFrame()
        
    return data_dict

all_data = load_all_data()

# ==========================================
# 3. 导航菜单
# ==========================================
menu = st.sidebar.radio("导航", ["📅 当月日程 & 流水", "📊 类别数据统计", "🎤 喜剧演艺全景", "📝 手动录入", "🤖 AI 智能解析录入"])

# ----------------- 模块 1：当月日程 & 流水 -----------------
if menu == "📅 当月日程 & 流水":
    st.write(f"### 🗓️ {selected_year} 年流动档案")
    df_list = []
    for cat_name, df in all_data.items():
        if cat_name != "Specials" and not df.empty:
            df_copy = df.copy()
            df_copy['Category'] = cat_name
            df_list.append(df_copy)
            
    if df_list:
        total_df = pd.concat(df_list, ignore_index=True)
        total_df = total_df[total_df['Year'] == selected_year]
        total_df = total_df.sort_values(by='Date', ascending=False)
        
        current_month = datetime.date.today().month
        
        if selected_year == current_year_default:
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
        st.info("尚未读取到有效的历史流水数据，请检查 Google Sheets。")

# ----------------- 模块 2：类别数据统计 -----------------
elif menu == "📊 类别数据统计":
    st.write(f"### 📈 {selected_year} 年数据深度解构")
    selected_cat = st.selectbox("选择看板分类", list(CATEGORY_MAP.keys()))
    raw_df = all_data.get(selected_cat, pd.DataFrame())
    
    df = raw_df[raw_df['Year'] == selected_year] if "Year" in raw_df.columns and not raw_df.empty else raw_df
    
    if df.empty:
        st.warning(f"该分类在 {selected_year} 年暂无数据。")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric(f"{selected_year} 累计频次", f"{len(df)} 次")
        c2.metric(f"{selected_year} 合计开销", f"¥{df['Price'].sum():,}")
        c3.metric(f"{selected_year} 平均评分", f"{df['Rating'].mean():.1f} ★")
        st.line_chart(df.copy().sort_values('Date').set_index('Date')['Price'], color="#8e8e8e")

# ----------------- 模块 3：🎤 喜剧演艺全景 -----------------
elif menu == "🎤 喜剧演艺全景":
    st.write("### 🎤 个人喜剧演艺全景")
    df_specials = all_data.get("Specials", pd.DataFrame())
    year_specials = df_specials[df_specials['Year'] == selected_year] if not df_specials.empty else pd.DataFrame()
    
    c1, c2 = st.columns(2)
    c1.metric(f"{selected_year} 年斩获演艺", f"{len(year_specials)} 个" if not year_specials.empty else "0 个")
    c2.metric("生涯累计解锁演艺", f"{len(df_specials)} 个" if not df_specials.empty else "0 个")
    
    left_col, right_col = st.columns([5, 2])
    with left_col:
        st.write(f"📋 **{selected_year} 年清单**")
        if not year_specials.empty:
            st.dataframe(year_specials[['Comedian', 'Special_Name', 'Type', 'Format', 'Note']], use_container_width=True)
            st.write("🔥 **高频捕获排行**")
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
                        existing_sp = conn.read(worksheet="Standup_Specials", ttl=0).dropna(how='all')
                    except Exception:
                        existing_sp = pd.DataFrame(columns=['Comedian', 'Special_Name', 'Year', 'Type', 'Format', 'Note'])
                    conn.update(worksheet="Standup_Specials", data=pd.concat([existing_sp, new_sp_row], ignore_index=True))
                    st.success("🎉 成就在线解锁！")
                    st.cache_data.clear()

# ----------------- 模块 4 -----------------
elif menu == "📝 手动录入":
    st.write("### 📝 记录新日常")
    with st.form("manual_form", clear_on_submit=True):
        cat_input = st.selectbox("分类", list(CATEGORY_MAP.keys()))
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("活动日期", datetime.date.today())
            title_input = st.text_input("名称")
            artist_input = st.text_input("演职人员/导演")
        with col2:
            venue_input = st.text_input("场地/剧院")
            price_input = st.number_input("花费 (元)", min_value=0, value=0)
            rating_input = st.slider("评分", 1, 5, 5)
        review_input = st.text_area("短评回味")
        
        if st.form_submit_button("归档至云端"):
            if not title_input:
                st.error("请务必填写名称。")
            else:
                sheet_name = CATEGORY_MAP[cat_input]
                new_row = pd.DataFrame([{"Date": date_input.strftime("%Y-%m-%d"), "Title": title_input, "Artist": artist_input, "Venue": venue_input, "Price": price_input, "Rating": rating_input, "Review": review_input}])
                existing_df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
                conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
                st.success("已成功写入 Google Sheets！")
                st.cache_data.clear()

# ----------------- 模块 5 -----------------
elif menu == "🤖 AI 智能解析录入":
    st.write("### 🤖 DeepSeek 智能演艺解析专家")
    DEEPSEEK_API_KEY = "sk-ae70e2901a1e45eeb84a68fc56f40552"
    raw_text = st.text_area("请粘贴你的复杂文字信息：", height=180)
    
    if st.button("🪄 开始 AI 智能解析"):
        if not raw_text.strip():
            st.error("请输入内容。")
        else:
            with st.spinner("DeepSeek 正在解析..."):
                try:
                    url = "[https://api.deepseek.com/v1/chat/completions](https://api.deepseek.com/v1/chat/completions)"
                    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                    system_prompt = f"""
                    你是一个演艺消费数据提取专家。今天日期：{datetime.date.today().strftime('%Y-%m-%d')}。
                    字段规范：
                    1. "Category": 必须是：'🎙️ 单口喜剧', '🎭 其他喜剧', '🎬 电影纪录', '🎸 Live/音乐节', '🏛️ 音乐剧/舞台剧'。
                    2. "Date": 格式 YYYY-MM-DD。
                    3. "Title": 演出名。
                    4. "Artist": 艺人/导演。
                    5. "Venue": 剧场名。
                    6. "Price": 整数。
                    7. "Rating": 1-5 整数。
                    8. "Review": 一句话评论。
                    输出纯 JSON，不要包含 Markdown 代码块标记。
                    """
                    payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}], "temperature": 0.1}
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    ai_content = response.json()['choices'][0]['message']['content'].strip()
                    
                    # 修复截断报错的元凶：改用单引号替换双引号包裹 Markdown 反引号
                    if ai_content.startswith('```'):
                        ai_content = ai_content.split('\n', 1)[1].rsplit('\n', 1)[0].strip()
                    if ai_content.startswith('json'):
                        ai_content = ai_content[4:].strip()
                        
                    st.session_state['parsed_data'] = json.loads(ai_content)
                    st.success("🎯 解析成功！")
                except Exception as e:
                    st.error(f"解析失败: {e}")
                    
    if 'parsed_data' in st.session_state:
        data = st.session_state['parsed_data']
        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            final_cat = st.selectbox("确认分类", list(CATEGORY_MAP.keys()), index=list(CATEGORY_MAP.keys()).index(data.get('Category', '🎬 电影纪录')))
            final_date = st.text_input("确认日期", value=data.get('Date', ''))
            final_title = st.text_input("确认名称", value=data.get('Title', ''))
            final_artist = st.text_input("确认演职人员", value=data.get('Artist', '未知'))
        with col2:
            final_venue = st.text_input("确认场地", value=data.get('Venue', '未知'))
            final_price = st.number_input("确认票价", value=int(data.get('Price', 0)))
            final_rating = st.slider("确认评分", 1, 5, int(data.get('Rating', 5)))
        final_review = st.text_area("确认短评", value=data.get('Review', ''))
        
        if st.button("🚀 确认为真，一键同步归库"):
            sheet_name = CATEGORY_MAP[final_cat]
            new_row = pd.DataFrame([{"Date": final_date, "Title": final_title, "Artist": final_artist, "Venue": final_venue, "Price": final_price, "Rating": final_rating, "Review": final_review}])
            existing_df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
            conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
            st.success("数据已成功录入！")
            del st.session_state['parsed_data']
            st.cache_data.clear()
