import streamlit as st
import pandas as pd
import altair as alt # 用於繪製圖表
import os
import numpy as np

# --- 1. 設定 ---
#
# *** 關鍵修改！ ***
# 我們現在使用 'Ultimate' 檔案作為基礎
# 並會 *自動合併* 'AI' 檔案 (如果它存在)
#
DATA_FILE_A = 'Jeff_Chang_Ultimate_Master_File.csv'
DATA_FILE_B = 'Jeff_Chang_AI_Lyrical_Analysis.csv'

# AI 分析欄位 (用於合併)
AI_COLS = ['track_name', 'album_title', 'ai_theme', 'ai_sentiment', 'ai_notes']

# --- 2. 載入資料 (已更新) ---
@st.cache_data  # 快取資料以提高效能
def load_data():
    """
    載入主資料檔案，並可選地合併 AI 分析檔案。
    """
    # 載入主檔案 (Ultimate Master File)
    if not os.path.exists(DATA_FILE_A):
        st.error(f"致命錯誤：找不到主資料檔案: {DATA_FILE_A}")
        st.info(f"請確認 {DATA_FILE_A} 檔案與 dashboard.py 位於同一資料夾中。")
        return None
    
    df_ultimate = pd.read_csv(DATA_FILE_A, low_memory=False)
    
    # 標準化 'track_name' 和 'album_title' 以便合併
    # (將 NaN/None/空字串 統一轉換)
    for col in ['track_name', 'album_title']:
        if col in df_ultimate.columns:
            df_ultimate[col] = df_ultimate[col].astype(str).replace(['nan', 'None', ''], np.nan)

    # 檢查 AI 分析檔案是否存在
    if os.path.exists(DATA_FILE_B):
        # AI 檔案存在，嘗試載入並合併
        try:
            df_ai = pd.read_csv(DATA_FILE_B, low_memory=False)
            
            # 檢查 AI 檔案是否包含必要的合併欄位
            if all(col in df_ai.columns for col in AI_COLS):
                
                # 準備合併金鑰 (處理空值和型別)
                for key in ['track_name', 'album_title']:
                    # 確保 df_ai 中的金鑰也被標準化
                    if key in df_ai.columns:
                         df_ai[key] = df_ai[key].astype(str).replace(['nan', 'None', ''], np.nan)
                    else:
                        st.warning(f"AI 檔案 {DATA_FILE_B} 中缺少金鑰欄位: {key}。合併可能不準確。")

                # 執行左合併，將 AI 分析添加到主檔案中
                df_merged = pd.merge(
                    df_ultimate,
                    df_ai[AI_COLS],
                    on=['track_name', 'album_title'],
                    how='left'
                )
                st.session_state['ai_available'] = True # 設定一個標記
                return df_merged
            
            else:
                # AI 檔案已損壞或欄位不符
                st.warning(f"AI 分析檔案 ({DATA_FILE_B}) 已找到，但缺少必要欄位 (例如 'ai_theme')。AI 分析將不可用。")
                st.session_state['ai_available'] = False
                return df_ultimate

        except Exception as e:
            st.error(f"載入 AI 分析檔案 ({DATA_FILE_B}) 時出錯: {e}")
            st.session_state['ai_available'] = False
            return df_ultimate
    else:
        # AI 檔案不存在
        st.info(f"AI 分析檔案 ({DATA_FILE_B}) 未上傳。AI 相關功能將被禁用。")
        st.session_state['ai_available'] = False
        return df_ultimate

# --- 3. 儀表板主要應用程式 ---

def main():
    # 設定頁面為寬螢幕模式
    st.set_page_config(layout="wide")

    # 載入資料
    df = load_data()

    # --- 3a. 處理資料載入失敗 ---
    if df is None:
        st.title("張信哲 (Jeff Chang) AI 歌詞分析儀表板")
        st.error("資料載入失敗，請檢查終端機中的錯誤訊息。")
        return # *** 這裡的 return 是在 main() 函數中，所以是合法的 ***

    # --- 3b. 成功的資料載入 ---
    
    # --- 側邊欄導航 (Sidebar) ---
    st.sidebar.title("導航 (Navigation)")
    st.sidebar.markdown("從下方選擇一首歌曲以查看詳細分析。若不選擇，將顯示主儀表板。")
    
    # 建立一個包含 "瀏覽所有歌曲" 選項的歌曲列表
    # (我們使用 .fillna 將空白名稱替換掉)
    df['display_name'] = df['track_name'].fillna('N/A') + " | " + df['album_title'].fillna('N/A')
    song_list = ['[ 主儀表板 (General Dashboard) ]'] + sorted(df['display_name'].unique())
    
    # 歌曲選擇器
    selected_song = st.sidebar.selectbox(
        "選擇一首歌曲 (Select a Song)",
        options=song_list,
        index=0  # 預設顯示主儀表板
    )

    # --- 4. 頁面邏輯 ---

    # --- 4a. 如果沒有選擇歌曲 -> 顯示主儀表板 ---
    if selected_song == '[ 主儀表板 (General Dashboard) ]':
        st.title("張信哲 (Jeff Chang) AI 歌詞分析儀表板")
        
        # 取得統計數據
        total_songs = len(df)
        songs_with_lyrics = df['lyrics_text'].notna().sum()
        songs_with_ai = 0
        
        if st.session_state.get('ai_available', False) and 'ai_theme' in df.columns:
            # 確保只計算非空、非錯誤的 AI 分析
            songs_with_ai = df['ai_theme'].notna() & (df['ai_theme'] != 'SKIPPED') & (df['ai_theme'] != 'ERROR')
            songs_with_ai = songs_with_ai.sum()

        st.info(f"已載入 {total_songs} 筆資料。 | {songs_with_lyrics} 筆包含歌詞。 | {songs_with_ai} 筆已成功獲得 AI 分析。")
        
        st.header("總體分析 (Overall Analysis)")
        
        col1, col2 = st.columns(2)
        
        # 只有在 AI 可用時才顯示圖表
        if st.session_state.get('ai_available', False) and 'ai_theme' in df.columns:
            df_analyzed = df.dropna(subset=['ai_theme', 'ai_sentiment'])
            # 過濾掉錯誤和跳過的
            df_analyzed = df_analyzed[~df_analyzed['ai_theme'].isin(['SKIPPED', 'ERROR'])]
            
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
                        x=alt.X("主題 (Theme)", sort=None),
                        y=alt.Y("歌曲數量 (Count)"),
                        color="主題 (Theme)",
                        tooltip=["主題 (Theme)", "歌曲數量 (Count)"]
                    ).properties(title="前 10 大 AI 分析主題")
                    st.altair_chart(chart_theme, use_container_width=True)
            else:
                st.warning("AI 分析資料已載入，但似乎不包含有效的情緒或主題資料。")
        else:
            st.warning("AI 分析檔案 'Jeff_Chang_AI_Lyrical_Analysis.csv' 未找到或格式不符。圖表無法顯示。")
            st.write("請運行 `analyze_lyrics_with_gemini.py` 腳本，然後重新整理此頁面。")

        # === ★★★ 這裏是您要求的新增區塊 ★★★ ===
        
        st.divider() # 加入一個分隔線
        st.header("音訊資料維度分析 (Tonal Data Dimensions)")
        st.markdown("顯示 `Ultimate_Master_File.csv` 中非稀疏 (non-sparse) 欄位的資料分佈。")

        # --- 用於繪圖的輔助函式 ---
        # (將它們移到 main 函數內部，或者保持在 main 外部並傳遞 df)
        # 為了簡潔，我們將它們保留在 @st.cache_data 狀態，並移到 main 外部
        # (註：在 Streamlit 的新模型中，將它們放在 main 內部也完全可以)

        st.subheader("分類型資料 (Categorical Data)")
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        with chart_col1:
            # 您要求的 'genre_ros'
            chart_genre = plot_categorical_chart(df, 'genre_ros', '音樂流派 (Genre)', top_n=15)
            if chart_genre:
                st.altair_chart(chart_genre, use_container_width=True)
        
        with chart_col2:
            chart_scale = plot_categorical_chart(df, 'key_scale', '音樂調式 (大/小調)')
            if chart_scale:
                st.altair_chart(chart_scale, use_container_width=True)
        
        with chart_col3:
            # 歌曲調性 (key_key)
            # (將數字轉換為調性名稱)
            df_key = df.copy()
            if 'key_key' in df_key.columns:
                key_map = {
                    0: 'C', 1: 'C#', 2: 'D', 3: 'D#', 4: 'E', 5: 'F',
                    6: 'F#', 7: 'G', 8: 'G#', 9: 'A', 10: 'A#', 11: 'B'
                }
                df_key['key_name'] = df_key['key_key'].map(key_map)
                chart_key = plot_categorical_chart(df_key, 'key_name', '歌曲調性 (Key) 分佈', top_n=12)
                if chart_key:
                    st.altair_chart(chart_key, use_container_width=True)

        st.subheader("數值型資料 (Numerical Data)")
        chart_col4, chart_col5 = st.columns(2)

        with chart_col4:
            # 您要求的 'mood_party'
            chart_party = plot_numerical_histogram(df, 'mood_party', '派對指數 (Mood: Party)')
            if chart_party:
                st.altair_chart(chart_party, use_container_width=True)
            
        with chart_col5:
            chart_dance = plot_numerical_histogram(df, 'danceability', '舞蹈指數 (Danceability)')
            if chart_dance:
                st.altair_chart(chart_dance, use_container_width=True)
        
        # (移除了 Top 20 常用詞的區塊)

    # --- 4b. 如果選擇了歌曲 -> 顯示全新的「單曲分析頁面」 ---
    else:
        # 獲取被選中歌曲的資料 (取第一筆，以防萬一有重複)
        # 我們現在使用 'display_name' 來查找，以確保唯一性
        song_data_list = df[df['display_name'] == selected_song]
        
        if song_data_list.empty:
            st.error("找不到歌曲資料。")
            return # *** 這裡的 return 是在 main() 函數中，所以是合法的 ***
            
        song_data = song_data_list.iloc[0]
        
        st.title(f"🎵 {song_data['track_name']}")
        st.subheader(f"專輯 (Album): *{song_data.get('album_title', 'N/A')}*")
        st.markdown("---")
        
        col1, col2 = st.columns([2, 1]) # 左欄 (歌詞/AI) 寬度是右欄 (資料) 的 2 倍
        
        with col1:
            # === 左欄：歌詞、製作人員、AI 分析 ===
            st.header("歌詞與分析")
            
            # 顯示歌詞
            st.markdown("### 歌詞 (Lyrics)")
            if pd.notna(song_data.get('lyrics_text')):
                st.text_area(
                    "Lyrics", 
                    song_data['lyrics_text'], 
                    height=300, 
                    label_visibility="collapsed"
                )
            else:
                st.info("此歌曲無歌詞資料。")
            
            # 顯示 AI 分析 (如果存在)
            st.markdown("### AI 綜合分析 (AI Analysis)")
            ai_available = st.session_state.get('ai_available', False)
            if ai_available and pd.notna(song_data.get('ai_theme')) and song_data.get('ai_theme') not in ['SKIPPED', 'ERROR']:
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
            # === 右欄：所有其他欄位 ===
            st.header("所有資料欄位 (All Data Fields)")
            st.markdown("顯示此歌曲在 `Ultimate_Master_File.csv` 中的所有非空欄位。")
            
            # 找出我們要手動顯示的欄位 (已在左欄顯示)
            manual_cols = [
                'track_name', 'album_title', 'lyrics_text', '作詞', '作曲', '製作', '編曲',
                'ai_theme', 'ai_sentiment', 'ai_notes', 'display_name', 'has_ai_analysis'
            ]
            
            # 獲取所有其他欄位
            other_fields = song_data.drop(labels=manual_cols, errors='ignore')
            
            # 關鍵：移除所有空值 (NaN) 欄位，這樣我們只會看到有資料的欄位
            other_fields_with_data = other_fields.dropna()
            
            if not other_fields_with_data.empty:
                # 使用 st.dataframe 將其顯示為一個漂亮的 "欄位名 | 值" 列表
                st.dataframe(other_fields_with_data, use_container_width=True)
            else:
                st.info("此歌曲沒有其他可用的 (Tonal/AcousticBrainz) 資料。")

# --- 5. 繪圖函式 (移至 main 外部，使其可被快取) ---

@st.cache_data
def plot_categorical_chart(df, column, title, top_n=15):
    """ 繪製分類型別的長條圖 """
    if column not in df.columns or df[column].dropna().empty:
        st.caption(f"欄位 '{column}' 無足夠資料可供繪圖。")
        return None
    
    data = df.dropna(subset=[column])
    
    # 針對 key_key 進行特殊處理 (將數字 0-11 轉換為音名)
    if column == 'key_key':
        key_map = {
            0: 'C', 1: 'C#', 2: 'D', 3: 'D#', 4: 'E', 5: 'F',
            6: 'F#', 7: 'G', 8: 'G#', 9: 'A', 10: 'A#', 11: 'B'
        }
        data[column] = data[column].apply(lambda x: key_map.get(x, pd.NA))
        data = data.dropna(subset=[column])

    chart_data = data[column].value_counts().head(top_n).reset_index()
    chart_data.columns = [column, 'count']

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X(column, title=title, sort='-y'),
        y=alt.Y('count', title='歌曲數量 (Count)'),
        color=alt.Color(column, title=title, legend=None),
        tooltip=[column, 'count']
    ).properties(
        title=f"{title} 分佈 (Top {top_n})"
    ).interactive()
    return chart

@st.cache_data
def plot_histogram(df, column, title, bin_count=10):
    """ 繪製數值型別的直方圖 (Histogram) """
    if column not in df.columns or df[column].dropna().empty:
        st.caption(f"欄位 '{column}' 無足夠資料可供繪圖。")
        return None
        
    data = df.dropna(subset=[column])

    chart = alt.Chart(data).mark_bar().encode(
        alt.X(column, bin=alt.Bin(maxbins=bin_count), title=title),
        alt.Y('count()', title='歌曲數量 (Count)'),
        tooltip=[alt.Tooltip(column, bin=True), 'count()']
    ).properties(
        title=f"{title} 分佈 (直方圖)"
    ).interactive()
    return chart

# --- 6. 執行 Main ---
if __name__ == "__main__":
    main()


