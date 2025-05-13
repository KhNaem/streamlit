
# 📌 This script contains the corrected logic for handling all 32 brushes and avoiding None values
# Use pd.to_numeric(..., errors='coerce') and .dropna() to ensure all values are valid numbers
# Use reindex to guarantee brush numbers 1–32 are always included

import streamlit as st
import pandas as pd
import numpy as np
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
sheet_count = st.number_input("📌 กรอกจำนวนชีตย้อนหลังที่ต้องใช้", min_value=1, max_value=len(sheet_names), value=6)
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
    lower_df = lower_df.apply(pd.to_numeric, errors='coerce').dropna()

    upper_df = df.iloc[:, 4:6]
    upper_df.columns = ["Upper_Current", "Upper_Previous"]
    upper_df = upper_df.apply(pd.to_numeric, errors='coerce').dropna()
    upper_df["No_Upper"] = range(1, len(upper_df) + 1)

    for n in brush_numbers:
        u_row = upper_df[upper_df["No_Upper"] == n]
        if not u_row.empty:
            diff = u_row.iloc[0]["Upper_Current"] - u_row.iloc[0]["Upper_Previous"]
            rate = diff / hours if hours > 0 else np.nan
            upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else np.nan

        l_row = lower_df[lower_df["No_Lower"] == n]
        if not l_row.empty:
            diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
            rate = diff / hours if hours > 0 else np.nan
            lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else np.nan

def avg_positive(row):
    valid = row[row > 0]
    return valid.sum() / len(valid) if len(valid) > 0 else np.nan

upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')
upper_df = upper_df.reindex(range(1, 33)).fillna(0)
lower_df = lower_df.reindex(range(1, 33)).fillna(0)

upper_df["Avg Rate (Upper)"] = upper_df.apply(avg_positive, axis=1)
lower_df["Avg Rate (Lower)"] = lower_df.apply(avg_positive, axis=1)

st.subheader("📋 ตาราง Avg Rate - Upper")
st.dataframe(upper_df.style.format("{:.6f}"), use_container_width=True)

st.subheader("📋 ตาราง Avg Rate - Lower")
st.dataframe(lower_df.style.format("{:.6f}"), use_container_width=True)
