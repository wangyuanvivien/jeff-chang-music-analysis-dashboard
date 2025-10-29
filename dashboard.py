import streamlit as st
import pandas as pd
import altair as alt 
import os
import numpy as np

# --- 1. 頁面設定 (Page Config) ---
st.set_page_config(
    page_title="張信哲 (Jeff Chang) 歌詞與音樂分析",
    page_icon="🎵",
    layout="wide",
)

# --- 2. 檔案路徑設定 ---
# *** 關鍵變更：只讀取一個檔案 ***
DATA_FILE = 'Jeff_Chang_Final_Master_Dashboard_Data.csv'
AI_COLS = ['ai_theme', 'ai_sentiment', 'ai_notes']

# --- 3. 輔助函式 (Helper Functions) ---

@st.cache_data
def load_data():
    """
    載入單一的主儀表板資料檔案。
    """
    if not os.path.exists(DATA_FILE):
        st.error(f"致命錯誤：找不到儀表板主資料檔案: {DATA_FILE}")
        st.info(f"請確認您已在本地運行 'merge_ultimate_master_final.py' 並將 {DATA_FILE} 上傳至 GitHub。")
        return None
    
    try:
        df = pd.read_csv(DATA_FILE, encoding='utf-8-sig', low_memory=False)
        
        # 檢查 AI 欄位是否存在，設置狀態標記
        if all(col in df.columns for col in AI_COLS):
            # 建立一個 'has_ai_analysis' 欄位
            df['has_ai_analysis'] = df['ai_theme'].notna() & (~df['ai_theme'].isin(['SKIPPED', 'ERROR']))
            st.session_state['ai_available'] = True
        else:
            df['has_ai_analysis'] = False
            # 只有在初次運行時顯示警告
            if 'ai_available' not in st.session_state:
                st.warning("AI 分析資料欄位不存在。請確保已運行最終合併腳本並上傳了正確的檔案。")
            st.session_state['ai_available'] = False

        return df
    except Exception as e:
        st.error(f"載入 {DATA_FILE} 時發生錯誤: {e}")
        return None

@st.cache_data
def plot_categorical_chart(df, column, title, top_n=15):
    """ 繪製分類型別的長條圖 """
    if column not in df.columns or df[column].dropna().empty: return None
    data = df.dropna(subset=[column])
    
    if column == 'key_key':
        key_map = {
            0.0: 'C', 1.0: 'C#', 2.0: 'D', 3.0: 'D#', 4.0: 'E', 5.0: 'F',
            6.0: 'F#', 7.0: 'G', 8.0: 'G#', 9.0: 'A', 10.0: 'A#', 11.0: 'B'
        }
        data['key_name'] = data[column].apply(lambda x: key_map.get(x, pd.NA))
        data = data.dropna(subset=['key_name'])
        column = 'key_name'
        title = "歌曲調性 (Key)"

    chart_data = data[column].value_counts().head(top_n).reset_index()
    chart_data.columns = [column, 'count']

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(column, title=title, sort='-y'),
        y=alt.Y('count', title='歌曲數量 (Count)'),
        color=alt.Color(column, title=title, legend=None),
        tooltip=[column, 'count']
    ).properties(
        title=f"{title} 分佈 (Top {top_n})" if column != 'key_name' else f"{title} 分佈"
    ).interactive()
    return chart

@st.cache_data
def plot_histogram(df, column, title, bin_count=10):
    """ 繪製數值型別的直方圖 (Histogram) """
    if column not in df.columns or df[column].dropna().empty: return None
    data = df.dropna(subset=[column])

    chart = alt.Chart(data).mark_bar().encode(
        alt.X(column, bin=alt.Bin(maxbins=bin_count), title=title),
        alt.Y('count()', title='歌曲數量 (Count)'),
        tooltip=[alt.Tooltip(column, bin=True), 'count()']
    ).properties(
        title=f"{title} 分佈 (直方圖)"
    ).interactive()
    return chart

# --- 4. 儀表板主要應用程式 ---
def main():
    
    df = load_data()

    # --- 4a. 處理資料載入失敗 ---
    if df is None:
        st.title("張信哲 (Jeff Chang) AI 歌詞分析儀表板")
        st.error("資料載入失敗，請檢查 Streamlit 應用程式日誌。")
        return

    # --- 4b. 成功的資料載入 ---
    
    # --- 側邊欄導航 (Sidebar) ---
    st.sidebar.title("導航 (Navigation)")
    st.sidebar.markdown("從下方選擇一首歌曲以查看詳細分析。若不選擇，將顯示主儀表板。")
    
    if 'track_name' not in df.columns: df['track_name'] = 'N/A' 
    if 'album_title' not in df.columns: df['album_title'] = 'N/A'
        
    df['display_name'] = df['track_name'].fillna('N/A') + " | " + df['album_title'].fillna('N/A')
    
    # 排序邏輯：AI 分析在前，然後按名稱排序
    df_sorted_for_list = df.sort_values(
        by=['has_ai_analysis', 'display_name'],
        ascending=[False, True]
    )
    sorted_unique_names = df_sorted_for_list['display_name'].unique().tolist()
    
    song_list = ['[ 主儀表板 (General Dashboard) ]'] + sorted_unique_names
    
    selected_song = st.sidebar.selectbox(
        "選擇一首歌曲 (Select a Song)",
        options=song_list,
        index=0  
    )

    # --- 5. 頁面邏輯 ---

    if selected_song == '[ 主儀表板 (General Dashboard) ]':
        st.title("張信哲 (Jeff Chang) AI 歌詞分析儀表板 v1.4 [單一來源]")
        
        # 統計數據
        total_songs = len(df)
        songs_with_lyrics = df['lyrics_text'].notna().sum()
        songs_with_ai = (df['has_ai_analysis'] == True).sum()

        st.info(f"總歌曲數: {total_songs} | 包含歌詞: {songs_with_lyrics} 筆 | 已獲 AI 分析: {songs_with_ai} 筆")
        
        st.header("總體分析 (Overall Analysis)")
        
        col1, col2 = st.columns(2)
        
        # 只有在 AI 可用時才顯示圖表
        if st.session_state.get('ai_available', False) and songs_with_ai > 0:
            df_analyzed = df[df['has_ai_analysis'] == True]
            
            if not df_analyzed.empty:
                with col1:
                    # 圖表 1: AI 分析的情緒分佈
                    st.subheader("AI 分析的情緒分佈")
                    sentiment_counts = df_analyzed['ai_sentiment'].value_counts().reset_index()
                    sentiment_counts.columns = ['情緒 (Sentiment)', '歌曲數量 (Count)']
                    
                    chart_sentiment = alt.Chart(sentiment_counts).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta("歌曲數量 (Count)", stack=True),
                        color=alt.Color("情緒 (Sentiment)"),
                        tooltip=["情緒 (Sentiment)", "歌曲數量 (Count)"]
                    ).properties(title="AI 分析的情緒")
                    st.altair_chart(chart_sentiment, use_container_width=True)

                with col2:
                    # 圖表 2: AI 分析的主題分佈
                    st.subheader("AI 分析的主題分佈")
                    theme_counts = df_analyzed['ai_theme'].value_counts().head(10).reset_index()
                    theme_counts.columns = ['主題 (Theme)', '歌曲數量 (Count)']
                    
                    chart_theme = alt.Chart(theme_counts).mark_bar().encode(
                        x=alt.X("主題 (Theme)", sort='-y'),
                        y=alt.Y("歌曲數量 (Count)"),
                        color="主題 (Theme)",
                        tooltip=["主題 (Theme)", "歌曲數量 (Count)"]
                    ).properties(title="前 10 大 AI 分析主題")
                    st.altair_chart(chart_theme, use_container_width=True)
            else:
                st.warning("AI 分析資料已載入，但似乎不包含有效的情緒或主題資料。")
        else:
            st.warning("AI 分析資料未找到或無有效分析結果。圖表無法顯示。")
            st.write("請運行 AI 分析腳本並將資料合併到單一的 CSV 檔案中。")

        # === 音訊資料維度分析 ===
        st.divider() 
        st.header("音訊資料維度分析 (Tonal Data Dimensions)")

        st.subheader("分類型資料 (Categorical Data)")
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        with chart_col1:
            if chart_genre := plot_categorical_chart(df, 'genre_ros', '音樂流派 (Genre)', top_n=15):
                st.altair_chart(chart_genre, use_container_width=True)
        
        with chart_col2:
            if chart_scale := plot_categorical_chart(df, 'key_scale', '音樂調式 (大/小調)'):
                st.altair_chart(chart_scale, use_container_width=True)
        
        with chart_col3:
            if chart_key := plot_categorical_chart(df, 'key_key', '歌曲調性 (Key) 分佈', top_n=12):
                st.altair_chart(chart_key, use_container_width=True)

        st.subheader("數值型資料 (Numerical Data)")
        chart_col4, chart_col5 = st.columns(2)

        with chart_col4:
            if chart_party := plot_histogram(df, 'mood_party', '派對指數 (Mood: Party)'):
                st.altair_chart(chart_party, use_container_width=True)
            
        with chart_col5:
            if chart_dance := plot_histogram(df, 'danceability', '舞蹈指數 (Danceability)'):
                st.altair_chart(chart_dance, use_container_width=True)
        
    # --- 5b. 單曲分析頁面 ---
    else:
        song_data = df[df['display_name'] == selected_song].iloc[0]
        
        st.title(f"🎵 {song_data['track_name']}")
        st.subheader(f"專輯 (Album): *{song_data.get('album_title', 'N/A')}*")
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1]) 
        
        with col1:
            # 歌詞與 AI 分析
            st.header("歌詞與分析")
            
            # 顯示歌詞
            st.markdown("### 歌詞 (Lyrics)")
            if pd.notna(song_data.get('lyrics_text')):
                st.text_area("Lyrics", song_data['lyrics_text'], height=300, label_visibility="collapsed")
            else:
                st.info("此歌曲無歌詞資料。")
            
            # 顯示 AI 分析 (如果存在)
            st.markdown("### AI 綜合分析 (AI Analysis)")
            if st.session_state.get('ai_available', False) and pd.notna(song_data.get('ai_theme')) and song_data.get('ai_theme') not in ['SKIPPED', 'ERROR']:
                st.info(f"**AI 主題 (Theme):**\n{song_data['ai_theme']}")
                st.warning(f"**AI 情緒 (Sentiment):**\n{song_data['ai_sentiment']}")
                st.markdown("**AI 綜合筆記 (Notes):**")
                st.write(song_data['ai_notes'])
            else:
                st.info("此歌曲尚無 AI 分析資料。")
                
            # 顯示製作人員
            st.markdown("---")
            st.markdown("#### 製作人員 (Credits)")
            credits_cols = st.columns(2)
            credits_cols[0].markdown(f"**作詞:** {song_data.get('作詞', 'N/A')}")
            credits_cols[1].markdown(f"**作曲:** {song_data.get('作曲', 'N/A')}")
            credits_cols[0].markdown(f"**製作:** {song_data.get('製作', 'N/A')}")
            credits_cols[1].markdown(f"**編曲:** {song_data.get('編曲', 'N/A')}")

        with col2:
            # 所有其他資料欄位
            st.header("所有資料欄位 (All Data Fields)")
            manual_cols = [
                'track_name', 'album_title', 'lyrics_text', '作詞', '作曲', '製作', '編曲',
                'ai_theme', 'ai_sentiment', 'ai_notes', 'display_name', 'has_ai_analysis',
            ]
            
            other_fields = song_data.drop(labels=manual_cols, errors='ignore')
            other_fields_with_data = other_fields.dropna()
            
            if not other_fields_with_data.empty:
                st.dataframe(other_fields_with_data, use_container_width=True)
            else:
                st.info("此歌曲沒有其他可用的 (Tonal/AcousticBrainz) 資料。")

# --- 6. 執行 Main ---
if __name__ == "__main__":
    main()
