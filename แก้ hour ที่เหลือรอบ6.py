import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="📈 Page 3 (Rate Same as Page 1)", layout="wide")
st.title("📈 พล็อตกราฟตามเวลา (อิง Rate และ Current เดียวกับหน้าแรก)")

# เชื่อมต่อ Google Sheet
sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
xls = pd.ExcelFile(sheet_url)

sheet_count = st.number_input("📌 กรอกจำนวนชีตย้อนหลังที่ต้องใช้ (1-7)", min_value=1, max_value=7, value=6)
sheet_names = [f"Sheet{i}" for i in range(1, sheet_count + 1)]
brush_numbers = list(range(1, 33))
upper_rates, lower_rates = {n: {} for n in brush_numbers}, {n: {} for n in brush_numbers}

for sheet in sheet_names:
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
            upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else np.nan

        l_row = lower_df[lower_df["No_Lower"] == n]
        if not l_row.empty:
            diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
            rate = diff / hours if hours > 0 else np.nan
            lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else np.nan

def avg_positive(row_dict):
    values = [v for v in row_dict.values() if pd.notna(v) and v > 0]
    return sum(values) / len(values) if values else np.nan

avg_rate_upper = [avg_positive(upper_rates[n]) for n in brush_numbers]
avg_rate_lower = [avg_positive(lower_rates[n]) for n in brush_numbers]

# ใช้ current จาก sheet ล่าสุด เช่น Sheet{sheet_count}
df_current = xls.parse(f"Sheet{sheet_count}", header=None, skiprows=2)
upper_current = pd.to_numeric(df_current.iloc[0:32, 5], errors='coerce').values
lower_current = pd.to_numeric(df_current.iloc[0:32, 2], errors='coerce').values

time_hours = np.arange(0, 201, 10)

# UPPER
fig_upper = go.Figure()
for i, (start, rate) in enumerate(zip(upper_current, avg_rate_upper)):
    if pd.notna(start) and pd.notna(rate) and rate > 0:
        y = [start - rate*t for t in time_hours]
        fig_upper.add_trace(go.Scatter(x=time_hours, y=y, name=f"Upper {i+1}", mode='lines'))

fig_upper.add_shape(type="line", x0=0, x1=200, y0=35, y1=35, line=dict(color="firebrick", width=2, dash="dash"))
fig_upper.add_annotation(x=5, y=35, text="⚠️ Threshold 35 mm", showarrow=False, font=dict(color="firebrick", size=12), bgcolor="white")

fig_upper.update_layout(title="🔺 ความยาว Upper ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm",
                        xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
st.plotly_chart(fig_upper, use_container_width=True)

# LOWER
fig_lower = go.Figure()
for i, (start, rate) in enumerate(zip(lower_current, avg_rate_lower)):
    if pd.notna(start) and pd.notna(rate) and rate > 0:
        y = [start - rate*t for t in time_hours]
        fig_lower.add_trace(go.Scatter(x=time_hours, y=y, name=f"Lower {i+1}", mode='lines', line=dict(dash='dot')))

fig_lower.add_shape(type="line", x0=0, x1=200, y0=35, y1=35, line=dict(color="firebrick", width=2, dash="dash"))
fig_lower.add_annotation(x=5, y=35, text="⚠️ Threshold 35 mm", showarrow=False, font=dict(color="firebrick", size=12), bgcolor="white")

fig_lower.update_layout(title="🔻 ความยาว Lower ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm",
                        xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
st.plotly_chart(fig_lower, use_container_width=True)
