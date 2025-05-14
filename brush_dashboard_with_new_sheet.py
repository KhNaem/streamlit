import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Brush Dashboard", layout="wide")

# Setup credentials and spreadsheet access
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sheet_url = "https://docs.google.com/spreadsheets/d/1Pd6ISon7-7n7w22gPs4S3I9N7k-6uODdyiTvsfXaSqY"
sh = gc.open_by_url(sheet_url)

sheet_names = [ws.title for ws in sh.worksheets()]
if "Sheet1" in sheet_names:
    sheet_names.remove("Sheet1")
    sheet_names = ["Sheet1"] + sheet_names

sheet_count = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องใช้", min_value=1, max_value=len(sheet_names), value=7)
selected_sheets = sheet_names[:sheet_count]

sheet_url_export = f"{sheet_url}/export?format=xlsx"
xls = pd.ExcelFile(sheet_url_export)

brush_numbers = list(range(1, 33))
upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}
rate_fixed_upper = set()
rate_fixed_lower = set()
yellow_mark_upper = {}
yellow_mark_lower = {}

# Step 1: Calculate rates per sheet
for sheet in selected_sheets:
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
            rate = diff / hours if hours > 0 else 0
            upper_rates[n][f"Upper_{sheet}"] = rate if rate > 0 else 0

        l_row = lower_df[lower_df["No_Lower"] == n]
        if not l_row.empty:
            diff = l_row.iloc[0]["Lower_Previous"] - l_row.iloc[0]["Lower_Current"]
            rate = diff / hours if hours > 0 else 0
            lower_rates[n][f"Lower_{sheet}"] = rate if rate > 0 else 0

# Step 2: Check for stable (fixed) rate logic
def determine_final_rate(previous_rates, new_rate, row_index, sheet_name, mark_dict, min_required=5, threshold=0.05):
    previous_rates = [r for r in previous_rates if pd.notna(r) and r > 0]
    if len(previous_rates) >= min_required:
        avg_rate = sum(previous_rates) / len(previous_rates)
        percent_diff = abs(new_rate - avg_rate) / avg_rate
        if percent_diff <= threshold:
            mark_dict[row_index] = sheet_name
            return round(avg_rate, 6), True
    combined = previous_rates + [new_rate] if new_rate > 0 else previous_rates
    final_avg = sum(combined) / len(combined) if combined else 0
    return round(final_avg, 6), False

def calc_avg_with_flag(rates_dict, rate_fixed_set, mark_dict):
    df = pd.DataFrame.from_dict(rates_dict, orient='index')
    df = df.reindex(range(1, 33)).fillna(0)
    avg_col = []
    for i, row in df.iterrows():
        values = row[row > 0].tolist()
        if len(values) >= 6:
            prev = values[:-1]
            new = values[-1]
            sheet_name = row[row > 0].index[-1] if len(row[row > 0].index) > 0 else ""
            avg, fixed = determine_final_rate(prev, new, i, sheet_name, mark_dict)
            avg_col.append(avg)
            if fixed:
                rate_fixed_set.add(i)
        else:
            avg_col.append(round(np.mean(values), 6) if values else 0.000000)
    return df, avg_col

upper_df, upper_avg = calc_avg_with_flag(upper_rates, rate_fixed_upper, yellow_mark_upper)
lower_df, lower_avg = calc_avg_with_flag(lower_rates, rate_fixed_lower, yellow_mark_lower)

upper_df["Avg Rate (Upper)"] = upper_avg
lower_df["Avg Rate (Lower)"] = lower_avg

# Step 3: Styling output
def highlight_fixed_rate_row(row, column_name, fixed_set, yellow_mark_dict):
    styles = []
    for col in row.index:
        if col == column_name:
            if row.name in fixed_set:
                styles.append("background-color: green; color: black; font-weight: bold")
            else:
                styles.append("color: red; font-weight: bold")
        elif yellow_mark_dict.get(row.name) == col:
            styles.append("color: yellow; font-weight: bold")
        else:
            styles.append("")
    return styles

st.subheader("📋 ตาราง Avg Rate - Upper")
styled_upper = upper_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Upper)", rate_fixed_upper, yellow_mark_upper), axis=1).format("{:.6f}")
st.write(styled_upper)

st.subheader("📋 ตาราง Avg Rate - Lower")
styled_lower = lower_df.style.apply(lambda row: highlight_fixed_rate_row(row, "Avg Rate (Lower)", rate_fixed_lower, yellow_mark_lower), axis=1).format("{:.6f}")
st.write(styled_lower)

st.markdown("🟩 **สีเขียว** = ค่าคงที่ที่นำไปใช้ในกราฟ")
st.markdown("🟨 **ตัวอักษรสีเหลือง** = ค่า Rate ที่ทำให้ค่าเฉลี่ยกลายเป็น 'คงที่'")
st.markdown("🔴 **สีแดง** = ค่า Rate ยังไม่คงที่")

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
