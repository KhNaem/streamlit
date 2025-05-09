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
                rate = (cu - pu) / h
                if rate > 0: ur[i][s] = rate
            if pd.notna(cl) and pd.notna(pl) and h > 0:
                rate = (pl - cl) / h
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
