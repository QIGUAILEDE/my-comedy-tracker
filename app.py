import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import requests
import json
import calendar
import plotly.express as px

# ==========================================
# 1. 全局配置与状态初始化
# ==========================================
st.set_page_config(page_title="奇怪了的观演记录和备忘录", page_icon="📓", layout="wide")

current_date = datetime.date.today()

# 初始化日历的时间穿梭状态
if 'cal_year' not in st.session_state:
    st.session_state.cal_year = current_date.year
if 'cal_month' not in st.session_state:
    st.session_state.cal_month = current_date.month

def prev_month():
    if st.session_state.cal_month == 1:
        st.session_state.cal_month = 12
        st.session_state.cal_year -= 1
    else:
        st.session_state.cal_month -= 1

def next_month():
    if st.session_state.cal_month == 12:
        st.session_state.cal_month = 1
        st.session_state.cal_year += 1
    else:
        st.session_state.cal_month += 1

def go_today():
    st.session_state.cal_year = current_date.year
    st.session_state.cal_month = current_date.month

# ==========================================
# 2. 视觉主题与控制台
# ==========================================
st.sidebar.write("### 🎛️ 控制台")
# 🚀 新增：彻底解决手机适配的核心开关
view_mode = st.sidebar.radio("📱 视图排版 (解决手机拥挤)", ["💻 桌面大屏 (网格)", "📱 手机竖屏 (时间轴)"])
st.sidebar.write("---")

theme_mode = st.sidebar.selectbox("🌓 视觉主题", ["明亮白天 (Ins Light)", "暗黑静谧 (Ins Dark)"])
selected_year = st.sidebar.selectbox("📅 年份筛选 (统计页)", [2026, 2025, 2024, 2023, 2022], index=0)

if st.sidebar.button("🔄 同步云端数据", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("已拉取云端最新数据")

if theme_mode == "明亮白天 (Ins Light)":
    bg_color, card_bg, text_color, sub_text, border_color = "#fafafa", "#ffffff", "#262626", "#8e8e8e", "#dbdbdb"
    chart_template = "plotly_white"
else:
    bg_color, card_bg, text_color, sub_text, border_color = "#121212", "#1c1c1e", "#f5f5f5", "#767676", "#262626"
    chart_template = "plotly_dark"

# 剥离容易引发报错的劣质 CSS，保留核心美化
st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    h1 {{ color: {text_color} !important; font-weight: 700 !important; font-size: 26px !important; padding-bottom: 5px; }}
    h2, h3 {{ color: {text_color} !important; font-weight: 600 !important; font-size: 18px !important; margin-top: 10px !important; }}
    .ins-card {{ background-color: {card_bg}; border: 1px solid {border_color}; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
    .ins-tag {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background-color: {border_color}; color: {text_color}; margin-right: 6px; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; }}
    .stTabs [data-baseweb="tab"] {{ color: {sub_text}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {text_color} !important; border-bottom: 2px solid {text_color} !important; }}
    [data-testid="stExpander"] {{ border: 1px solid {border_color} !important; border-radius: 8px !important; background-color: {card_bg} !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
</style>
""", unsafe_allow_html=True)

st.title("奇怪了的观演记录和备忘录")

# ==========================================
# 3. 核心数据拉取
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

CATEGORY_MAP = {
    "🎙️ 单口喜剧": "Standup",
    "🎭 其他喜剧": "Comedy",
    "🎬 电影纪录": "Movies",
    "🎸 Live/音乐节": "Live_Music",
    "🏛️ 音乐剧/舞台剧": "Theater"
}
COLOR_MAP = {
    "🎙️ 单口喜剧": "🟣", "🎭 其他喜剧": "🟡", "🎬 电影纪录": "🔵",
    "🎸 Live/音乐节": "🔴", "🏛️ 音乐剧/舞台剧": "🟢"
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
                    df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year.fillna(current_date.year).astype(int)
                    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
                    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
                    for col in ['Artist', 'Venue', 'Review']:
                        if col in df.columns:
                            df[col] = df[col].fillna("").astype(str).replace("nan", "")
                    data_dict[name] = df
                else:
                    data_dict[name] = pd.DataFrame()
            else:
                data_dict[name] = pd.DataFrame()
        except Exception:
            data_dict[name] = pd.DataFrame()
            
    try:
        df_specials = conn.read(worksheet="Standup_Specials", ttl=0)
        if not df_specials.empty:
            df_specials.columns = df_specials.columns.str.strip()
            df_specials = df_specials.dropna(subset=['Special_Name'])
            df_specials['Year'] = pd.to_numeric(df_specials['Year'], errors='coerce').fillna(current_date.year).astype(int)
            for col in ['Comedian', 'Type', 'Format', 'Note']:
                if col in df_specials.columns:
                    df_specials[col] = df_specials[col].fillna("").astype(str).replace("nan", "")
            data_dict["Specials"] = df_specials
        else:
            data_dict["Specials"] = pd.DataFrame()
    except Exception:
        data_dict["Specials"] = pd.DataFrame()
        
    return data_dict

def update_record(old_cat, old_date, old_title, new_cat, new_date, new_title, new_artist, new_venue, new_price, new_rating, new_review):
    old_sheet = CATEGORY_MAP[old_cat]
    new_sheet = CATEGORY_MAP[new_cat]
    df_old = conn.read(worksheet=old_sheet, ttl=0)
    df_old.columns = df_old.columns.str.strip()
    df_old_dates = pd.to_datetime(df_old['Date'], errors='coerce').dt.date
    mask = (df_old_dates == old_date) & (df_old['Title'] == old_title)
    
    new_row_data = {
        "Date": new_date.strftime("%Y-%m-%d"),
        "Title": new_title,
        "Artist": new_artist,
        "Venue": new_venue,
        "Price": new_price if pd.notnull(new_price) else "",
        "Rating": new_rating if pd.notnull(new_rating) else "",
        "Review": new_review
    }
    
    if old_sheet == new_sheet:
        for k, v in new_row_data.items():
            df_old.loc[mask, k] = v
        conn.update(worksheet=old_sheet, data=df_old)
    else:
        df_old_kept = df_old[~mask]
        conn.update(worksheet=old_sheet, data=df_old_kept)
        df_new = conn.read(worksheet=new_sheet, ttl=0)
        df_new.columns = df_new.columns.str.strip()
        df_new = pd.concat([df_new, pd.DataFrame([new_row_data])], ignore_index=True)
        conn.update(worksheet=new_sheet, data=df_new)
    st.cache_data.clear()

def render_event_details_and_edit(row, unique_key):
    price_display = f"¥{int(row['Price'])}" if pd.notnull(row['Price']) else "无价格"
    rating_display = f"{'★'*int(row['Rating'])}" if pd.notnull(row['Rating']) else "未评分"
    venue_text = str(row.get('Venue', '')).strip()
    artist_text = str(row.get('Artist', '')).strip()
    review_text = str(row.get('Review', '')).strip()
    
    st.caption(f"🎭 **{row['Category']}**")
    if artist_text: st.write(f"🧑‍🎤 **演职人员:** {artist_text}")
    if venue_text: st.write(f"📍 **场地:** {venue_text}")
    st.write(f"🏷️ **{price_display}** &nbsp;|&nbsp; ⭐ **{rating_display}**")
    if review_text: st.info(f"💬 {review_text}")
    st.divider()
    
    with st.expander("✏️ 修改 / 补全信息"):
        with st.form(f"edit_form_{unique_key}"):
            f_cat = st.selectbox("分类", list(CATEGORY_MAP.keys()), index=list(CATEGORY_MAP.keys()).index(row['Category']))
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.date_input("日期", row['Date'])
                f_title = st.text_input("名称", row['Title'])
                f_artist = st.text_input("演职人员", artist_text)
            with c2:
                f_venue = st.text_input("场地", venue_text)
                f_price = st.number_input("票价 (元)", value=row.get('Price') if pd.notnull(row.get('Price')) else None)
                r_val = row.get('Rating')
                r_idx = [None, 1, 2, 3, 4, 5].index(r_val) if r_val in [1, 2, 3, 4, 5] else 0
                f_rating = st.selectbox("评分", [None, 1, 2, 3, 4, 5], index=r_idx)
            f_review = st.text_area("短评", review_text)
            if st.form_submit_button("💾 保存同步至云端", type="primary", use_container_width=True):
                update_record(row['Category'], row['Date'], row['Title'], f_cat, f_date, f_title, f_artist, f_venue, f_price, f_rating, f_review)
                st.success("数据已更新！")
                st.rerun()

all_data = load_all_data()
menu = st.sidebar.radio("菜单", ["📅 日程排期", "📊 数据统计", "🎤 单口喜剧专场记录", "📝 数据录入"])

df_list = []
for cat_name, df in all_data.items():
    if cat_name != "Specials" and not df.empty:
        df_copy = df.copy()
        df_copy['Category'] = cat_name
        df_list.append(df_copy)
        
total_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# ----------------- 模块 1：日程排期 (双端适配 + 月份穿梭) -----------------
if menu == "📅 日程排期":
    if not total_df.empty:
        # 1. 动态日历头（带月份穿梭导航）
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        with col1:
            st.button("⬅️ 上个月", on_click=prev_month, use_container_width=True)
        with col2:
            st.markdown(f"<h3 style='text-align:center; margin-top:5px;'>📅 {st.session_state.cal_year} 年 {st.session_state.cal_month} 月</h3>", unsafe_allow_html=True)
        with col3:
            st.button("下个月 ➡️", on_click=next_month, use_container_width=True)
        with col4:
            st.button("🏠 回本月", on_click=go_today, use_container_width=True)

        st.write("---")
        
        # 获取当前穿梭目标月份的数据
        month_df = total_df[(pd.to_datetime(total_df['Date']).dt.month == st.session_state.cal_month) & 
                            (pd.to_datetime(total_df['Date']).dt.year == st.session_state.cal_year)]
        
        # 💻 视图分支 1：电脑网格版
        if view_mode == "💻 桌面大屏 (网格)":
            cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
            days_of_week = ["一", "二", "三", "四", "五", "六", "日"]
            
            cols = st.columns(7)
            for i, day in enumerate(days_of_week):
                cols[i].markdown(f"<div style='text-align:center; color:{sub_text}; font-size:14px; font-weight:600;'>{day}</div>", unsafe_allow_html=True)
                
            for week in cal:
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        cols[i].write("")
                    else:
                        target_date = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
                        events_today = month_df[month_df['Date'] == target_date]
                        
                        if not events_today.empty:
                            dots = "".join([COLOR_MAP.get(row['Category'], "⚪") for _, row in events_today.iterrows()])
                            with cols[i].popover(f"{day}\n{dots}", use_container_width=True):
                                for idx, row in events_today.iterrows():
                                    with st.expander(f"✨ {row['Title']}", expanded=True):
                                        render_event_details_and_edit(row, f"cal_{idx}")
                        else:
                            cols[i].button(f"{day}", key=f"day_{target_date}", disabled=True, use_container_width=True)
        
        # 📱 视图分支 2：手机时间轴版
        else:
            if month_df.empty:
                st.info(f"{st.session_state.cal_month}月 暂无日程安排，快去添加吧！")
            else:
                # 必须将本月数据按时间先后顺序排列
                month_df_sorted = month_df.sort_values(by="Date")
                grouped = month_df_sorted.groupby('Date')
                
                for date_val, group in grouped:
                    weekday_str = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_val.weekday()]
                    # 精美的日期分隔头
                    st.markdown(f"<div style='margin-top:15px; margin-bottom:10px; color:{sub_text}; font-size:16px; font-weight:bold; border-bottom:1px solid {border_color}; padding-bottom:5px;'>📆 {date_val.day}日 ({weekday_str})</div>", unsafe_allow_html=True)
                    
                    for idx, row in group.iterrows():
                        dots = COLOR_MAP.get(row['Category'], "⚪")
                        venue_text = str(row.get('Venue', '')).strip()
                        venue_display = f" @ {venue_text}" if venue_text else ""
                        # 直接把展开面板当成列表卡片用，体验拉满
                        with st.expander(f"{dots} **{row['Title']}**{venue_display}"):
                            render_event_details_and_edit(row, f"mob_cal_{idx}")

        st.write("---")
        
        # 3. 智能推流模块
        left_col, right_col = st.columns(2)
        with left_col:
            st.write("### 🔜 即将出发")
            upcoming_df = total_df[total_df['Date'] >= current_date].sort_values(by='Date').head(5)
            if not upcoming_df.empty:
                for idx, row in upcoming_df.iterrows():
                    venue_text = str(row.get('Venue', '')).strip()
                    venue_display = f" @ {venue_text}" if venue_text else ""
                    with st.expander(f"📌 {row['Date']} | **{row['Title']}**{venue_display}"):
                        render_event_details_and_edit(row, f"up_{idx}")
            else:
                st.info("近期暂无新安排")
                
        with right_col:
            st.write("### ⏪ 近期回顾")
            past_df = total_df[total_df['Date'] < current_date].sort_values(by='Date', ascending=False).head(5)
            if not past_df.empty:
                for idx, row in past_df.iterrows():
                    rating_display = f" {'★'*int(row['Rating'])}" if pd.notnull(row['Rating']) else ""
                    with st.expander(f"🎞️ {row['Date']} | **{row['Title']}**{rating_display}"):
                        render_event_details_and_edit(row, f"past_{idx}")
            else:
                st.info("暂无历史记录")
    else:
        st.info("暂无数据。")

# ----------------- 模块 2：数据统计 -----------------
elif menu == "📊 数据统计":
    if not total_df.empty:
        year_df = total_df[total_df['Year'] == selected_year]
        if year_df.empty:
            st.warning(f"{selected_year} 年暂无数据。")
        else:
            c1, c2, c3 = st.columns(3)
            total_cost = year_df['Price'].sum(skipna=True)
            avg_rating = year_df['Rating'].mean(skipna=True)
            
            c1.metric("年度观演数", f"{len(year_df)} 场")
            c2.metric("总计消费", f"¥{total_cost:,.0f}" if total_cost > 0 else "¥0")
            c3.metric("平均评分", f"{avg_rating:.1f} ★" if pd.notnull(avg_rating) else "-")
            
            st.write("---")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                cat_counts = year_df['Category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                fig_pie = px.pie(cat_counts, values='Count', names='Category', title="类别分布", hole=0.6, template=chart_template)
                fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_chart2:
                year_df_charts = year_df.copy()
                year_df_charts['Month'] = pd.to_datetime(year_df_charts['Date']).dt.month
                monthly_cost = year_df_charts.groupby('Month')['Price'].sum().reset_index()
                fig_bar = px.bar(monthly_cost, x='Month', y='Price', title="月度开销趋势 (元)", template=chart_template, color_discrete_sequence=['#a3a3a3'])
                fig_bar.update_layout(xaxis=dict(tickmode='linear'), margin=dict(t=40, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_bar, use_container_width=True)
            
            st.write("### 📚 完整记录")
            st.dataframe(year_df[['Date', 'Category', 'Title', 'Artist', 'Venue', 'Price', 'Rating', 'Review']], use_container_width=True)
    else:
        st.info("暂无数据。")

# ----------------- 模块 3：单口喜剧专场记录 -----------------
elif menu == "🎤 单口喜剧专场记录":
    df_specials = all_data.get("Specials", pd.DataFrame())
    year_specials = df_specials[df_specials['Year'] == selected_year] if not df_specials.empty else pd.DataFrame()
    
    c1, c2 = st.columns(2)
    c1.metric(f"{selected_year} 年记录", f"{len(year_specials)} 场" if not year_specials.empty else "0 场")
    c2.metric("生涯总计", f"{len(df_specials)} 场" if not df_specials.empty else "0 场")
    
    st.write("---")
    if not df_specials.empty:
        comedian_counts = df_specials['Comedian'].value_counts().head(10).reset_index()
        comedian_counts.columns = ['Comedian', 'Count']
        fig_bar_h = px.bar(comedian_counts, x='Count', y='Comedian', orientation='h', title="高频演员榜 Top 10", template=chart_template)
        fig_bar_h.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=40, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar_h, use_container_width=True)
        
        st.write(f"### 📋 {selected_year} 年专场明细")
        st.dataframe(year_specials[['Comedian', 'Special_Name', 'Type', 'Format', 'Note']], use_container_width=True)
    else:
        st.info("尚未录入专场数据。")

# ----------------- 模块 4：数据录入 (合并 AI 与手动) -----------------
elif menu == "📝 数据录入":
    tab1, tab2, tab3 = st.tabs(["🤖 AI 智能解析", "✍️ 手动常规录入", "🎤 专场专属录入"])
    
    with tab1:
        st.caption("粘贴聊天记录或碎碎念，自动提炼并归档。")
        DEEPSEEK_API_KEY = "sk-ae70e2901a1e45eeb84a68fc56f40552"
        raw_text = st.text_area("输入文字：", height=120, label_visibility="collapsed", placeholder="昨天在大剧院看剧花了680，给五星。")
        
        if st.button("🪄 开始解析", use_container_width=True):
            if raw_text.strip():
                with st.spinner("解析中..."):
                    try:
                        url = "https://api.deepseek.com/v1/chat/completions"
                        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
                        system_prompt = f"""
                        提取演艺消费记录为JSON。今天日期：{current_date.strftime('%Y-%m-%d')}。
                        "Category": '🎙️ 单口喜剧', '🎭 其他喜剧', '🎬 电影纪录', '🎸 Live/音乐节', '🏛️ 音乐剧/舞台剧' 之一。
                        "Date": YYYY-MM-DD。
                        "Title": 演出名。
                        "Artist": 艺人/导演。
                        "Venue": 剧场名。
                        "Price": 整数，无则空(null)。
                        "Rating": 1-5整数，无则空(null)。
                        "Review": 短评。
                        输出纯 JSON，不含反引号。
                        """
                        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}], "temperature": 0.1}
                        response = requests.post(url, json=payload, headers=headers, timeout=30)
                        ai_content = response.json()['choices'][0]['message']['content'].strip()
                        
                        backticks = chr(96) * 3 
                        if ai_content.startswith(backticks):
                            ai_content = ai_content.split('\n', 1)[1].rsplit('\n', 1)[0].strip()
                        if ai_content.startswith("json"):
                            ai_content = ai_content[4:].strip()
                            
                        st.session_state['parsed_data'] = json.loads(ai_content)
                    except Exception as e:
                        st.error("解析失败，请检查输入或 API 状态。")
            
        if 'parsed_data' in st.session_state:
            data = st.session_state['parsed_data']
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                f_cat = st.selectbox("分类", list(CATEGORY_MAP.keys()), index=list(CATEGORY_MAP.keys()).index(data.get('Category', '🎬 电影纪录')))
                f_date = st.text_input("日期", value=data.get('Date', ''))
                f_title = st.text_input("名称", value=data.get('Title', ''))
                f_artist = st.text_input("演职人员", value=data.get('Artist', ''))
            with c2:
                f_venue = st.text_input("场地", value=data.get('Venue', ''))
                f_price = st.number_input("票价", value=data.get('Price') if pd.notnull(data.get('Price')) else None)
                rating_val = data.get('Rating')
                rating_index = [None, 1, 2, 3, 4, 5].index(rating_val) if rating_val in [1, 2, 3, 4, 5] else 0
                f_rating = st.selectbox("评分", [None, 1, 2, 3, 4, 5], index=rating_index)
            f_review = st.text_area("短评", value=data.get('Review', ''))
            
            if st.button("✔️ 确认入库", type="primary", use_container_width=True):
                sheet_name = CATEGORY_MAP[f_cat]
                new_row = pd.DataFrame([{"Date": f_date, "Title": f_title, "Artist": f_artist, "Venue": f_venue, "Price": f_price if f_price is not None else "", "Rating": f_rating if f_rating is not None else "", "Review": f_review}])
                existing_df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
                conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
                st.success("入库成功！")
                del st.session_state['parsed_data']
                st.cache_data.clear()

    with tab2:
        with st.form("manual_form", clear_on_submit=True):
            m_cat = st.selectbox("分类", list(CATEGORY_MAP.keys()))
            c1, c2 = st.columns(2)
            with c1:
                m_date = st.date_input("日期", current_date)
                m_title = st.text_input("名称")
                m_artist = st.text_input("演职人员")
            with c2:
                m_venue = st.text_input("场地")
                m_price = st.number_input("票价", value=None)
                m_rating = st.selectbox("评分", [None, 1, 2, 3, 4, 5])
            m_review = st.text_area("短评")
            
            if st.form_submit_button("✔️ 提交", type="primary", use_container_width=True):
                if m_title:
                    sheet_name = CATEGORY_MAP[m_cat]
                    new_row = pd.DataFrame([{"Date": m_date.strftime("%Y-%m-%d"), "Title": m_title, "Artist": m_artist, "Venue": m_venue, "Price": m_price if m_price is not None else "", "Rating": m_rating if m_rating is not None else "", "Review": m_review}])
                    existing_df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
                    conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
                    st.success("已记录！")
                    st.cache_data.clear()
                else:
                    st.error("名称不能为空。")

    with tab3:
        with st.form("special_form", clear_on_submit=True):
            sp_type = st.radio("类型", ["单口喜剧", "新喜剧/即兴"], horizontal=True)
            sp_format = st.selectbox("形式", ["专场", "主打秀", "双拼", "其他"])
            sp_comedian = st.text_input("演员/厂牌")
            sp_name = st.text_input("名称")
            sp_year = st.number_input("年份", min_value=2020, max_value=2030, value=current_date.year)
            sp_note = st.text_input("备注")
            
            if st.form_submit_button("✔️ 提交", type="primary", use_container_width=True):
                if sp_comedian and sp_name:
                    new_sp_row = pd.DataFrame([{"Comedian": sp_comedian, "Special_Name": sp_name, "Year": int(sp_year), "Type": sp_type, "Format": sp_format, "Note": sp_note}])
                    existing_sp = conn.read(worksheet="Standup_Specials", ttl=0).dropna(how='all')
                    conn.update(worksheet="Standup_Specials", data=pd.concat([existing_sp, new_sp_row], ignore_index=True))
                    st.success("已记录！")
                    st.cache_data.clear()
                else:
                    st.error("名称不能为空。")
