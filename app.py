import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# ==========================================
# 1. 页面基本配置与新黑色电影（Neo-noir）视觉注入
# ==========================================
st.set_page_config(page_title="夜航人·文娱看板", page_icon="🎬", layout="wide")

# 注入自定义 CSS：极暗背景、冷峻白字、霓虹高光发光效果
st.markdown("""
<style>
    /* 全局背景与字体 */
    .stApp {
        background-color: #08090c;
        color: #e2e8f0;
        font-family: 'Courier New', Courier, monospace;
    }
    /* 标题动感霓虹粉 */
    h1 {
        color: #ff007f !important;
        text-shadow: 0 0 10px #ff007f, 0 0 20px #ff007f;
        font-weight: 800;
        letter-spacing: 2px;
    }
    h2, h3 {
        color: #00f3ff !important;
        text-shadow: 0 0 5px #00f3ff;
    }
    /* 标签页与输入框样式微调 */
    .stTabs [data-baseweb="tab"] {
        color: #a0aec0;
        font-size: 16px;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #fffb00 !important;
        border-bottom-color: #fffb00 !important;
        text-shadow: 0 0 5px #fffb00;
    }
    /* 卡片式区块 */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 243, 255, 0.2);
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

st.title("🌌 夜航人 · 个人文娱可视化看板")
st.caption("同步存储至 Google Sheets | 跨端实时更新")

# ==========================================
# 2. 连接 Google Sheets 数据库
# ==========================================
# 建立连接（部署时通过 Streamlit Secrets 传入凭证）
conn = st.connection("gsheets", type=GSheetsConnection)

# 分类映射字典（页面显示名称 -> Google Sheet 工作表名）
CATEGORY_MAP = {
    "🎙️ 单口喜剧": "Standup",
    "🎭 其他喜剧": "Comedy",
    "🎬 电影纪录": "Movies",
    "🎸 Live/音乐节": "Live_Music",
    "🏛️ 音乐剧/舞台剧": "Theater"
}

# 读取所有数据的函数（带缓存防止频繁请求）
@st.cache_data(ttl=60)
def load_all_data():
    data_dict = {}
    for name, sheet_id in CATEGORY_MAP.items():
        try:
            df = conn.read(worksheet=sheet_id)
            # 确保日期列为日期格式
            if not df.empty and 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date']).dt.date
            data_dict[name] = df
        except Exception:
            # 如果是新表或为空，初始化空 DataFrame
            data_dict[name] = pd.DataFrame(columns=['Date', 'Title', 'Artist', 'Venue', 'Price', 'Rating', 'Review'])
    return data_dict

all_data = load_all_data()

# ==========================================
# 3. 核心功能模块导航
# ==========================================
menu = st.sidebar.radio("功能导航", ["📆 当月日程 & 总览", "📈 分类统计分析", "➕ 录入新足迹"])

# ----------------- 模块 1：当月日程 & 总览 -----------------
if menu == "📆 当月日程 & 总览":
    st.header("📆 本月演艺日程")
    
    # 汇总所有数据
    df_list = []
    for cat_name, df in all_data.items():
        if not df.empty:
            df_copy = df.copy()
            df_copy['Category'] = cat_name
            df_list.append(df_copy)
            
    if df_list:
        total_df = pd.concat(df_list, ignore_index=True)
        total_df = total_df.sort_values(by='Date', ascending=False)
        
        # 筛选当月数据
        current_month = datetime.date.today().month
        current_year = datetime.date.today().year
        month_df = total_df[(pd.to_datetime(total_df['Date']).dt.month == current_month) & 
                            (pd.to_datetime(total_df['Date']).dt.year == current_year)]
        
        if not month_df.empty:
            st.subheader(f"✨ {current_year}年{current_month}月 已解锁的夜生活")
            # 霓虹色小高光卡片展示本月数据
            for idx, row in month_df.iterrows():
                st.markdown(f"""
                <div class="metric-card" style="margin-bottom:10px;">
                    <span style="color:#fffb00;">【{row['Category']}】</span> 
                    <strong style="color:#ffffff; font-size:16px;">{row['Title']}</strong> 
                    <span style="color:#888;"> | {row['Date']} @ {row['Venue']}</span>
                    <br><span style="color:#00f3ff;">评分: {"★"*int(row['Rating'])}</span> 
                    <p style="margin:5px 0 0 0; font-style:italic; color:#b3b3b3;">“ {row['Review']} ”</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("本月还没有记录哦，快去『录入新足迹』吧！")
            
        st.write("---")
        st.subheader("📚 历史全记录流水")
        st.dataframe(total_df[['Date', 'Category', 'Title', 'Artist', 'Venue', 'Price', 'Rating']], use_container_width=True)
    else:
        st.info("数据库空空如也，请先添加数据。")

# ----------------- 模块 2：分类统计分析 -----------------
elif menu == "📈 分类统计分析":
    st.header("📈 演艺数据深度解构")
    selected_cat = st.selectbox("选择你要分析的板块", list(CATEGORY_MAP.keys()))
    df = all_data[selected_cat]
    
    if df.empty:
        st.warning("该分类下暂无数据。")
    else:
        # 指标总览
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("累计观演/看片数", f"{len(df)} 次")
        with col2:
            st.metric("总计花费", f"¥{df['Price'].sum():,}")
        with col3:
            st.metric("平均评分", f"{df['Rating'].mean():.1f} ★")
            
        st.write("---")
        
        # 趋势与图表 (使用 Streamlit 原生深色适配图表)
        st.subheader("📊 消费与评分走势")
        chart_data = df.copy().sort_values('Date')
        chart_data = chart_data.set_index('Date')
        
        # 花费折线图
        st.line_chart(chart_data['Price'], color="#ff007f")
        
        # 评分分布
        st.subheader("⭐ 评分分布频次")
        rating_count = df['Rating'].value_counts().sort_index()
        st.bar_chart(rating_count, color="#00f3ff")

# ----------------- 模块 3：录入新足迹 -----------------
elif menu == "➕ 录入新足迹":
    st.header("➕ 新增消费与观演记录")
    
    with st.form("add_record_form", clear_on_submit=True):
        cat_input = st.selectbox("文化消费类别", list(CATEGORY_MAP.keys()))
        
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("活动日期", datetime.date.today())
            title_input = st.text_input("演出/电影/活动名称", placeholder="例如：周奇墨单口喜剧专场")
            artist_input = st.text_input("主演/导演/艺人", placeholder="例如：周奇墨")
        with col2:
            venue_input = st.text_input("场地/影院/剧场", placeholder="例如：上海大剧院 / 线下影院")
            price_input = st.number_input("票价 (元)", min_value=0, value=0, step=10)
            rating_input = st.slider("我的评分", min_value=1, max_value=5, value=5, step=1)
            
        review_input = st.text_area("一句话短评", placeholder="写下那一刻的震撼、欢笑或感动...")
        
        submit_btn = st.form_submit_button("确认同步到云端数据库")
        
        if submit_btn:
            if not title_input:
                st.error("❌ 名称不能为空！")
            else:
                # 获取对应工作表的原数据
                sheet_name = CATEGORY_MAP[cat_input]
                
                # 构建新行
                new_row = pd.DataFrame([{
                    "Date": date_input.strftime("%Y-%m-%d"),
                    "Title": title_input,
                    "Artist": artist_input,
                    "Venue": venue_input,
                    "Price": price_input,
                    "Rating": rating_input,
                    "Review": review_input
                }])
                
                # 读取原有数据并拼接
                existing_df = conn.read(worksheet=sheet_name)
                # 清除可能读取出的全空行
                existing_df = existing_df.dropna(how='all')
                
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                
                # 写回 Google Sheets
                conn.update(worksheet=sheet_name, data=updated_df)
                
                st.balloons()
                st.success(f"🚀 成功！记录已实时同步至云端 Google Sheet 里的 [{sheet_name}] 表格！")
                st.cache_data.clear() # 清除缓存以便下次加载最新数据