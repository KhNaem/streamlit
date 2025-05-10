
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="คำนวณ Remaining Hours จาก Google Sheet", layout="wide")
st.title("📊 วิเคราะห์ Remaining Hours ถึง 35mm (จาก Google Sheet)")

# 📌 กำหนดจำนวน Sheet ที่ใช้คำนวณย้อนหลัง
sheet_count = st.number_input("📌 กรอกจำนวนชีตย้อนหลังที่ต้องใช้ (1-7)", min_value=1, max_value=7, value=6)

# ✅ ดึงข้อมูลจาก Google Sheets
sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

try:
    xls = pd.ExcelFile(sheet_url)
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

    color_upper = ['black' if h < 200 else 'red' for h in hour_upper]
    bars1 = ax1.bar(brush_numbers, hour_upper, color=color_upper)
    ax1.set_title("Remaining Hours to Reach 35mm - Upper")
    ax1.set_ylabel("Hours")
    ax1.set_xticks(brush_numbers)
    for bar, val in zip(bars1, hour_upper):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

    color_lower = ['black' if h < 800 else 'darkred' for h in hour_lower]
    bars2 = ax2.bar(brush_numbers, hour_lower, color=color_lower)
    ax2.set_title("Remaining Hours to Reach 35mm - Lower")
    ax2.set_ylabel("Hours")
    ax2.set_xticks(brush_numbers)
    for bar, val in zip(bars2, hour_lower):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(val)}", ha='center', fontsize=8)

    plt.tight_layout()

    # 🔍 วิเคราะห์แนวโน้ม Remaining Hours จาก Sheet1-2 ถึง Sheet1-7
    st.subheader("📈 แนวโน้มค่าเฉลี่ย Remaining Hours (Upper/Lower) เมื่อใช้ Sheet1 ถึง SheetX")
    history_upper, history_lower = [], []
    labels = []

    for count in range(2, 8):  # Sheet1-2 to Sheet1-7
        sheet_names = [f"Sheet{i}" for i in range(1, count + 1)]
        upper_rates_hist, lower_rates_hist = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}

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
                    upper_rates_hist[n][sheet] = rate if rate > 0 else np.nan

                l_row = lower_df[lower_df["No_Lower"] == n]
                if not l_row.empty:
                    diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                    rate = diff / hours if hours > 0 else np.nan
                    lower_rates_hist[n][sheet] = rate if rate > 0 else np.nan

        upper_df_hist = pd.DataFrame.from_dict(upper_rates_hist, orient='index')
        lower_df_hist = pd.DataFrame.from_dict(lower_rates_hist, orient='index')
        upper_df_hist["Avg"] = upper_df_hist.apply(avg_positive, axis=1)
        lower_df_hist["Avg"] = lower_df_hist.apply(avg_positive, axis=1)

        rate_u = upper_df_hist["Avg"].tolist()[:32]
        rate_l = lower_df_hist["Avg"].tolist()[:32]

        hr_u = calculate_hours_safe(upper_current, rate_u)
        hr_l = calculate_hours_safe(lower_current, rate_l)

        history_upper.append(np.nanmean(hr_u))
        history_lower.append(np.nanmean(hr_l))
        labels.append(f"Sheet1-{count}")

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(labels, history_upper, marker='o', label='Upper Avg Hours')
    ax.plot(labels, history_lower, marker='s', label='Lower Avg Hours')
    ax.set_ylabel("Avg Remaining Hours")
    ax.set_title("แนวโน้มค่าเฉลี่ย Remaining Hours จากการใช้ Sheet เพิ่มขึ้น")
    ax.legend()
    st.pyplot(fig)

    df_trend = pd.DataFrame({
        "ช่วงชีต": labels,
        "Upper Avg Hours": history_upper,
        "Lower Avg Hours": history_lower
    })
    st.dataframe(df_trend, use_container_width=True)

    st.pyplot(fig)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")
