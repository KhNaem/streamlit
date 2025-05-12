
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# สมมุติข้อมูล DataFrame
data = {
    "Brush #": list(range(1, 11)),
    "Sheet1": [0.0] * 10,
    "Sheet2": [None, 0.005, 0.025, 0.023, 0.01, 0.008, 0.007, 0.006, 0.005, 0.01],
    "Sheet3": [0.022, 0.007, 0.022, 0.013, 0.021, 0.025, 0.013, 0.021, 0.024, 0.023],
    "Sheet4": [0.005, 0.016, 0.024, 0.014, 0.020, 0.006, 0.018, 0.017, 0.012, 0.024],
    "Sheet5": [0.023, 0.004, 0.022, 0.007, 0.015, 0.023, 0.014, 0.009, 0.023, 0.027],
    "Sheet6": [0.025, 0.009333, 0.026, 0.011, 0.015, 0.006, 0.018, 0.011, 0.023, 0.026],
    "Sheet7": [0.011, 0.011, 0.024, 0.019, 0.015, 0.016, 0.020, 0.011, 0.011, 0.016],
}

df = pd.DataFrame(data)
df.set_index("Brush #", inplace=True)

def get_final_avg_rate(row):
    values = row.dropna().values
    if len(values) >= 5:
        avg = np.mean(values[:-1])
        diff = abs(values[-1] - avg)
        if diff / avg <= 0.05:
            return avg, True, row.dropna().index[-2]  # ใช้ค่าก่อนสุดท้ายตัดสิน
    return np.mean(values), False, None

rates, stable_flags, source_sheets = [], [], []

for i, row in df.iterrows():
    val, is_stable, src = get_final_avg_rate(row)
    rates.append(val)
    stable_flags.append(is_stable)
    source_sheets.append(src)

df["Avg Rate (Upper)"] = rates
df["is_stable"] = stable_flags
df["Stable_Sheet"] = source_sheets

def highlight_row(row):
    style = []
    for col in row.index:
        if row["is_stable"] and col == row["Stable_Sheet"]:
            style.append("background-color: yellow")
        elif col == "Avg Rate (Upper)":
            if row["is_stable"]:
                style.append("color: green; font-weight: bold")
            else:
                style.append("color: red; font-weight: bold")
        else:
            style.append("")
    return style

styled_df = df.style.apply(highlight_row, axis=1).format("{:.6f}", na_rep="None")
st.dataframe(styled_df, use_container_width=True)

st.markdown("🟨 **สีเหลือง**: Sheet ที่ใช้ในการตัดสินว่า Rate คงที่ (ต่างจากค่าเฉลี่ยก่อนหน้าน้อยกว่า 5%)")
st.markdown("🟩 **สีเขียว**: ค่า Avg Rate ที่ถูกตัดสินว่า 'คงที่' และจะไม่เปลี่ยนแม้มีข้อมูลใหม่")
st.markdown("🟥 **สีแดง**: ค่า Avg Rate ปกติ ที่ยังอาจเปลี่ยนได้เมื่อมีข้อมูลใหม่เข้ามา")
