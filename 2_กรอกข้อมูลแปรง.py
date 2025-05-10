import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import gspread
from google.oauth2.service_account import Credentials

# 💡 วางโค้ด PAGE 2 ที่นี่
st.title("📝 กรอกข้อมูลแปรงถ่าน + ชั่วโมง")

service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
gc = gspread.authorize(creds)
sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ")

editable_sheets = [ws.title for ws in sh.worksheets() if "Sheet" in ws.title]
selected_sheet = st.selectbox("📄 เลือก Sheet ที่ต้องการกรอกข้อมูล", editable_sheets)
ws = sh.worksheet(selected_sheet)

hours = st.number_input("⏱️ ชั่วโมง", min_value=0.0, step=0.1)

st.markdown("### 🔧 แปลงถ่านส่วน UPPER")
upper = []
cols = st.columns(8)
for i in range(32):
    col = cols[i % 8]
    with col:
        st.markdown(f"<div style='text-align: center;'>แปลงถ่านที่ {i+1}</div>", unsafe_allow_html=True)
        value = st.text_input(f"{i+1}", key=f"upper_{i}", placeholder="0.00")
        try:
            upper.append(float(value))
        except:
            upper.append(0.0)

st.markdown("### 🔧 แปลงถ่านส่วน LOWER")
lower = []
cols = st.columns(8)
for i in range(32):
    col = cols[i % 8]
    with col:
        st.markdown(f"<div style='text-align: center;'>แปลงถ่านที่ {i+1}</div>", unsafe_allow_html=True)
        value = st.text_input(f"{i+1}", key=f"lower_{i}", placeholder="0.00")
        try:
            lower.append(float(value))
        except:
            lower.append(0.0)

if st.button("📤 บันทึก"):
    try:
        ws.update("H1", [[hours]])
        ws.update("F3:F34", [[v] for v in upper])
        ws.update("C3:C34", [[v] for v in lower])
        st.success(f"✅ บันทึกลง {selected_sheet} แล้วเรียบร้อย")
    except Exception as e:
        st.error(f"❌ {e}")

# ------------------ แสดงตารางรวม ------------------
st.subheader("📄 ตารางรวม Upper + Lower (Current / Previous)")
xls = pd.ExcelFile("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx")
sheet_options = [s for s in xls.sheet_names if "Sheet" in s and "Sheet8" not in s]
selected_view_sheet = st.selectbox("📌 เลือกชีตที่ต้องการดู", sheet_options)

try:
    df = xls.parse(selected_view_sheet, header=0)
    df = df.dropna(subset=["Upper_Current", "Upper_Previous", "Lower_Current", "Lower_Previous"])

    upper_df = df[["Upper_Current", "Upper_Previous"]].dropna()
    lower_df = df[["Lower_Current", "Lower_Previous"]].dropna()
    combined_df = pd.concat([upper_df, lower_df], axis=1)
    st.dataframe(combined_df)
    
    # เพิ่มตัวแปร x สำหรับ upper และ lower โดยแยกกัน
    x_upper = list(range(1, len(upper_df) + 1))
    x_lower = list(range(1, len(lower_df) + 1))

    st.markdown("### 📊 กราฟรวม Upper และ Lower (Current vs Previous)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_upper, y=upper_df["Upper_Current"], mode='lines+markers',
        name='Upper Current', line=dict(color='blue')))

    fig.add_trace(go.Scatter(
        x=x_upper, y=upper_df["Upper_Previous"], mode='lines+markers',
        name='Upper Previous', line=dict(color='blue', dash='dot')))

    fig.add_trace(go.Scatter(
        x=x_lower, y=lower_df["Lower_Current"], mode='lines+markers',
        name='Lower Current', line=dict(color='red')))

    fig.add_trace(go.Scatter(
        x=x_lower, y=lower_df["Lower_Previous"], mode='lines+markers',
        name='Lower Previous', line=dict(color='red', dash='dot')))

    

    fig.update_layout(xaxis_title='Brush Number', yaxis_title='mm', height=600)
    st.plotly_chart(fig, use_container_width=True)


except Exception as e:
    st.error(f"❌ ไม่สามารถโหลดข้อมูลจากชีตนี้ได้: {e}")































# import streamlit as st
# import pandas as pd
# import numpy as np
# import plotly.graph_objects as go
# import matplotlib.pyplot as plt
# import gspread
# from google.oauth2.service_account import Credentials


# # 💡 วางโค้ด PAGE 2 ที่นี่
# #if page == "📝 กรอกข้อมูลแปลงถ่านเพิ่มเติม":
# st.title("📝 กรอกข้อมูลแปรงถ่าน + ชั่วโมง")

# service_account_info = st.secrets["gcp_service_account"]
# creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
# gc = gspread.authorize(creds)
# sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ")

# editable_sheets = [ws.title for ws in sh.worksheets() if "Sheet" in ws.title]
# selected_sheet = st.selectbox("📄 เลือก Sheet ที่ต้องการกรอกข้อมูล", editable_sheets)
# ws = sh.worksheet(selected_sheet)

# hours = st.number_input("⏱️ ชั่วโมง", min_value=0.0, step=0.1)

# st.markdown("### 🔧 แปลงถ่านส่วน UPPER")
# upper = []
# cols = st.columns(8)
# for i in range(32):
#     col = cols[i % 8]
#     with col:
#         st.markdown(f"<div style='text-align: center;'>แปลงถ่านที่ {i+1}</div>", unsafe_allow_html=True)
#         value = st.text_input(f"{i+1}", key=f"upper_{i}", placeholder="0.00")

#         try:
#             upper.append(float(value))
#         except:
#             upper.append(0.0)

# st.markdown("### 🔧 แปลงถ่านส่วน LOWER")
# lower = []
# cols = st.columns(8)
# for i in range(32):
#     col = cols[i % 8]
#     with col:
#         st.markdown(f"<div style='text-align: center;'>แปลงถ่านที่ {i+1}</div>", unsafe_allow_html=True)
#         value = st.text_input(f"{i+1}", key=f"lower_{i}", placeholder="0.00")

#         try:
#             lower.append(float(value))
#         except:
#             lower.append(0.0)

# if st.button("📤 บันทึก"):
#     try:
#         ws.update("H1", [[hours]])
#         #ws.update("C3:C34", [[v] for v in upper])
#         #ws.update("F3:F34", [[v] for v in lower])
#         ws.update("F3:F34", [[v] for v in upper])
#         ws.update("C3:C34", [[v] for v in lower])
#         st.success(f"✅ บันทึกลง {selected_sheet} แล้วเรียบร้อย")
#     except Exception as e:
#         st.error(f"❌ {e}")

# # ------------------ แสดงตารางรวม ------------------
# st.subheader("📄 ตารางรวม Upper + Lower (Current / Previous)")
# xls = pd.ExcelFile("https://docs.google.com/spreadsheets/d/1SOkIH9jchaJi_0eck5UeyUR8sTn2arndQofmXv5pTdQ/export?format=xlsx")
# sheet_options = [s for s in xls.sheet_names if "Sheet" in s and "Sheet8" not in s]
# selected_view_sheet = st.selectbox("📌 เลือกชีตที่ต้องการดู", sheet_options)

# try:
#     df = xls.parse(selected_view_sheet, header=0)
#     df = df.dropna(subset=["Upper_Current", "Upper_Previous", "Lower_Current", "Lower_Previous"])


#     upper_df = df[["Upper_Current", "Upper_Previous"]]
#     lower_df = df[["Lower_Current", "Lower_Previous"]]


#     combined_df = pd.concat([upper_df, lower_df], axis=1)
#     st.dataframe(combined_df)


#     st.markdown("### 📊 กราฟรวม Upper และ Lower (Current vs Previous)")
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(
#         y=upper_df["Upper_Current"], x=x,
#         mode='lines+markers', name='Upper Current'
#     ))
#     fig.add_trace(go.Scatter(
#         y=upper_df["Upper_Previous"], x=x,
#         mode='lines+markers', name='Upper Previous'
#     ))
#     fig.add_trace(go.Scatter(
#         y=lower_df["Lower_Current"], x=x,
#         mode='lines+markers', name='Lower Current', line=dict(dash='dot')
#     ))
#     fig.add_trace(go.Scatter(
#         y=lower_df["Lower_Previous"], x=x,
#         mode='lines+markers', name='Lower Previous', line=dict(dash='dot')
#     ))
#     fig.update_layout(xaxis_title='Brush Number', yaxis_title='mm', height=600)
#     st.plotly_chart(fig, use_container_width=True)
# except Exception as e:
#     st.error(f"❌ ไม่สามารถโหลดข้อมูลจากชีตนี้ได้: {e}")