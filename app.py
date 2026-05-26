import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import requests
import json
import calendar
import plotly.express as px

# ==========================================
# 1. 全局配置与视觉主题
# ==========================================
st.set_page_config(page_title="奇怪了的观演记录和备忘录", page_icon="📓", layout="wide")

st.sidebar.write("### 🎛️ 控制台")
theme_mode = st.sidebar.selectbox("🌓 视觉主题", ["明亮白天 (Ins Light)", "暗黑静谧 (Ins Dark)"])
selected_year = st.sidebar.selectbox("📅 年份筛选", [2026, 2025, 2024, 2023, 2022], index=0)
current_date = datetime.date.today()

if st.sidebar.button("🔄 同步数据", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("已拉取云端最新数据")

if theme_mode == "明亮白天 (Ins Light)":
    bg_color, card_bg, text_color, sub_text, border_color = "#fafafa", "#ffffff", "#262626", "#8e8e8e", "#dbdbdb"
    chart_template = "plotly_white"
else:
    bg_color, card_bg, text_color, sub_text, border_color = "#121212", "#1c1c1e", "#f5f5f5", "#767676", "#262626"
    chart_template = "plotly_dark"

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    h1 {{ color: {text_color} !important; font-weight: 700 !important; font-size: 26px !important; padding-bottom: 5px; }}
    h2, h3 {{ color: {text_color} !important; font-weight: 600 !important; font-size: 18px !important; margin-top: 10px !important; }}
    .ins-card {{ background-color: {card_bg}; border: 1px solid {border_color}; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
    .ins-tag {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background-color: {border_color}; color: {text_color}; margin-right: 6px; }}
    /* 隐藏默认标签，实现极简 */
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; }}
    .stTabs [data-baseweb="tab"] {{ color: {sub_text}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {text_color} !important; border-bottom: 2px solid {text_color} !important; }}
</style>
""", unsafe_allow_html=True)

st.title("奇怪了的观演记录和备忘录")

# ==========================================
# 2. 核心数据同步
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

CATEGORY_MAP = {
    "🎙️ 单口喜剧": "Standup",
    "🎭 其他喜剧": "Comedy",
    "🎬 电影纪录": "Movies",
    "🎸 Live/音乐节": "Live_Music",
    "🏛️ 音乐剧/舞台剧": "Theater"
}

# 类别颜色映射 (用于日历和图表)
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
                    # 允许空值，不再默认填 0 或 5
                    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
                    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
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
            data_dict["Specials"] = df_specials
        else:
            data_dict["Specials"] = pd.DataFrame()
    except Exception:
        data_dict["Specials"] = pd.DataFrame()
        
    return data_dict

all_data = load_all_data()

menu = st.sidebar.radio("菜单", ["📅 当月日程", "📊 数据统计", "🎤 单口喜剧专场记录", "📝 数据录入"])

# 提取全局流水数据
df_list = []
for cat_name, df in all_data.items():
    if cat_name != "Specials" and not df.empty:
        df_copy = df.copy()
        df_copy['Category'] = cat_name
        df_list.append(df_copy)
        
total_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# ----------------- 模块 1：当月日程 -----------------
if menu == "📅 当月日程":
    if not total_df.empty:
        # 1. 动态日历模块 (根据系统当前月)
        st.write(f"### 📅 {current_date.year} 年 {current_date.month} 月 日历")
        
        # 提取当月数据
        month_df = total_df[(pd.to_datetime(total_df['Date']).dt.month == current_date.month) & 
                            (pd.to_datetime(total_df['Date']).dt.year == current_date.year)]
        
        cal = calendar.monthcalendar(current_date.year, current_date.month)
        days_of_week = ["一", "二", "三", "四", "五", "六", "日"]
        
        # 绘制表头
        cols = st.columns(7)
        for i, day in enumerate(days_of_week):
            cols[i].markdown(f"<div style='text-align:center; color:{sub_text}; font-size:14px;'>{day}</div>", unsafe_allow_html=True)
            
        # 绘制日历网格
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].write("")
                else:
                    target_date = datetime.date(current_date.year, current_date.month, day)
                    events_today = month_df[month_df['Date'] == target_date]
                    
                    if not events_today.empty:
                        # 组合当天的类别圆点颜色，深浅（数量）通过圆点个数体现
                        dots = "".join([COLOR_MAP.get(row['Category'], "⚪") for _, row in events_today.iterrows()])
                        
                        # 交互式弹窗 (点击日期查看详情)
                        with cols[i].popover(f"{day}\n{dots}", use_container_width=True):
                            for _, row in events_today.iterrows():
                                price_display = f"¥{int(row['Price'])}" if pd.notnull(row['Price']) else "无价格"
                                rating_display = f"{'★'*int(row['Rating'])}" if pd.notnull(row['Rating']) else "未评分"
                                st.markdown(f"**{row['Title']}**")
                                st.caption(f"{row['Category']} | {row['Venue']}")
                                st.write(f"🏷️ {price_display} | ⭐ {rating_display}")
                                st.divider()
                    else:
                        cols[i].button(f"{day}", key=f"day_{day}", disabled=True, use_container_width=True)
        
        st.write("---")
        
        # 2. 最新行程推送模块 (智能识别前后)
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.write("### 🔜 即将出发")
            upcoming_df = total_df[total_df['Date'] >= current_date].sort_values(by='Date').head(5)
            if not upcoming_df.empty:
                for _, row in upcoming_df.iterrows():
                    st.markdown(f"""
                    <div class="ins-card" style="border-left: 4px solid {text_color};">
                        <span style="font-size:12px; color:{sub_text};">{row['Date']}</span><br>
                        <strong>{row['Title']}</strong> <span style="font-size:12px;">@ {row['Venue']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("近期暂无新安排")
                
        with right_col:
            st.write("### ⏪ 近期回顾")
            past_df = total_df[total_df['Date'] < current_date].sort_values(by='Date', ascending=False).head(5)
            if not past_df.empty:
                for _, row in past_df.iterrows():
                    rating_display = f"<span style='color:#ffcc00;'>{'★'*int(row['Rating'])}</span>" if pd.notnull(row['Rating']) else "<span style='color:#888;'>未评分</span>"
                    st.markdown(f"""
                    <div class="ins-card">
                        <span style="font-size:12px; color:{sub_text};">{row['Date']}</span><br>
                        <strong>{row['Title']}</strong><br>
                        <span style="font-size:12px;">{rating_display}</span>
                    </div>
                    """, unsafe_allow_html=True)
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
            
            # 使用 Plotly 创建智能美观图表
            st.write("---")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # 饼图：各类型占比
                cat_counts = year_df['Category'].value_counts().reset_index()
                cat_counts.columns = ['Category', 'Count']
                fig_pie = px.pie(cat_counts, values='Count', names='Category', title="类别分布", hole=0.6, template=chart_template)
                fig_pie.update_layout(margin=dict(t=40, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col_chart2:
                # 柱状图：月份消费趋势
                year_df['Month'] = pd.to_datetime(year_df['Date']).dt.month
                monthly_cost = year_df.groupby('Month')['Price'].sum().reset_index()
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
        # 高频演员横向条形图
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
                        if ai_content.startswith('
http://googleusercontent.com/immersive_entry_chip/0
