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
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ")

    
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
    fig_combined.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='deepskyblue'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_combined.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_combined, use_container_width=True)

    st.subheader("🔺 กราฟ Avg Rate - Upper")
    fig_upper = go.Figure()
    fig_upper.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_upper, mode='lines+markers+text', name='Upper Avg Rate', line=dict(color='red'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_upper.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_upper, use_container_width=True)

    st.subheader("🔻 กราฟ Avg Rate - Lower")
    fig_lower = go.Figure()
    fig_lower.add_trace(go.Scatter(x=brush_numbers, y=avg_rate_lower, mode='lines+markers+text', name='Lower Avg Rate', line=dict(color='deepskyblue'), text=[str(i) for i in brush_numbers], textposition='top center'))
    fig_lower.update_layout(xaxis_title='Brush Number', yaxis_title='Wear Rate (mm/hour)', template='plotly_white')
    st.plotly_chart(fig_lower, use_container_width=True)


#----------------ลองแก้ดู----------------------------------------
    sheet_names = [ws.title for ws in sh.worksheets() if ws.title.lower().startswith("sheet")]
    sheet_count = st.number_input("📌 กรอกจำนวนชีตย้อนหลังที่ต้องใช้", min_value=1, max_value=len(sheet_names), value=6)
    try:
        xls = pd.ExcelFile(sheet_url)
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

        def avg_positive(row):
            valid = row[row > 0]
            return valid.sum() / len(valid) if len(valid) > 0 else np.nan

        upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
        lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')
        upper_df["Avg Rate (Upper)"] = upper_df.apply(avg_positive, axis=1)
        lower_df["Avg Rate (Lower)"] = lower_df.apply(avg_positive, axis=1)

        avg_rate_upper = upper_df["Avg Rate (Upper)"].tolist()[:32]
        avg_rate_lower = lower_df["Avg Rate (Lower)"].tolist()[:32]

        df_current = xls.parse(f"Sheet{sheet_count}", header=None, skiprows=2)
        upper_current = pd.to_numeric(df_current.iloc[0:32, 5], errors='coerce').values
        lower_current = pd.to_numeric(df_current.iloc[0:32, 2], errors='coerce').values

        def calculate_hours_safe(current, rate):
            return [(c - 35) / r if pd.notna(c) and r and r > 0 and c > 35 else 0 for c, r in zip(current, rate)]

        hour_upper = calculate_hours_safe(upper_current, avg_rate_upper)
        hour_lower = calculate_hours_safe(lower_current, avg_rate_lower)

        st.subheader("📋 ตารางผลการคำนวณ")
        result_df = pd.DataFrame({
            "Brush #": brush_numbers,
            "Upper Current (F)": upper_current,
            "Lower Current (C)": lower_current,
            "Avg Rate Upper": avg_rate_upper,
            "Avg Rate Lower": avg_rate_lower,
            "Remaining Hours Upper": hour_upper,
            "Remaining Hours Lower": hour_lower,
        })
        st.dataframe(result_df, use_container_width=True)

        st.subheader("📊 กราฟ Remaining Hours ถึง 35mm")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

        color_upper = ['black' if h < 500 else 'red' for h in hour_upper]
        bars1 = ax1.bar(brush_numbers, hour_upper, color=color_upper)
        ax1.set_title("Remaining Hours to Reach 35mm - Upper")
        ax1.set_ylabel("Hours")
        ax1.set_xticks(brush_numbers)
        for bar, val in zip(bars1, hour_upper):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

        color_lower = ['black' if h < 500 else 'deepskyblue' for h in hour_lower]
        bars2 = ax2.bar(brush_numbers, hour_lower, color=color_lower)
        ax2.set_title("Remaining Hours to Reach 35mm - Lower")
        ax2.set_ylabel("Hours")
        ax2.set_xticks(brush_numbers)
        for bar, val in zip(bars2, hour_lower):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

        plt.tight_layout()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
