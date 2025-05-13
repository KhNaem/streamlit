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
    rate_fixed_upper = set()
    rate_fixed_lower = set()

    for sheet in selected_sheets:
        df_raw = xls.parse(sheet, header=None)
        try:
            hours = float(df_raw.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=1, header=None)

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

    def avg_positive(row):
        valid = row[row > 0]
        return valid.sum() / len(valid) if len(valid) > 0 else np.nan

    upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
    lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')

    def get_final_avg_rate(row):
        values = row[row > 0].values
        if len(values) >= 5:
            avg = np.mean(values[:-1])
            diff = abs(values[-1] - avg)
            if diff / avg <= 0.05:
                return avg, True
        return np.mean(values), False

    avg_rate_upper = []
    avg_rate_lower = []
    for n in brush_numbers:
        val_u, is_fixed_u = get_final_avg_rate(upper_df.loc[n])
        val_l, is_fixed_l = get_final_avg_rate(lower_df.loc[n])
        avg_rate_upper.append(val_u)
        avg_rate_lower.append(val_l)
        if is_fixed_u:
            rate_fixed_upper.add(n)
        if is_fixed_l:
            rate_fixed_lower.add(n)

    upper_df["Avg Rate (Upper)"] = avg_rate_upper
    lower_df["Avg Rate (Lower)"] = avg_rate_lower

    def style_rate(val, row_idx, fixed_set):
        return 'color: green; font-weight: bold' if row_idx in fixed_set else 'color: red; font-weight: bold'

    st.subheader("📋 ตาราง Avg Rate - Upper")
    st.dataframe(
        upper_df.style.applymap(lambda val: '', subset=upper_df.columns[:-1])
        .apply(lambda row: [style_rate(v, row.name+1, rate_fixed_upper) if col == "Avg Rate (Upper)" else '' for col, v in row.items()], axis=1)
        .format("{:.6f}"),
        use_container_width=True
    )

    st.subheader("📋 ตาราง Avg Rate - Lower")
    st.dataframe(
        lower_df.style.applymap(lambda val: '', subset=lower_df.columns[:-1])
        .apply(lambda row: [style_rate(v, row.name+1, rate_fixed_lower) if col == "Avg Rate (Lower)" else '' for col, v in row.items()], axis=1)
        .format("{:.6f}"),
        use_container_width=True
    )

    st.markdown("✅ สี **เขียว** = ค่า Rate คงที่แล้ว❌ สี **แดง** = ยังไม่คงที่")

    brush_numbers = list(range(1, 33))
    fig_combined = go.Figure()
    fig_combined.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_upper, mode='lines+markers+text', name='Upper Avg Rate', line=dict(color='red'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_combined.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='deepskyblue'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_combined.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.subheader("📊 กราฟรวม Avg Rate")
    st.plotly_chart(fig_combined, use_container_width=True)

    fig_upper = go.Figure()
    fig_upper.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_upper, mode='lines+markers+text', name='Upper Avg Rate', line=dict(color='red'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_upper.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.subheader("🔺 กราฟ Avg Rate - Upper")
    st.plotly_chart(fig_upper, use_container_width=True)

    fig_lower = go.Figure()
    fig_lower.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='deepskyblue'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_lower.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.subheader("🔻 กราฟ Avg Rate - Lower")
    st.plotly_chart(fig_lower, use_container_width=True)
