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

# 在侧边栏最上方增加日夜模式切换
theme_mode = st.sidebar.selectbox("🌓 视觉主题", ["明亮白天 (Ins Light)", "暗黑静谧 (Ins Dark)"])

# 根据选择动态注入不同的 Ins 极简主义 CSS
if theme_mode == "明亮白天 (Ins Light)":
    bg_color = "#fafafa"
    card_bg = "#ffffff"
    text_color = "#262626"
    sub_text = "#8e8e8e"
    border_color = "#dbdbdb"
    accent_color = "#0095f6" # Ins经典动感蓝
else:
    bg_color = "#121212"
    card_bg = "#1c1c1e"
    text_color = "#f5f5f5"
    sub_text = "#767676"
    border_color = "#262626"
    accent_color = "#ffffff"

st.markdown(f"""
<style>
    /* 全局框架重塑：Ins 杂志风（简洁、大留白、克制） */
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    /* 标题去荧光，改用高级黑白大字 */
    h1 {{
        color: {text_color} !important;
        font-weight: 700 !important;
        letter-spacing: -1px;
        font-size: 28px !important;
        padding-bottom: 20px;
    }}
    h2, h3 {{
        color: {text_color} !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        margin-top: 20px !important;
    }}
    /* 侧边栏及组件微调 */
    .stRadio [data-testid="stMarkdownContainer"] {{
        color: {text_color};
    }}
    /* Ins 风卡片：细边框、无突兀阴影、轻量内衬 */
    .ins-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        padding: 18px;
        border-radius: 4px;
        margin-bottom: 12px;
    }}
    .ins-tag {{
        display: inline-block;
        font-size: 11px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 3px;
        background-color: {border_color};
        color: {text_color};
        margin-right: 6px;
    }}
</style>
""", unsafe_allow_html=True)

st.title("📓 足迹 · 个人文娱日志")

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

@st.cache_data(ttl=30)
def load_all_data():
    data_dict = {}
    for name, sheet_id in CATEGORY_MAP.items():
        try:
            df = conn.read(worksheet=sheet_id)
            if not df.empty and 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date']).dt.date
            data_dict[name] = df
        except Exception:
            data_dict[name] = pd.DataFrame(columns=['Date', 'Title', 'Artist', 'Venue', 'Price', 'Rating', 'Review'])
    return data_dict

all_data = load_all_data()

# ==========================================
# 3. 导航菜单
# ==========================================
menu = st.sidebar.radio("导航", ["📅 当月日程 & 流水", "📊 类别数据统计", "📝 手动录入", "🤖 AI 智能解析录入"])

# ----------------- 模块 1：当月日程 & 流水 -----------------
if menu == "📅 当月日程 & 流水":
    st.write("### 🗓️ 本月动态")
    
    df_list = []
    for cat_name, df in all_data.items():
        if not df.empty:
            df_copy = df.copy()
            df_copy['Category'] = cat_name
            df_list.append(df_copy)
            
    if df_list:
        total_df = pd.concat(df_list, ignore_index=True)
        total_df = total_df.sort_values(by='Date', ascending=False)
        
        current_month = datetime.date.today().month
        current_year = datetime.date.today().year
        month_df = total_df[(pd.to_datetime(total_df['Date']).dt.month == current_month) & 
                            (pd.to_datetime(total_df['Date']).dt.year == current_year)]
        
        if not month_df.empty:
            for idx, row in month_df.iterrows():
                st.markdown(f"""
                <div class="ins-card">
                    <span class="ins-tag">{row['Category']}</span>
                    <strong style="font-size:15px; color:{text_color};">{row['Title']}</strong>
                    <span style="color:{sub_text}; font-size:13px; float:right;">{row['Date']} @ {row['Venue']}</span>
                    <div style="margin-top: 8px; font-size: 13px; color:{sub_text};">
                        评分: <span style="color:#ffcc00;">{"★"*int(row['Rating'])}</span> | 花费: ¥{row['Price']}
                    </div>
                    <p style="margin: 8px 0 0 0; font-size:13px; color:{text_color}; line-height:1.5; border-left: 2px solid {border_color}; padding-left: 8px; font-style: italic;">
                        “ {row['Review']} ”
                    </p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("本月还没有留下足迹。")
            
        st.write("### 📚 历史全局档案")
        st.dataframe(total_df[['Date', 'Category', 'Title', 'Artist', 'Venue', 'Price', 'Rating']], use_container_width=True)
    else:
        st.info("暂无历史数据。")

# ----------------- 模块 2：类别数据统计 -----------------
elif menu == "📊 类别数据统计":
    st.write("### 📈 观演统计视窗")
    selected_cat = st.selectbox("选择看板分类", list(CATEGORY_MAP.keys()))
    df = all_data[selected_cat]
    
    if df.empty:
        st.warning("该分类下暂无数据。")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("累计记录", f"{len(df)}次")
        with col2:
            st.metric("合计开销", f"¥{df['Price'].sum():,}")
        with col3:
            st.metric("平均综合评分", f"{df['Rating'].mean():.1f} ★")
            
        st.write("---")
        chart_data = df.copy().sort_values('Date').set_index('Date')
        st.write("📋 **开支走势**")
        st.line_chart(chart_data['Price'], color="#8e8e8e")
        st.write("⭐️ **评分偏好频次**")
        st.bar_chart(df['Rating'].value_counts().sort_index(), color="#555555")

# ----------------- 模块 3：手动录入 -----------------
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
                existing_df = conn.read(worksheet=sheet_name).dropna(how='all')
                conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
                st.success("已成功写入 Google Sheets！")
                st.cache_data.clear()

# ----------------- 模块 4：🤖 AI 智能解析录入 (DeepSeek) -----------------
elif menu == "🤖 AI 智能解析录入":
    st.write("### 🤖 DeepSeek 智能演艺解析专家")
    st.caption("把微信聊天记录、购票短信、随手写的糊涂账贴在下面，AI 将自动结构化并归档。")
    
    # 填入你提供的 API Key
    DEEPSEEK_API_KEY = "sk-ae70e2901a1e45eeb84a68fc56f40552"
    
    raw_text = st.text_area(
        "请粘贴你的复杂文字信息：", 
        height=180, 
        placeholder="例如：上周六去上海大剧院看了汉密尔顿舞台剧，位置挺靠前票价花了1280，林漫威绝了！直接给5星好评！"
    )
    
    if st.button("🪄 开始 AI 智能解析"):
        if not raw_text.strip():
            st.error("请输入有效的文字内容。")
        else:
            with st.spinner("DeepSeek 正在玩命拆解文本结构..."):
                try:
                    # 调用 DeepSeek API
                    url = "https://api.deepseek.com/v1/chat/completions"
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                    }
                    
                    # 构建 Prompt，强约束输出为标准格式 JSON
                    system_prompt = f"""
                    你是一个演艺消费数据提取专家。请从用户输入的非结构化文本中，提取出文化演艺消费记录，并严格以 JSON 格式输出。
                    
                    系统时间上下文参考：今天是 {datetime.date.today().strftime('%Y-%m-%d')}，星期几：{datetime.date.today().strftime('%A')}。如果用户提及“上周六”、“昨天”等相对时间，请结合今天日期推算准确的 YYYY-MM-DD 格式。
                    
                    字段规范：
                    1. "Category": 必须是以下五种字面值之一：'🎙️ 单口喜剧', '🎭 其他喜剧', '🎬 电影纪录', '🎸 Live/音乐节', '🏛️ 音乐剧/舞台剧'。
                    2. "Date": 格式必须为 YYYY-MM-DD。若没提年份默认2026年，若完全没提到日期则填今天。
                    3. "Title": 演出、电影或活动的名字。
                    4. "Artist": 主演、导演、艺人或乐队。找不到填“未知”。
                    5. "Venue": 剧场、体育馆、Livehouse或影院名。找不到填“未知”。
                    6. "Price": 票价或开销，必须是纯数字整数。找不到填 0。
                    7. "Rating": 评分，必须是 1 到 5 之间的整数。未提及默认填 5。
                    8. "Review": 提炼或生成的简短一句话评论。
                    
                    请输出纯 JSON，不要包裹 ```json 标记，不要任何前后解释性废话。
                    """
                    
                    payload = {
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": raw_text}
                        ],
                        "temperature": 0.1
                    }
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    response_json = response.json()
                    
                    # 解析 AI 返回的内容
                    ai_content = response_json['choices'][0]['message']['content'].strip()
                    
                    # 容错处理：有时LLM还是会带反引号，清洗干净
                    if ai_content.startswith("```"):
                        ai_content = ai_content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
                    if ai_content.startswith("json"):
                        ai_content = ai_content[4:].strip()
                        
                    parsed_data = json.loads(ai_content)
                    
                    # 将解析出来的结果暂存到 Session State
                    st.session_state['parsed_data'] = parsed_data
                    st.success("🎯 解析成功！请核对以下解析结果：")
                    
                except Exception as e:
                    st.error(f"解析失败，可能 API 响应异常或文本无法结构化。错误信息: {e}")
                    
    # 如果存在已经解析好的数据，显示确认表单
    if 'parsed_data' in st.session_state:
        data = st.session_state['parsed_data']
        
        st.write("---")
        st.markdown("### 🔍 AI 结构化核对清单")
        
        # 允许用户在最终提交前进行微调
        col1, col2 = st.columns(2)
        with col1:
            final_cat = st.selectbox("确认分类", list(CATEGORY_MAP.keys()), index=list(CATEGORY_MAP.keys()).index(data.get('Category', '🎬 电影纪录')))
            final_date = st.text_input("确认日期 (YYYY-MM-DD)", value=data.get('Date', ''))
            final_title = st.text_input("确认名称", value=data.get('Title', ''))
            final_artist = st.text_input("确认演职人员/导演", value=data.get('Artist', '未知'))
        with col2:
            final_venue = st.text_input("确认场地", value=data.get('Venue', '未知'))
            final_price = st.number_input("确认票价 (元)", value=int(data.get('Price', 0)))
            final_rating = st.slider("确认评分", 1, 5, int(data.get('Rating', 5)))
        final_review = st.text_area("确认短评", value=data.get('Review', ''))
        
        if st.button("🚀 确认为真，一键同步归库"):
            sheet_name = CATEGORY_MAP[final_cat]
            new_row = pd.DataFrame([{
                "Date": final_date,
                "Title": final_title,
                "Artist": final_artist,
                "Venue": final_venue,
                "Price": final_price,
                "Rating": final_rating,
                "Review": final_review
            }])
            
            existing_df = conn.read(worksheet=sheet_name).dropna(how='all')
            conn.update(worksheet=sheet_name, data=pd.concat([existing_df, new_row], ignore_index=True))
            
            st.balloons()
            st.success(f"数据已自动录入至 Google Sheets 的 [{sheet_name}] 工作表！")
            del st.session_state['parsed_data'] # 清理暂存
            st.cache_data.clear()
