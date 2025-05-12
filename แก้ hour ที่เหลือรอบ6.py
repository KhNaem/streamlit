
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
xls = pd.ExcelFile(sheet_url)

service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]

sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]
brush_numbers = list(range(1, 33))

def get_final_avg_rate(row):
    values = row.dropna().values
    if len(values) >= 5:
        avg = np.mean(values[:-1])
        diff = abs(values[-1] - avg)
        if diff / avg <= 0.05:
            return avg, True, row.dropna().index[-2]
    return np.mean(values), False, None

upper_rates = {n:{} for n in brush_numbers}
lower_rates = {n:{} for n in brush_numbers}
hours_map = {}

for sheet in selected_sheets:
    df_raw = xls.parse(sheet, header=None)
    try:
        hours = float(df_raw.iloc[0, 7])
        hours_map[sheet] = hours
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

# Convert to DataFrame
upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')

upper_flags, lower_flags, upper_sources, lower_sources = [], [], [], []

for _, row in upper_df.iterrows():
    val, is_stable, src = get_final_avg_rate(row)
    upper_flags.append(is_stable)
    upper_sources.append(src)
upper_df["Avg Rate (Upper)"] = upper_df.apply(get_final_avg_rate, axis=1).apply(lambda x: x[0])
upper_df["is_stable"] = upper_flags
upper_df["Stable_Sheet"] = upper_sources

for _, row in lower_df.iterrows():
    val, is_stable, src = get_final_avg_rate(row)
    lower_flags.append(is_stable)
    lower_sources.append(src)
lower_df["Avg Rate (Lower)"] = lower_df.apply(get_final_avg_rate, axis=1).apply(lambda x: x[0])
lower_df["is_stable"] = lower_flags
lower_df["Stable_Sheet"] = lower_sources

def highlight(row, kind):
    style = []
    for col in row.index:
        if col == "Stable_Sheet":
            style.append("")
        elif row["is_stable"] and col == row["Stable_Sheet"]:
            style.append("background-color: yellow")
        elif kind == "Upper" and col == "Avg Rate (Upper)":
            color = "green" if row["is_stable"] else "red"
            style.append(f"color: {color}; font-weight: bold")
        elif kind == "Lower" and col == "Avg Rate (Lower)":
            color = "green" if row["is_stable"] else "red"
            style.append(f"color: {color}; font-weight: bold")
        else:
            style.append("")
    return style

st.subheader("📋 ตาราง Avg Rate - Upper")
styled_upper = upper_df.style.apply(highlight, kind="Upper", axis=1).format("{:.6f}")
st.dataframe(styled_upper, use_container_width=True)

st.subheader("📋 ตาราง Avg Rate - Lower")
styled_lower = lower_df.style.apply(highlight, kind="Lower", axis=1).format("{:.6f}")
st.dataframe(styled_lower, use_container_width=True)

st.markdown("🟩 **สีเขียว**: ค่าคงที่ที่ใช้ในการคำนวณต่อ")

st.markdown("🟨 **สีเหลือง**: ค่าที่ถูกใช้แทน sheet ล่าสุดเพราะไม่เกิน 5% ของค่าเฉลี่ยก่อนหน้า")

st.markdown("🔴 **สีแดง**: ค่าไม่คงที่")
