
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("📉 วิเคราะห์แนวโน้ม Remaining Hours จาก Sheet 1 ถึง 7")

sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

xls = pd.ExcelFile(sheet_url)
brush_numbers = list(range(1, 33))
history_upper = []
history_lower = []

def avg_positive(rate_dict):
    valid = [v for v in rate_dict.values() if v > 0]
    return sum(valid) / len(valid) if valid else np.nan

def calculate_hours_safe(current, rate):
    return [(c - 35) / r if pd.notna(c) and r and r > 0 and c > 35 else 0 for c, r in zip(current, rate)]

df_current = xls.parse("Sheet7", header=None, skiprows=2)
upper_current = pd.to_numeric(df_current.iloc[0:32, 5], errors='coerce').values
lower_current = pd.to_numeric(df_current.iloc[0:32, 2], errors='coerce').values

for count in range(2, 8):  # Sheet1-2 ... Sheet1-7
    sheet_names = [f"Sheet{i}" for i in range(1, count + 1)]
    upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n: {} for n in brush_numbers}

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
                upper_rates[n][sheet] = rate if rate > 0 else np.nan

            l_row = lower_df[lower_df["No_Lower"] == n]
            if not l_row.empty:
                diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
                rate = diff / hours if hours > 0 else np.nan
                lower_rates[n][sheet] = rate if rate > 0 else np.nan

    upper_df = pd.DataFrame.from_dict(upper_rates, orient='index')
    lower_df = pd.DataFrame.from_dict(lower_rates, orient='index')
    upper_df["Avg Rate (Upper)"] = upper_df.apply(avg_positive, axis=1)
    lower_df["Avg Rate (Lower)"] = lower_df.apply(avg_positive, axis=1)

    avg_rate_upper = upper_df["Avg Rate (Upper)"].tolist()[:32]
    avg_rate_lower = lower_df["Avg Rate (Lower)"].tolist()[:32]

    hour_upper = calculate_hours_safe(upper_current, avg_rate_upper)
    hour_lower = calculate_hours_safe(lower_current, avg_rate_lower)

    history_upper.append(np.nanmean(hour_upper))
    history_lower.append(np.nanmean(hour_lower))

# แสดงผล
st.subheader("📊 แนวโน้มค่าเฉลี่ย Remaining Hours (Upper/Lower)")
labels = [f"Sheet1-{i}" for i in range(2, 8)]

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(labels, history_upper, marker='o', label='Upper')
ax.plot(labels, history_lower, marker='s', label='Lower')
ax.set_ylabel("Average Remaining Hours")
ax.set_title("แนวโน้ม Remaining Hours ตามจำนวน Sheet ที่ใช้คำนวณ")
ax.legend()
st.pyplot(fig)

# แสดงเป็นตารางด้วย
df_result = pd.DataFrame({
    "ช่วงชีต": labels,
    "Avg Upper Remaining Hours": history_upper,
    "Avg Lower Remaining Hours": history_lower
})
st.dataframe(df_result, use_container_width=True)
