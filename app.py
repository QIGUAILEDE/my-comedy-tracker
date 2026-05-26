import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime
import requests
import json
import calendar
import plotly.express as px
import re

# ==========================================
# 1. 全局配置与状态初始化
# ==========================================
st.set_page_config(page_title="奇怪了的观演记录和备忘录", page_icon="📓", layout="wide")

current_date = datetime.date.today()

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
# 2. 视觉主题与响应式 CSS 架构
# ==========================================
st.sidebar.write("### 🎛️ 控制台")
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

st.markdown(f"""
<style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, sans-serif; }}
    h1 {{ color: {text_color} !important; font-weight: 700 !important; font-size: 26px !important; padding-bottom: 5px; }}
    h2, h3 {{ color: {text_color} !important; font-weight: 600 !important; font-size: 18px !important; margin-top: 10px !important; }}
    .ins-card {{ background-color: {card_bg}; border: 1px solid {border_color}; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; }}
    .stTabs [data-baseweb="tab"] {{ color: {sub_text}; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{ color: {text_color} !important; border-bottom: 2px solid {text_color} !important; }}
    [data-testid="stExpander"] {{ border: 1px solid {border_color} !important; border-radius: 8px !important; background-color: {card_bg} !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
    
    @media (min-width: 800px) {{
        .mobile-timeline {{ display: none !important; }}
    }}
    @media (max-width: 799px) {{
        .desktop-calendar {{ display: none !important; }}
    }}
</style>
""", unsafe_allow_html=True)

st.title("奇怪了的观演记录和备忘录")

# ==========================================
# 3. 核心数据同步
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
CATEGORY_MAP = {"🎙️ 单口喜剧": "Standup", "🎭 其他喜剧": "Comedy", "🎬 电影纪录": "Movies", "🎸 Live/音乐节": "Live_Music", "🏛️ 音乐剧/舞台剧": "Theater"}
COLOR_MAP = {"🎙️ 单口喜剧": "🟣", "🎭 其他喜剧": "🟡", "🎬 电影纪录": "🔵", "🎸 Live/音乐节": "🔴", "🏛️ 音乐剧/舞台剧": "🟢"}

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
                else: data_dict[name] = pd.DataFrame()
            else: data_dict[name] = pd.DataFrame()
        except: data_dict[name] = pd.DataFrame()
            
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
        else: data_dict["Specials"] = pd.DataFrame()
    except: data_dict["Specials"] = pd.DataFrame()
    return data_dict

def update_record(old_cat, old_date, old_title, new_cat, new_date, new_title, new_artist, new_venue, new_price, new_rating, new_review):
    old_sheet, new_sheet = CATEGORY_MAP[old_cat], CATEGORY_MAP[new_cat]
    df_old = conn.read(worksheet=old_sheet, ttl=0)
    df_old.columns = df_old.columns.str.strip()
    mask = (pd.to_datetime(df_old['Date'], errors='coerce').dt.date == old_date) & (df_old['Title'] == old_title)
    new_data = {"Date": new_date.strftime("%Y-%m-%d"), "Title": new_title, "Artist": new_artist, "Venue": new_venue, "Price": new_price if pd.notnull(new_price) else "", "Rating": new_rating if pd.notnull(new_rating) else "", "Review": new_review}
    
    if old_sheet == new_sheet:
        for k, v in new_data.items(): df_old.loc[mask, k] = v
        conn.update(worksheet=old_sheet, data=df_old)
    else:
        conn.update(worksheet=old_sheet, data=df_old[~mask])
        df_new = conn.read(worksheet=new_sheet, ttl=0)
        df_new.columns = df_new.columns.str.strip()
        conn.update(worksheet=new_sheet, data=pd.concat([df_new, pd.DataFrame([new_data])], ignore_index=True))
    st.cache_data.clear()

def render_event_details_and_edit(row, unique_key):
    st.caption(f"🎭 **{row['Category']}**")
    if str(row.get('Artist', '')).strip(): st.write(f"🧑‍🎤 **演职人员:** {str(row.get('Artist', '')).strip()}")
    if str(row.get('Venue', '')).strip(): st.write(f"📍 **场地:** {str(row.get('Venue', '')).strip()}")
    p = f"¥{int(row['Price'])}" if pd.notnull(row['Price']) else "无价格"
    r = f"{'★'*int(row['Rating'])}" if pd.notnull(row['Rating']) else "未评分"
    st.write(f"🏷️ **{p}** &nbsp;|&nbsp; ⭐ **{r}**")
    if str(row.get('Review', '')).strip(): st.info(f"💬 {str(row.get('Review', '')).strip()}")
    st.divider()
    with st.expander("✏️ 修改 / 补全信息"):
        with st.form(f"ef_{unique_key}"):
            f_cat = st.selectbox("分类", list(CATEGORY_MAP.keys()), index=list(CATEGORY_MAP.keys()).index(row['Category']))
            c1, c2 = st.columns(2)
            with c1:
                f_date = st.date_input("日期", row['Date'])
                f_title = st.text_input("名称", row['Title'])
                f_artist = st.text_input("演职人员", str(row.get('Artist', '')).strip())
            with c2:
                f_venue = st.text_input("场地", str(row.get('Venue', '')).strip())
                f_price = st.number_input("票价 (元)", value=row.get('Price') if pd.notnull(row.get('Price')) else None)
                idx = [None, 1, 2, 3, 4, 5].index(row.get('Rating')) if row.get('Rating') in [1, 2, 3, 4, 5] else 0
                f_rating = st.selectbox("评分", [None, 1, 2, 3, 4, 5], index=idx)
            f_review = st.text_area("短评", str(row.get('Review', '')).strip())
            if st.form_submit_button("💾 保存同步至云端", type="primary", use_container_width=True):
                update_record(row['Category'], row['Date'], row['Title'], f_cat, f_date, f_title, f_artist, f_venue, f_price, f_rating, f_review)
                st.success("数据已更新！"); st.rerun()

all_data = load_all_data()
menu = st.sidebar.radio("菜单", ["📅 日程排期", "📊 数据统计", "🎤 单口喜剧专场记录", "📝 数据录入"])

df_list = [df.assign(Category=cat) for cat, df in all_data.items() if cat != "Specials" and not df.empty]
total_df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

# ----------------- 模块 1：日程排期 -----------------
if menu == "📅 日程排期":
    if not total_df.empty:
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        with col1: st.button("⬅️ 上个月", on_click=prev_month, use_container_width=True)
        with col2: st.markdown(f"<h3 style='text-align:center; margin-top:5px;'>📅 {st.session_state.cal_year} 年 {st.session_state.cal_month} 月</h3>", unsafe_allow_html=True)
        with col3: st.button("下个月 ➡️", on_click=next_month, use_container_width=True)
        with col4: st.button("🏠 回本月", on_click=go_today, use_container_width=True)
        st.write("---")
        
        month_df = total_df[(pd.to_datetime(total_df['Date']).dt.month == st.session_state.cal_month) & (pd.to_datetime(total_df['Date']).dt.year == st.session_state.cal_year)]
        
        # 1. 桌面专属 UI：网格日历
        st.markdown('<div class="desktop-calendar">', unsafe_allow_html=True)
        cal = calendar.monthcalendar(st.session_state.cal_year, st.session_state.cal_month)
        cols = st.columns(7)
        for i, day in enumerate(["一", "二", "三", "四", "五", "六", "日"]):
            cols[i].markdown(f"<div style='text-align:center; color:{sub_text}; font-size:14px; font-weight:600;'>{day}</div>", unsafe_allow_html=True)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: cols[i].write("")
                else:
                    target_date = datetime.date(st.session_state.cal_year, st.session_state.cal_month, day)
                    events = month_df[month_df['Date'] == target_date]
                    if not events.empty:
                        dots = "".join([COLOR_MAP.get(r['Category'], "⚪") for _, r in events.iterrows()])
                        with cols[i].popover(f"{day}\n{dots}", use_container_width=True):
                            for idx, r in events.iterrows():
                                with st.expander(f"✨ {r['Title']}", expanded=True): render_event_details_and_edit(r, f"d_{idx}")
                    else: cols[i].button(f"{day}", key=f"d_{target_date}", disabled=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 2. 手机专属 UI：垂直时间轴
        st.markdown('<div class="mobile-timeline">', unsafe_allow_html=True)
        if month_df.empty:
            st.info(f"{st.session_state.cal_month}月 暂无日程安排。")
        else:
            for date_val, group in month_df.sort_values(by="Date").groupby('Date'):
                ws = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_val.weekday()]
                st.markdown(f"<div style='margin-top:15px; margin-bottom:10px; color:{sub_text}; font-size:16px; font-weight:bold; border-bottom:1px solid {border_color}; padding-bottom:5px;'>📆 {date_val.day}日 ({ws})</div>", unsafe_allow_html=True)
                for idx, r in group.iterrows():
                    v = str(r.get('Venue', '')).strip()
                    vd = f" @ {v}" if v else ""
                    with st.expander(f"{COLOR_MAP.get(r['Category'], '⚪')} **{r['Title']}**{vd}"):
                        render_event_details_and_edit(r, f"m_{idx}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        
        left_col, right_col = st.columns(2)
        with left_col:
            st.write("### 🔜 即将出发")
            up_df = total_df[total_df['Date'] >= current_date].sort_values(by='Date').head(5)
            if not up_df.empty:
                for idx, r in up_df.iterrows():
                    v = str(r.get('Venue', '')).strip()
                    with st.expander(f"📌 {r['Date']} | **{r['Title']}**{f' @ {v}' if v else ''}"): render_event_details_and_edit(r, f"u_{idx}")
            else: st.info("近期无新安排")
        with right_col:
            st.write("### ⏪ 近期回顾")
            past_df = total_df[total_df['Date'] < current_date].sort_values(by='Date', ascending=False).head(5)
            if not past_df.empty:
                for idx, r in past_df.iterrows():
                    with st.expander(f"🎞️ {r['Date']} | **{r['Title']}**{f' ★'*int(r['Rating']) if pd.notnull(r['Rating']) else ''}"): render_event_details_and_edit(r, f"p_{idx}")
            else: st.info("暂无记录")
    else: st.info("暂无数据。")

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
    else: st.info("暂无数据。")

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
    else: st.info("尚未录入专场数据。")

# ----------------- 模块 4：数据录入 (带强力除错功能的AI解析) -----------------
elif menu == "📝 数据录入":
    t1, t2, t3 = st.tabs(["🤖 AI 智能解析", "✍️ 手动常规录入", "🎤 专场专属录入"])
    
    with t1:
        st.caption("粘贴聊天记录或碎碎念，自动提炼并归档。")
        DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
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
                        """
                        payload = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}], "temperature": 0.1}
                        
                        response = requests.post(url, json=payload, headers=headers, timeout=30)
                        
                        # ✨ 精准拦截状态码：如果是欠费、被封号等，这里会直接红色弹窗
                        if response.status_code != 200:
                            st.error(f"🔴 API 拒绝访问 (状态码 {response.status_code})：{response.text}")
                        else:
                            ai_content = response.json()['choices'][0]['message']['content'].strip()
                            
                            # ✨ 暴力提取机制：不管模型怎么说废话，只抓取 {} 里的核心 JSON
                            json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                            if json_match:
                                clean_json = json_match.group(0)
                                st.session_state['parsed_data'] = json.loads(clean_json)
                                st.rerun() # 提取成功后主动刷新，展示下方的核对表单
                            else:
                                st.error(f"🟡 AI 结构异常，未能识别出标准格式。原始回复：\n{ai_content}")
                                
                    except requests.exceptions.RequestException as e:
                        st.error(f"🌐 网络请求异常 (请检查服务器是否屏蔽了外网): {e}")
                    except json.JSONDecodeError as e:
                        st.error(f"🧩 JSON 结构转换失败: {e}")
                    except Exception as e:
                        st.error(f"❌ 发生未知错误: {e}")
            
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
                idx = [None, 1, 2, 3, 4, 5].index(data.get('Rating')) if data.get('Rating') in [1, 2, 3, 4, 5] else 0
                f_rating = st.selectbox("评分", [None, 1, 2, 3, 4, 5], index=idx)
            f_review = st.text_area("短评", value=data.get('Review', ''))
            
            if st.button("✔️ 确认入库", type="primary", use_container_width=True):
                sheet_name = CATEGORY_MAP[f_cat]
                new_row = pd.DataFrame([{"Date": f_date, "Title": f_title, "Artist": f_artist, "Venue": f_venue, "Price": f_price if f_price is not None else "", "Rating": f_rating if f_rating is not None else "", "Review": f_review}])
                existing_df = conn.read(worksheet=sheet_name, ttl=0).dropna(how='all')
                conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
                st.success("入库成功！"); del st.session_state['parsed_data']; st.cache_data.clear()

    with t2:
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
                    st.success("已记录！"); st.cache_data.clear()
                else: st.error("名称不能为空。")

    with t3:
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
                    st.success("已记录！"); st.cache_data.clear()
                else: st.error("名称不能为空。")
