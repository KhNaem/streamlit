import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

st.title("🛠️ วิเคราะห์อัตราสึกหรอและชั่วโมงที่เหลือของ Brush")

# --- เชื่อมต่อ Google Sheet ---
sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{sheet_id}")

sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]
xls = pd.ExcelFile(sheet_url)

brush_numbers = list(range(1, 33))
upper_rates, lower_rates = {n: {} for n in brush_numbers}, {n: {} for n in brush_numbers}
upper_stable_flag = {n: False for n in brush_numbers}
lower_stable_flag = {n: False for n in brush_numbers}
upper_stable_sheet = {n: "" for n in brush_numbers}
lower_stable_sheet = {n: "" for n in brush_numbers}

# --- ฟังก์ชันตรวจ rate คงที่ ---
def check_rate_stability(rates_dict):
    for n in brush_numbers:
        rates = pd.Series(rates_dict[n]).dropna()
        if len(rates) < 5:
            continue
        avg = rates.iloc[:-1].mean()
        last = rates.iloc[-1]
        if abs(last - avg) / avg <= 0.05:
            rates_dict[n] = {f"Sheet{i+1}": rates.iloc[i] for i in range(len(rates)-1)}
            rates_dict[n]["Stable"] = avg
            return True, avg, rates.index[-1]
    return False, None, None

# --- อ่านค่าจากแต่ละ Sheet ---
for sheet in selected_sheets:
    df_raw = xls.parse(sheet, header=None)
    try:
        hours = float(df_raw.iloc[0, 7])
    except:
        continue
    df = xls.parse(sheet, skiprows=2, header=None)
    df.columns = [None]*df.shape[1]

    for i in range(32):
        try:
            uc, up = df.iloc[i, 4], df.iloc[i, 5]
            lc, lp = df.iloc[i, 2], df.iloc[i, 1]
            if hours > 0:
                upper_rate = (uc - up) / hours if uc > up else np.nan
                lower_rate = (lp - lc) / hours if lp > lc else np.nan
                if upper_rate > 0:
                    upper_rates[i+1][sheet] = upper_rate
                if lower_rate > 0:
                    lower_rates[i+1][sheet] = lower_rate
        except:
            continue

# --- ตรวจว่าค่าไหน stable ---
for n in brush_numbers:
    u_stable, u_avg, u_src = check_rate_stability(upper_rates)
    l_stable, l_avg, l_src = check_rate_stability(lower_rates)
    if u_stable:
        upper_rates[n] = {**upper_rates[n], "Stable": u_avg}
        upper_stable_flag[n] = True
        upper_stable_sheet[n] = u_src
    if l_stable:
        lower_rates[n] = {**lower_rates[n], "Stable": l_avg}
        lower_stable_flag[n] = True
        lower_stable_sheet[n] = l_src

# --- แสดง DataFrame + สี ---
upper_df = pd.DataFrame.from_dict(upper_rates, orient="index")
lower_df = pd.DataFrame.from_dict(lower_rates, orient="index")

upper_df["is_stable"] = pd.Series(upper_stable_flag)
lower_df["is_stable"] = pd.Series(lower_stable_flag)
upper_df["Stable_Sheet"] = pd.Series(upper_stable_sheet)
lower_df["Stable_Sheet"] = pd.Series(lower_stable_sheet)

def highlight_row(row):
    style = []
    for col in row.index:
        if row["is_stable"]:
            if col == row["Stable_Sheet"]:
                style.append("background-color: yellow")
            elif col == "Stable":
                style.append("color: green; font-weight: bold")
            else:
                style.append("")
        else:
            if col == "Stable":
                style.append("color: red; font-weight: bold")
            else:
                style.append("")
    return style

styled_upper = upper_df.drop(columns=["is_stable", "Stable_Sheet"]).style.apply(highlight_row, axis=1).format("{:.6f}")
styled_lower = lower_df.drop(columns=["is_stable", "Stable_Sheet"]).style.apply(highlight_row, axis=1).format("{:.6f}")

st.subheader("📋 ตาราง Avg Rate - Upper")
st.dataframe(styled_upper, use_container_width=True)

st.subheader("📋 ตาราง Avg Rate - Lower")
st.dataframe(styled_lower, use_container_width=True)

st.markdown("🟨 **สีเหลือง:** คือค่า Rate ที่ใช้เป็นตัวตัดสินว่าค่า Stable นั้นคงที่แล้ว")
st.markdown("🟢 **สีเขียว:** คือค่าที่คงที่แล้วไม่ต้องเปลี่ยนอีก")
st.markdown("🔴 **สีแดง:** คือค่าที่ยังไม่คงที่")
