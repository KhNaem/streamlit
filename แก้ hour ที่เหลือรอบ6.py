
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

# Setup credentials and spreadsheet access
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sheet_url = "https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sh = gc.open_by_url(sheet_url)

sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]

brush_numbers = list(range(1, 33))
upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}
upper_flags, lower_flags = {}, {}
stable_sheets_upper, stable_sheets_lower = {}, {}

@st.cache_data(ttl=60)
def load_xls(url):
    return pd.ExcelFile(url)

xls = load_xls(sheet_url)

def calculate_avg_and_flag(rate_dict):
    df = pd.DataFrame.from_dict(rate_dict, orient='index')
    avg_rates = []
    stable_flags = []
    stable_sheets = []
    for _, row in df.iterrows():
        values = row.dropna().values
        if len(values) >= 5:
            avg = np.mean(values[:-1])
            last = values[-1]
            diff = abs(last - avg)
            if avg > 0 and (diff / avg) <= 0.05:
                avg_rates.append(avg)
                stable_flags.append(True)
                stable_sheets.append(row.dropna().index[-2])
            else:
                avg_rates.append(np.mean(values))
                stable_flags.append(False)
                stable_sheets.append(None)
        else:
            avg_rates.append(np.mean(values) if len(values) > 0 else 0)
            stable_flags.append(False)
            stable_sheets.append(None)
    return df, avg_rates, stable_flags, stable_sheets

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
            upper_rates[n][f"{sheet}"] = rate if rate > 0 else np.nan
        l_row = lower_df[lower_df["No_Lower"] == n]
        if not l_row.empty:
            diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
            rate = diff / hours if hours > 0 else np.nan
            lower_rates[n][f"{sheet}"] = rate if rate > 0 else np.nan

# Calculate
upper_df, avg_rate_upper, upper_flags, stable_sheets_upper = calculate_avg_and_flag(upper_rates)
lower_df, avg_rate_lower, lower_flags, stable_sheets_lower = calculate_avg_and_flag(lower_rates)
upper_df["Avg Rate (Upper)"] = avg_rate_upper
lower_df["Avg Rate (Lower)"] = avg_rate_lower

st.subheader("📋 ตาราง Avg Rate - Upper")
def style_upper(val, is_stable):
    if is_stable:
        return 'color: green; font-weight: bold'
    return 'color: red; font-weight: bold' if isinstance(val, float) and val > 0 else ''

def highlight_last_sheet(row):
    style = []
    for col in row.index:
        if col == stable_sheets_upper[row.name]:
            style.append('background-color: yellow')
        else:
            style.append('')
    return style

styled_upper = upper_df.style.apply(highlight_last_sheet, axis=1)
styled_upper = styled_upper.applymap(lambda x: 'color: green; font-weight: bold' if x == True else 'color: red; font-weight: bold', subset=["Avg Rate (Upper)"])
st.dataframe(styled_upper.format("{:.6f}"), use_container_width=True)

st.subheader("📋 ตาราง Avg Rate - Lower")
def style_lower(val, is_stable):
    if is_stable:
        return 'color: green; font-weight: bold'
    return 'color: red; font-weight: bold' if isinstance(val, float) and val > 0 else ''

styled_lower = lower_df.style.applymap(lambda x: 'color: green; font-weight: bold' if isinstance(x, float) and x > 0 else 'color: red; font-weight: bold', subset=["Avg Rate (Lower)"])
st.dataframe(styled_lower.format("{:.6f}"), use_container_width=True)

# Legend
st.markdown("### 🟠 Legend")
st.markdown("- 🔴 สีแดง = ยังไม่คงที่")
st.markdown("- 🟡 สีเหลือง = ชีตล่าสุดที่ใช้ตัดสินความคงที่")
st.markdown("- 🟢 สีเขียว = ค่า Rate ที่คงที่แล้ว")
