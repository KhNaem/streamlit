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

    # โหลดข้อมูลจาก Google Sheet
    sheet_id = "1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    xls = pd.ExcelFile(sheet_url)
    sheet_names = xls.sheet_names
    num_sheets = st.number_input("📌 เลือกจำนวน Sheet ที่ต้องการใช้ (สำหรับคำนวณ Avg Rate)", 
                                 min_value=1, max_value=len(sheet_names), value=7)
    selected_sheets = sheet_names[:num_sheets]
    brush_numbers = list(range(1, 33))

    # คำนวณ Avg Rate
    upper_rates, lower_rates = {n:{} for n in brush_numbers}, {n:{} for n in brush_numbers}
    for sheet in selected_sheets:
        df0 = xls.parse(sheet, header=None)
        try:
            hours = float(df0.iloc[0, 7])
        except:
            continue
        df = xls.parse(sheet, skiprows=1, header=None)
        # Lower
        df_l = df.iloc[:,0:3].dropna().apply(pd.to_numeric,errors='coerce')
        df_l.columns=["No","Prev","Curr"]
        # Upper
        df_u = df.iloc[:,4:6].dropna().apply(pd.to_numeric,errors='coerce')
        df_u.columns=["Curr","Prev"]
        df_u["No"]=range(1,len(df_u)+1)
        # เก็บ rate
        for n in brush_numbers:
            ul = df_u[df_u["No"]==n]
            if not ul.empty:
                r = (ul.Curr.values[0]-ul.Prev.values[0])/hours
                if r>0: upper_rates[n][sheet]=r
            ll = df_l[df_l["No"]==n]
            if not ll.empty:
                r = (ll.Prev.values[0]-ll.Curr.values[0])/hours
                if r>0: lower_rates[n][sheet]=r

    def avg_pos(d):
        v=[x for x in d.values() if x>0]
        return sum(v)/len(v) if v else np.nan

    df_u = pd.DataFrame.from_dict(upper_rates,orient='index').fillna(0)
    df_l = pd.DataFrame.from_dict(lower_rates,orient='index').fillna(0)
    df_u["AvgRate"]=df_u.apply(avg_pos,axis=1)
    df_l["AvgRate"]=df_l.apply(avg_pos,axis=1)
    avg_u = df_u["AvgRate"].tolist()[:32]
    avg_l = df_l["AvgRate"].tolist()[:32]

    # ค่าสภาพปัจจุบัน
    if "Sheet7" not in xls.sheet_names:
        st.error("❌ ไม่พบ Sheet7")
        st.stop()
    df7 = xls.parse("Sheet7",header=None)
    curr_u = pd.to_numeric(df7.iloc[2:34,5],errors='coerce').values
    curr_l = pd.to_numeric(df7.iloc[2:34,2],errors='coerce').values

    # คำนวณ Remaining Hours
    def calc(rem,rate):
        return [(c-35)/r if pd.notna(c) and r>0 and c>35 else 0 for c,r in zip(rem,rate)]
    hr_u = calc(curr_u,avg_u)
    hr_l = calc(curr_l,avg_l)

    # สรุปสถิติ
    stats = {
        "": ["Min","Mean","Max"],
        "Upper": [np.nanmin(hr_u), np.nanmean(hr_u), np.nanmax(hr_u)],
        "Lower": [np.nanmin(hr_l), np.nanmean(hr_l), np.nanmax(hr_l)],
    }
    st.table(pd.DataFrame(stats).set_index(""))    

    # ดาวน์โหลดผลลัพธ์
    res = pd.DataFrame({
        "Brush":brush_numbers,
        "Curr_U":curr_u,"Curr_L":curr_l,
        "Rate_U":avg_u,"Rate_L":avg_l,
        "Hour_U":hr_u,"Hour_L":hr_l
    })
    st.download_button("📥 ดาวน์โหลด CSV", data=res.to_csv(index=False), file_name="remaining_hours.csv")

    # วาดกราฟ
    fig,axes = plt.subplots(2,1,figsize=(14,8))
    # Upper
    cols_u = ['orange' if h<100 else 'red' for h in hr_u]
    axes[0].bar(brush_numbers,hr_u,color=cols_u)
    axes[0].set_title("Remaining Hours - Upper")
    # Lower
    cols_l = ['orange' if h<200 else 'darkred' for h in hr_l]
    axes[1].bar(brush_numbers,hr_l,color=cols_l)
    axes[1].set_title("Remaining Hours - Lower")
    plt.tight_layout()
    st.pyplot(fig)

# ------------------ PAGE 2 ------------------
elif page == "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม":
    # (โค้ดไม่เปลี่ยน)

# ------------------ PAGE 3 ------------------
elif page == "📈 พล็อตกราฟตามเวลา (แยก Upper และ Lower)":
    # (โค้ดไม่เปลี่ยน)
