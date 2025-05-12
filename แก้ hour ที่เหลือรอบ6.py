import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

page = st.sidebar.radio("📂 เลือกหน้า", [
    "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ",
    "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม",
    "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)"
])

if page == "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ":
    st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")

    sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

    xls = pd.ExcelFile(sheet_url)
    sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]

    sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
    selected_sheet_names = sheet_names[:sheet_count]

    brush_numbers = list(range(1, 33))
    upper_rates, lower_rates = {n: {} for n in brush_numbers}, {n: {} for n in brush_numbers}

    for sheet in selected_sheet_names:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue

        df = xls.parse(sheet, skiprows=2, header=None)
        lower_df = df.iloc[:, 0:3]
        lower_df.columns = ["No_Lower", "Lower_Previous", "Lower_Current"]
        lower_df = lower_df.dropna().apply(pd.to_numeric, errors='coerce')

        upper_df = df.iloc[:, 4:6]
        upper_df.columns = ["Upper_Current", "Upper_Previous"]
        upper_df = upper_df.dropna().apply(pd.to_numeric, errors='coerce')
        upper_df["No_Upper"] = range(1, len(upper_df) + 1)

        for n in brush_numbers:
            u_row = upper_df[upper_df["No_Upper"] == n]
            if not u_row.empty:
                diff = u_row.iloc[0]["Upper_Current"] - u_row.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else np.nan
                upper_rates[n][f"{sheet}"] = rate if rate > 0 else np.nan

            l_row = lower_df[lower_df["No_Lower"] == n]
            if not l_row.empty:
                diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else np.nan
                lower_rates[n][f"{sheet}"] = rate if rate > 0 else np.nan

    def get_final_avg_rate(row):
        values = row.dropna().values
        if len(values) >= 5:
            avg = np.mean(values[:-1])
            diff = abs(values[-1] - avg)
            if diff / avg <= 0.05:
                return np.mean(values), True, row.dropna().index[-1]
        return np.mean(values), False, None

    upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
    lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')

    upper_avg, lower_avg = [], []
    upper_flag, lower_flag = [], []
    upper_source, lower_source = [], []

    for _, row in upper_df.iterrows():
        avg, flag, src = get_final_avg_rate(row)
        upper_avg.append(avg)
        upper_flag.append(flag)
        upper_source.append(src)

    for _, row in lower_df.iterrows():
        avg, flag, src = get_final_avg_rate(row)
        lower_avg.append(avg)
        lower_flag.append(flag)
        lower_source.append(src)

    upper_df["Avg Rate (Upper)"] = upper_avg
    upper_df["is_stable"] = upper_flag
    upper_df["Stable_Sheet"] = upper_source

    lower_df["Avg Rate (Lower)"] = lower_avg
    lower_df["is_stable"] = lower_flag
    lower_df["Stable_Sheet"] = lower_source

    def highlight_row(row):
        style = []
        for col in row.index:
            if row["is_stable"] and col == row["Stable_Sheet"]:
                style.append("background-color: yellow")
            elif col == "Avg Rate (Upper)":
                if row["is_stable"]:
                    style.append("color: green; font-weight: bold")
                else:
                    style.append("color: red; font-weight: bold")
            else:
                style.append("")
        return style

    st.subheader("📄 ตาราง Avg Rate - Upper")
    styled_upper = upper_df.drop(columns=["is_stable", "Stable_Sheet"]).style.apply(highlight_row, axis=1).format("{:.6f}")
    st.write(styled_upper)

    st.subheader("📄 ตาราง Avg Rate - Lower")
    styled_lower = lower_df.drop(columns=["is_stable", "Stable_Sheet"]).style.apply(highlight_row, axis=1).format("{:.6f}")
    st.write(styled_lower)

    st.markdown("🟩 สีเขียว = ค่าคงที่  |  🟨 สีเหลือง = ค่า Sheet ที่ทำให้ค่าคงที่")
