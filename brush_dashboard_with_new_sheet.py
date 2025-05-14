import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

# Setup credentials and spreadsheet access
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sheet_url = "https://docs.google.com/spreadsheets/d/1Pd6ISon7-7n7w22gPs4S3I9N7k-6uODdyiTvsfXaSqY"
sh = gc.open_by_url(sheet_url)

sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องใช้", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]

sheet_url_export = f"{sheet_url}/export?format=xlsx"
xls = pd.ExcelFile(sheet_url_export)

brush_numbers = list(range(1, 33))
upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}
rate_fixed_upper = set()
rate_fixed_lower = set()

# Step 1: Calculate rates per sheet
for sheet in selected_sheets:
    df_raw = xls.parse(sheet, header=None)
    try:
        hours = float(df_raw.iloc[0, 7])
    except:
        continue
    df = xls.parse(sheet, skiprows=2, header=None)
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

# Step 2: Check for stable (fixed) rate logic
def determine_final_rate(previous_rates, new_rate, min_required=5, threshold=0.05):
    previous_rates = [r for r in previous_rates if pd.notna(r) and r > 0]
    if len(previous_rates) >= min_required:
        avg_rate = sum(previous_rates) / len(previous_rates)
        percent_diff = abs(new_rate - avg_rate) / avg_rate
        if percent_diff <= threshold:
            return round(avg_rate, 6), True
    combined = previous_rates + [new_rate] if new_rate > 0 else previous_rates
    final_avg = sum(combined) / len(combined) if combined else 0
    return round(final_avg, 6), False

def calc_avg_with_flag(rates_dict, rate_fixed_set):
    df = pd.DataFrame.from_dict(rates_dict, orient='index').fillna(0)
    avg_col = []
    for i, row in df.iterrows():
        values = row[row > 0].tolist()
        if len(values) >= 6:
            prev = values[:-1]
            new = values[-1]
            avg, fixed = determine_final_rate(prev, new)
            avg_col.append(avg)
            if fixed:
                rate_fixed_set.add(i)
        else:
            avg_col.append(np.mean(values))
    return df, avg_col

upper_df, upper_avg = calc_avg_with_flag(upper_rates, rate_fixed_upper)
lower_df, lower_avg = calc_avg_with_flag(lower_rates, rate_fixed_lower)

upper_df["Avg Rate (Upper)"] = upper_avg
lower_df["Avg Rate (Lower)"] = lower_avg

# Step 3: Styling output
def highlight_fixed_rate_row(row, column_name, fixed_set):
    styles = []
    for col in row.index:
        if col == column_name:
            if row.name in fixed_set:
                styles.append("background-color: yellow; color: black; font-weight: bold")
            else:
                styles.append("color: red; font-weight: bold")
        else:
            styles.append("")
    return styles

st.subheader("📋 ตาราง Avg Rate - Upper")
styled_upper = upper_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Upper)", rate_fixed_upper), axis=1).format("{:.6f}")
st.write(styled_upper)

st.subheader("📋 ตาราง Avg Rate - Lower")
styled_lower = lower_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Lower)", rate_fixed_lower), axis=1).format("{:.6f}")
st.write(styled_lower)

st.markdown("🟩 **สีเขียว** = ค่าคงที่ที่นำไปใช้ในกราฟ")
st.markdown("🟨 **สีเหลือง** = ค่าที่ถูกตัดสินว่า 'คงที่' แล้ว ใช้ค่านี้ถาวรในตาราง")
st.markdown("🔴 **สีแดง** = ค่า Rate ยังไม่คงที่")