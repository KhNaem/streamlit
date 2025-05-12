import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")
st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")

sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]
brush_numbers = list(range(1, 33))
xls = pd.ExcelFile(sheet_url)

# เก็บค่า rate
upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

for sheet in selected_sheets:
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
            upper_rates[n][sheet] = rate if rate > 0 else np.nan

        l_row = lower_df[lower_df["No_Lower"] == n]
        if not l_row.empty:
            diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
            rate = diff / hours if hours > 0 else np.nan
            lower_rates[n][sheet] = rate if rate > 0 else np.nan

# คำนวณค่าเฉลี่ยและตรวจ stable
def stable_avg_rate(row):
    values = row.dropna().values
    if len(values) < 5:
        return np.nan, False, None
    avg = np.mean(values[:-1])
    diff = abs(values[-1] - avg)
    is_stable = diff / avg <= 0.05
    return (avg if is_stable else np.mean(values), is_stable, row.dropna().index[-2] if is_stable else None)

upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')

upper_results = upper_df.apply(stable_avg_rate, axis=1, result_type="expand")
lower_results = lower_df.apply(stable_avg_rate, axis=1, result_type="expand")
upper_df["Avg Rate (Upper)"], upper_df["is_stable"], upper_df["Stable_Sheet"] = upper_results[0], upper_results[1], upper_results[2]
lower_df["Avg Rate (Lower)"], lower_df["is_stable"], lower_df["Stable_Sheet"] = lower_results[0], lower_results[1], lower_results[2]

def highlight_rate(val, is_stable, source):
    if source:
        return "background-color: yellow"
    if is_stable:
        return "color: green; font-weight: bold"
    if val > 0:
        return "color: red; font-weight: bold"
    return ""

# Apply styling for upper
def style_upper(row):
    return [highlight_rate(row["Avg Rate (Upper)"], row["is_stable"], row["Stable_Sheet"])] * len(row)

# Apply styling for lower
def style_lower(row):
    return [highlight_rate(row["Avg Rate (Lower)"], row["is_stable"], row["Stable_Sheet"])] * len(row)

st.subheader("📋 ตาราง Avg Rate - Upper")
st.dataframe(upper_df.style.apply(lambda x: style_upper(x), axis=1).format("{:.6f}"), use_container_width=True)

st.subheader("📋 ตาราง Avg Rate - Lower")
st.dataframe(lower_df.style.apply(lambda x: style_lower(x), axis=1).format("{:.6f}"), use_container_width=True)

st.caption("🟩 สีเขียว = ค่าคงที่ตามเงื่อนไข | 🟨 สีเหลือง = ค่า stable ถูกนำไปใช้จริงแล้ว | 🔴 สีแดง = ค่าไม่คงที่")
