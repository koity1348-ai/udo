import streamlit as st
import sqlite3
import datetime
import os
import pandas as pd

# =========================
# 資料庫設定
# =========================
DB_FILE = os.path.join(os.path.dirname(__file__), "documents.db")

def get_conn():
    return sqlite3.connect(DB_FILE)

# =========================
# 初始化資料表
# =========================
def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            category TEXT,
            created_at TEXT,
            author TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT '未標記'
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_category ON documents(category)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_end_date ON documents(end_date)")
    conn.commit()
    conn.close()

# =========================
# 公告類型選項
# =========================
categories = ["公告類", "財務類", "教學類", "行政類", "其他"]

# =========================
# Streamlit 初始化
# =========================
st.set_page_config(page_title="公司內部公告系統", layout="wide")
st.title("📢 公司內部公告系統")

init_db()

if "refresh" not in st.session_state:
    st.session_state["refresh"] = False

# =========================
# 上傳公告
# =========================
st.subheader("上傳公告")
with st.expander("新增公告"):
    title_input = st.text_input("公告標題")
    author_input = st.text_input("發布者")
    category_input = st.selectbox("公告類型", categories)
    content_input = st.text_area("公告內容，每行一筆")

    # 開始時間
    start_datetime = st.datetime_input(
        "公告開始時間",
        value=datetime.datetime.now(),
        step=datetime.timedelta(minutes=1)
    )
    # 結束時間預設為開始時間 + 1 分鐘
    end_datetime = st.datetime_input(
        "公告結束時間",
        value=start_datetime + datetime.timedelta(minutes=1),
        step=datetime.timedelta(minutes=1)
    )

    upload_btn = st.button("上傳公告")

    if upload_btn:
        if not title_input.strip() or not author_input.strip() or not content_input.strip():
            st.warning("請填寫完整資料！")
        elif start_datetime >= end_datetime:
            st.warning("結束時間必須晚於開始時間！")
        else:
            lines = [line.strip() for line in content_input.split("\n") if line.strip()]
            now = datetime.datetime.now().isoformat()
            with get_conn() as conn:
                c = conn.cursor()
                for line in lines:
                    c.execute(
                        "INSERT INTO documents (title, content, category, created_at, start_date, end_date, author) VALUES (?,?,?,?,?,?,?)",
                        (title_input, line, category_input, now,
                         start_datetime.isoformat(), end_datetime.isoformat(),
                         author_input)
                    )
                conn.commit()
            st.success(f"✅ 成功上傳 {len(lines)} 筆公告！")
            st.session_state["refresh"] = not st.session_state["refresh"]

# =========================
# 清空公告
# =========================
st.subheader("清空公告")
clear_confirm = st.checkbox("我確定要清空所有公告")
if st.button("⚠️ 清空所有公告") and clear_confirm:
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM documents")
        conn.commit()
    st.warning("🗑 已清空所有公告！")
    st.session_state["refresh"] = not st.session_state["refresh"]

# =========================
# 公告瀏覽
# =========================
st.subheader("公告瀏覽")
category_selected = st.selectbox("選擇分類", categories)
page_size = 20
page_number = st.number_input("頁數", min_value=1, value=1)

now_str = datetime.datetime.now().isoformat()
offset = (page_number - 1) * page_size

# 查詢未過期公告
with get_conn() as conn:
    c = conn.cursor()
    c.execute(
        "SELECT id, title, content, created_at, start_date, end_date, author, status FROM documents "
        "WHERE category=? AND end_date>=? ORDER BY start_date ASC LIMIT ? OFFSET ?",
        (category_selected, now_str, page_size, offset)
    )
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM documents WHERE category=? AND end_date>=?", (category_selected, now_str))
    total_count = c.fetchone()[0]

total_pages = max((total_count + page_size - 1) // page_size, 1)
st.write(f"分類: **{category_selected}**  共 {total_count} 筆未過期公告，頁數 {page_number}/{total_pages}")

# 顯示未過期公告（美化 + 高對比字體 + 勾選標記）
if rows:
    df = pd.DataFrame(rows, columns=["ID","標題","內容","建立時間","開始時間","結束時間","發布者","status"])
    for idx, row in df.iterrows():
        st.markdown("---")

        # 背景顏色
        bg_color = "#D0F0FF" if row['status'] in (None, "", "未標記") else "#FFF2CC"  # 已標記重要為淡黃色
        text_color = "#003366"

        # 勾選框欄
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            read_mark = st.checkbox("已讀", key=f"read_{row['ID']}", value=("已讀" in row['status'] if row['status'] else False))
            important_mark = st.checkbox("重要", key=f"important_{row['ID']}", value=("重要" in row['status'] if row['status'] else False))

            # 更新資料庫
            new_status = []
            if read_mark:
                new_status.append("已讀")
            if important_mark:
                new_status.append("重要")
            if not new_status:
                new_status_text = "未標記"
            else:
                new_status_text = ",".join(new_status)

            with get_conn() as conn:
                c = conn.cursor()
                c.execute("UPDATE documents SET status=? WHERE id=?", (new_status_text, row['ID']))
                conn.commit()

        with col2:
            st.markdown(
                f"""
                <div style='padding:12px; margin-bottom:10px; border-radius:10px; background-color:{bg_color}; box-shadow:2px 2px 5px rgba(0,0,0,0.1)'>
                    <h4 style='margin-bottom:5px; color:{text_color}'>{row['標題']}</h4>
                    <p style='margin:0; font-size:12px; color:#555'>
                        發布者: {row['發布者']} | 時間: {row['開始時間']} ~ {row['結束時間']} | 狀態: {new_status_text}
                    </p>
                    <p style='margin-top:5px; font-size:14px; color:{text_color}'>{row['內容']}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

# 已過期公告
st.subheader("已過期公告")
with get_conn() as conn:
    c = conn.cursor()
    c.execute(
        "SELECT id, title, content, created_at, start_date, end_date, author, status FROM documents "
        "WHERE category=? AND end_date<? ORDER BY end_date ASC",
        (category_selected, now_str)
    )
    expired_rows = c.fetchall()

if expired_rows:
    for row in expired_rows:
        st.markdown("---")
        st.markdown(
            f"""
            <div style='padding:12px; margin-bottom:10px; border-radius:10px; background-color:#FFD6D6; box-shadow:1px 1px 4px rgba(0,0,0,0.1)'>
                <h4 style='margin-bottom:5px; color:#990000'>{row[1]}</h4>
                <p style='margin:0; font-size:12px; color:#555'>
                    發布者: {row[6]} | 時間: {row[4]} ~ {row[5]} | 已過期
                </p>
                <p style='margin-top:5px; font-size:14px; color:#990000'>{row[2]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("此分類沒有已過期公告。")
