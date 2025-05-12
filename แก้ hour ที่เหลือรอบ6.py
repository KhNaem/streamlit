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

# ------------------ PAGE 1 ------------------
if page == "📊 หน้าแสดงผล rate และ ชั่วโมงที่เหลือ":
    st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")

    sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    xls = pd.ExcelFile(sheet_url)

    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

    sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
    num_sheets = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
    selected_sheets = sheet_names[:num_sheets]

    brush_numbers = list(range(1, 33))
    upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

    for sheet in selected_sheets:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=1, header=None)
        lower_df_sheet = df.iloc[:, 0:3]
        lower_df_sheet.columns = ["No_Lower", "Lower_Previous", "Lower_Current"]
        lower_df_sheet = lower_df_sheet.dropna().apply(pd.to_numeric, errors='coerce')
        upper_df_sheet = df.iloc[:, 4:6]
        upper_df_sheet.columns = ["Upper_Current", "Upper_Previous"]
        upper_df_sheet = upper_df_sheet.dropna().apply(pd.to_numeric, errors='coerce')
        upper_df_sheet["No_Upper"] = range(1, len(upper_df_sheet) + 1)

        for n in brush_numbers:
            u_row = upper_df_sheet[upper_df_sheet["No_Upper"] == n]
            if not u_row.empty:
                diff = u_row.iloc[0]["Upper_Current"] - u_row.iloc[0]["Upper_Previous"]
                rate = diff / hours if hours > 0 else np.nan
                upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else np.nan

            l_row = lower_df_sheet[lower_df_sheet["No_Lower"] == n]
            if not l_row.empty:
                diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else np.nan
                lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else np.nan

    def calculate_avg_rate_with_threshold(df_dict, threshold=0.05, min_sheets=5):
        df = pd.DataFrame.from_dict(df_dict, orient='index')
        avg_rates, fixed_flags = [], []
        for _, row in df.iterrows():
            valid_rates = row[row > 0]
            n = len(valid_rates)
            if n >= min_sheets:
                prev_avg = valid_rates.iloc[:n-1].mean()
                latest = valid_rates.iloc[-1]
                if abs(latest - prev_avg) / prev_avg <= threshold:
                    avg_rates.append(prev_avg)
                    fixed_flags.append(True)
                else:
                    avg_rates.append(valid_rates.mean())
                    fixed_flags.append(False)
            else:
                avg_rates.append(valid_rates.mean())
                fixed_flags.append(False)
        return df, avg_rates, fixed_flags

    upper_df, upper_avg, upper_fixed = calculate_avg_rate_with_threshold(upper_rates)
    lower_df, lower_avg, lower_fixed = calculate_avg_rate_with_threshold(lower_rates)
    upper_df["Avg Rate (Upper)"] = upper_avg
    lower_df["Avg Rate (Lower)"] = lower_avg

    def style_rate(val, fixed):
        if fixed:
            return 'color: green; font-weight: bold'
        return 'color: red; font-weight: bold' if val > 0 else ''

    styled_upper = upper_df.style.format("{:.6f}")
    styled_lower = lower_df.style.format("{:.6f}")
    styled_upper = styled_upper.apply(lambda col: [style_rate(v, upper_fixed[i]) if col.name == "Avg Rate (Upper)" else '' for i, v in enumerate(col)], axis=0)
    styled_lower = styled_lower.apply(lambda col: [style_rate(v, lower_fixed[i]) if col.name == "Avg Rate (Lower)" else '' for i, v in enumerate(col)], axis=0)

    st.subheader("📋 ตาราง Avg Rate - Upper")
    st.dataframe(styled_upper, use_container_width=True)

    st.subheader("📋 ตาราง Avg Rate - Lower")
    st.dataframe(styled_lower, use_container_width=True)

    st.markdown("✅ สีเขียวหมายถึงค่า Rate คงที่ (แตกต่างจากเฉลี่ยไม่เกิน 5% จากอย่างน้อย 5 ชีต)")
