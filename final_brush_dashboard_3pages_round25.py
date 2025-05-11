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
    sheet_names = xls.sheet_names

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

    def avg_positive(row):
        valid = row[row > 0]
        return valid.sum() / len(valid) if len(valid) > 0 else np.nan

    upper_df = pd.DataFrame.from_dict(upper_rates, orient='index').fillna(0)
    lower_df = pd.DataFrame.from_dict(lower_rates, orient='index').fillna(0)
    upper_df["Avg Rate (Upper)"] = upper_df.apply(avg_positive, axis=1)
    lower_df["Avg Rate (Lower)"] = lower_df.apply(avg_positive, axis=1)

    avg_rate_upper = upper_df["Avg Rate (Upper)"].tolist()[:32]
    avg_rate_lower = lower_df["Avg Rate (Lower)"].tolist()[:32]

    if "Sheet7" in xls.sheet_names:
        df_sheet7 = xls.parse("Sheet7", header=None)
        upper_current = pd.to_numeric(df_sheet7.iloc[2:34, 5], errors='coerce').values
        lower_current = pd.to_numeric(df_sheet7.iloc[2:34, 2], errors='coerce').values
    else:
        st.error("❌ ไม่พบ Sheet7 สำหรับค่าสภาพปัจจุบัน")
        st.stop()

    def calculate_hours_safe(current, rate):
        return [(c - 35) / r if pd.notna(c) and r and r > 0 and c > 35 else 0 for c, r in zip(current, rate)]

    hour_upper = calculate_hours_safe(upper_current, avg_rate_upper)
    hour_lower = calculate_hours_safe(lower_current, avg_rate_lower)

    st.subheader("📋 ตาราง Avg Rate - Upper")
    def style_upper(val):
        return 'color: red; font-weight: bold' if isinstance(val, float) and val > 0 else ''
    st.dataframe(upper_df.style.applymap(style_upper, subset=["Avg Rate (Upper)"]).format("{:.6f}"), use_container_width=True)

    st.subheader("📋 ตาราง Avg Rate - Lower")
    def style_lower(val):
        return 'color: red; font-weight: bold' if isinstance(val, float) and val > 0 else ''
    st.dataframe(lower_df.style.applymap(style_lower, subset=["Avg Rate (Lower)"]).format("{:.6f}"), use_container_width=True)

    st.subheader("📊 กราฟรวม Avg Rate")
    fig_combined = go.Figure()
    fig_combined.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_upper, mode='lines+markers+text', name='Upper Avg Rate', line=dict(color='red'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_combined.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='darkred'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_combined.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_combined, use_container_width=True)

    st.subheader("🔺 กราฟ Avg Rate - Upper")
    fig_upper = go.Figure()
    fig_upper.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_upper, mode='lines+markers+text', name='Upper Avg Rate', line=dict(color='red'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_upper.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_upper, use_container_width=True)

    st.subheader("🔻 กราฟ Avg Rate - Lower")
    fig_lower = go.Figure()
    fig_lower.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='darkred'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_lower.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_lower, use_container_width=True)

    st.subheader("⏳ ชั่วโมงที่เหลือก่อนถึง 35mm (Remaining Life Estimate)")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

    color_upper = ['black' if h < 500 else 'red' for h in hour_upper]
    bars1 = ax1.bar(brush_numbers, hour_upper, color=color_upper)
    ax1.set_title("Remaining Hours - Upper")
    ax1.set_ylabel("Hours")
    ax1.set_xticks(brush_numbers)
    for bar, val in zip(bars1, hour_upper):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

    color_lower = ['black' if h < 500 else 'darkred' for h in hour_lower]
    bars2 = ax2.bar(brush_numbers, hour_lower, color=color_lower)
    ax2.set_title("Remaining Hours - Lower")
    ax2.set_ylabel("Hours")
    ax2.set_xticks(brush_numbers)
    for bar, val in zip(bars2, hour_lower):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

    plt.tight_layout()
    st.pyplot(fig)

# ------------------ PAGE 2 ------------------
elif page == "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม":
        st.title("📝 กรอกข้อมูลแปรงถ่าน + ชั่วโมง")
        service_account_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        ws = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ").worksheet("Sheet8")

        hours = st.number_input("⏱️ ชั่วโมง", min_value=0.0, step=0.1)
        st.title("แปลงถ่านส่วน UPPER")
        upper = [st.number_input(f"แปลงถ่านที่ {i+1}", key=f"u{i}", step=0.01) for i in range(32)]
        st.title("แปลงถ่านส่วน Lower")
        lower = [st.number_input(f"แปลงถ่านที่ {i+1}", key=f"l{i}", step=0.01) for i in range(32)]

        if st.button("📤 บันทึก"):
            try:
                ws.update("H1", [[hours]])
                ws.update("C3:C34", [[v] for v in upper])
                ws.update("F3:F34", [[v] for v in lower])
                st.success("✅ บันทึกแล้ว")
            except Exception as e:
                st.error(f"❌ {e}")

# ------------------ PAGE 3 ------------------
elif page == "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)":
    st.title("📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)")

    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ")

    selected_sheet = st.selectbox("📄 เลือก Sheet ปัจจุบัน", [ws.title for ws in sheet.worksheets()])
    count = st.number_input("📌 จำนวน Sheet ที่ใช้คำนวณ Rate", min_value=1, max_value=9, value=6)

    ws = sheet.worksheet(selected_sheet)
    upper_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in ws.get("F3:F34")]
    lower_current = [float(row[0]) if row and row[0] not in ["", "-"] else 0 for row in ws.get("C3:C34")]

    xls = pd.ExcelFile("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx")
    sheets = xls.sheet_names[:count]

    brush_numbers = list(range(1, 33))
    ur, lr = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

    for s in sheets:
        df = xls.parse(s, skiprows=1, header=None).apply(pd.to_numeric, errors='coerce')
        try: h = float(xls.parse(s, header=None).iloc[0, 7])
        except: continue

        for i in brush_numbers:
            cu, pu = df.iloc[i-1, 4], df.iloc[i-1, 5]
            cl, pl = df.iloc[i-1, 1], df.iloc[i-1, 2]
            if pd.notna(cu) and pd.notna(pu) and h > 0:
                diff = cu - pu
                rate = diff / h
                if rate > 0: ur[i][s] = rate
            if pd.notna(cl) and pd.notna(pl) and h > 0:
                diff = pl - cl
                rate = diff / h
                if rate > 0: lr[i][s] = rate


    def avg_positive(rate_dict):
        valid = [v for v in rate_dict.values() if v > 0]
        return sum(valid) / len(valid) if valid else 0
    avg_rate_upper = [avg_positive(ur[n]) for n in brush_numbers]
    avg_rate_lower = [avg_positive(lr[n]) for n in brush_numbers]
    time_hours = np.arange(0, 201, 10)

    fig_upper = go.Figure()
    for i, (start, rate) in enumerate(zip(upper_current, avg_rate_upper)):
        y = [start - rate*t for t in time_hours]
        fig_upper.add_trace(go.Scatter(x=time_hours, y=y, name=f"Upper {i+1}", mode='lines'))

    fig_upper.update_layout(title="🔺 ความยาว Upper ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm", xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_upper, use_container_width=True)

    fig_lower = go.Figure()
    for i, (start, rate) in enumerate(zip(lower_current, avg_rate_lower)):
        y = [start - rate*t for t in time_hours]
        fig_lower.add_trace(go.Scatter(x=time_hours, y=y, name=f"Lower {i+1}", mode='lines', line=dict(dash='dot')))

    fig_lower.update_layout(title="🔻 ความยาว Lower ตามเวลา", xaxis_title="ชั่วโมง", yaxis_title="mm", xaxis=dict(dtick=10, range=[0, 200]), yaxis=dict(range=[30, 65]))
    st.plotly_chart(fig_lower, use_container_width=True)