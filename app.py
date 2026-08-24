import streamlit as st
import qrcode
import io
import datetime

# ตั้งค่าหน้าจอเว็บแอป
st.set_page_config(page_title="ServiceTicker Online", layout="wide")

# แถบด้านข้าง (Sidebar): ล็อกอินและเมนู
st.sidebar.header("🔐 ระบบล็อกอินช่าง")
tech_name = st.sidebar.selectbox("เลือกชื่อช่างผู้รับงาน", ["ช่างดิด", "ช่างเอ", "ช่างบี", "ช่างทั่วไป"])

st.sidebar.divider()
menu = st.sidebar.selectbox("เมนูการทำงาน", ["รับงานซ่อมใหม่", "รายการงานซ่อมทั้งหมด"])

# จำลองฐานข้อมูลชั่วคราวใน Session State
if 'repairs' not in st.session_state:
    st.session_state['repairs'] = []

# เมนูที่ 1: รับงานซ่อมใหม่และสร้าง QR Code
if menu == "รับงานซ่อมใหม่":
    st.title("🛠️ ระบบรับแจ้งซ่อมและสร้าง QR Code")
    
    with st.form("repair_form"):
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("ชื่อลูกค้า")
            customer_phone = st.text_input("เบอร์โทรศัพท์")
            device_name = st.text_input("รุ่นอุปกรณ์ / อาการเสีย")
        with col2:
            serial_no = st.text_input("Serial Number (S/N)")
            deposit = st.number_input("เงินมัดจำ (บาท)", min_value=0.0, step=100.0)
            
        submitted = st.form_submit_button("บันทึกรับงานและสร้าง QR Code")
        
        if submitted:
            if customer_name and device_name:
                job_id = f"JOB-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                new_job = {
                    "job_id": job_id,
                    "customer": customer_name,
                    "phone": customer_phone,
                    "device": device_name,
                    "serial": serial_no,
                    "deposit": deposit,
                    "technician": tech_name,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                st.session_state['repairs'].append(new_job)
                st.success(f"บันทึกงานซ่อมสำเร็จ! หมายเลขใบงาน: {job_id}")
            else:
                st.error("กรุณากรอกข้อมูลชื่อลูกค้าและอุปกรณ์ให้ครบถ้วน")

    # แสดง QR Code สำหรับใบงานล่าสุด
    if st.session_state['repairs']:
        latest_job = st.session_state['repairs'][-1]
        st.divider()
        st.subheader(f"📲 QR Code สำหรับติดตามงาน / ชำระเงิน (ใบงาน: {latest_job['job_id']})")
        
        qr_data = f"ใบงาน: {latest_job['job_id']} | ลูกค้า: {latest_job['customer']} | อุปกรณ์: {latest_job['device']}"
        
        img = qrcode.make(qr_data)
        buf = io.BytesIO()
        img.save(buf)
        byte_im = buf.getvalue()
        
        col_qr1, col_qr2 = st.columns([1, 2])
        with col_qr1:
            st.image(byte_im, width=200)
        with col_qr2:
            st.write(f"**รหัสใบงาน:** {latest_job['job_id']}")
            st.write(f"**ชื่อลูกค้า:** {latest_job['customer']} ({latest_job['phone']})")
            st.write(f"**อุปกรณ์:** {latest_job['device']}")
            st.write(f"**Serial Number:** {latest_job['serial'] if latest_job['serial'] else 'ไม่มี'}")
            st.write(f"**ช่างผู้รับผิดชอบ:** {latest_job['technician']}")

# เมนูที่ 2: ดูรายการงานซ่อมทั้งหมด
elif menu == "รายการงานซ่อมทั้งหมด":
    st.title("📋 รายการงานซ่อมในระบบ")
    if st.session_state['repairs']:
        for job in st.session_state['repairs']:
            with st.expander(f"ใบงาน: {job['job_id']} - {job['customer']} ({job['device']})"):
                st.write(f"**เบอร์โทร:** {job['phone']}")
                st.write(f"**Serial Number:** {job['serial']}")
                st.write(f"**เงินมัดจำ:** {job['deposit']} บาท")
                st.write(f"**ช่างผู้รับผิดชอบ:** {job['technician']}")
                st.write(f"**วันที่รับเครื่อง:** {job['date']}")
    else:
        st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")