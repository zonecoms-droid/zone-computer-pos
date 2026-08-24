import streamlit as st
import qrcode
import io
import datetime
import pandas as pd

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ServiceTicker Online", layout="wide", page_icon="💻")

# จำลองฐานข้อมูลใน Session State
if 'repairs' not in st.session_state:
    st.session_state['repairs'] = []
if 'inventory' not in st.session_state:
    st.session_state['inventory'] = [
        {"id": "P001", "name": "แรม DDR4 8GB", "cost": 600, "price": 990, "stock": 10, "serial": "SN-884102"},
        {"id": "P002", "name": "SSD 240GB", "cost": 500, "price": 850, "stock": 5, "serial": "SN-992311"},
        {"id": "P003", "name": "จอคอมพิวเตอร์ 24 นิ้ว", "cost": 2500, "price": 3500, "stock": 3, "serial": "SN-110293"}
    ]
if 'sales' not in st.session_state:
    st.session_state['sales'] = []

# --- แถบด้านข้าง: ระบบล็อกอินและเมนูหลัก ---
st.sidebar.header("🔐 ระบบล็อกอินผู้ใช้งาน")
tech_list = ["ช่างดิด", "ช่างเอ", "ช่างบี", "แอดมินหน้าร้าน"]
logged_in_user = st.sidebar.selectbox("เลือกชื่อช่าง / ผู้ใช้งาน", tech_list)

st.sidebar.divider()
menu = st.sidebar.radio(
    "📌 เมนูการทำงานหลัก",
    [
        "1. รับงานซ่อม & สร้าง QR Code",
        "2. เช็คสถานะ & ส่งคืนงานซ่อม",
        "3. จัดสต็อก & Serial Number",
        "4. ระบบขายสินค้า (POS)",
        "5. รายงานและบัญชี"
    ]
)

# ==========================================
# เมนูที่ 1: รับงานซ่อม & สร้าง QR Code
# ==========================================
if menu == "1. รับงานซ่อม & สร้าง QR Code":
    st.title("🛠️ ระบบรับแจ้งซ่อมและสร้าง QR Code สำหรับลูกค้า")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.form("repair_form"):
            st.subheader("กรอกข้อมูลเครื่องซ่อม")
            customer_name = st.text_input("ชื่อลูกค้า")
            customer_phone = st.text_input("เบอร์โทรศัพท์")
            device_detail = st.text_input("รุ่นอุปกรณ์ / อาการเสีย")
            serial_no = st.text_input("Serial Number (S/N) อุปกรณ์")
            deposit = st.number_input("เงินมัดจำ (บาท)", min_value=0.0, step=100.0)
            
            submitted = st.form_submit_button("บันทึกรับงานและสร้าง QR Code")
            
            if submitted:
                if customer_name and device_detail:
                    job_id = f"JOB-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    new_job = {
                        "job_id": job_id,
                        "customer": customer_name,
                        "phone": customer_phone,
                        "device": device_detail,
                        "serial": serial_no if serial_no else "ไม่มี S/N",
                        "deposit": deposit,
                        "technician": logged_in_user,
                        "status": "รอซ่อม",
                        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state['repairs'].append(new_job)
                    st.success(f"บันทึกรับงานสำเร็จ! รหัสใบงาน: {job_id}")
                else:
                    st.error("กรุณากรอกชื่อลูกค้าและอาการเสียให้ครบถ้วน")

    with col2:
        st.subheader("📲 สร้าง QR Code ลงทะเบียน & สแกนจ่าย")
        # สร้าง QR สำหรับให้ลูกค้าลงทะเบียนหรือสแกนจ่าย
        qr_type = st.radio("เลือกประเภท QR Code", ["QR Code ลงทะเบียนซ่อมเอง", "QR Code สแกนจ่ายเงิน (PromptPay)"])
        
        if st.session_state['repairs']:
            latest_job = st.session_state['repairs'][-1]
            if qr_type == "QR Code ลงทะเบียนซ่อมเอง":
                qr_data = f"https://your-shop-register-url.com/job={latest_job['job_id']}"
                st.info("สแกนเพื่อลงทะเบียนหรือดูข้อมูลใบงานล่าสุด")
            else:
                qr_data = f"PromptPay: 081-234-5678 (ยอดชำระมัดจำ: {latest_job['deposit']} บาท)"
                st.info(f"สแกนชำระเงินมัดจำใบงาน {latest_job['job_id']} จำนวน {latest_job['deposit']} บาท")
            
            img = qrcode.make(qr_data)
            buf = io.BytesIO()
            img.save(buf)
            st.image(buf.getvalue(), width=220)
        else:
            st.warning("ยังไม่มีรายการใบงานในระบบสำหรับสร้าง QR Code")

# ==========================================
# เมนูที่ 2: เช็คสถานะ & ส่งคืนงานซ่อม
# ==========================================
elif menu == "2. เช็คสถานะ & ส่งคืนงานซ่อม":
    st.title("📋 เช็คสถานะและส่งคืนงานซ่อม")
    
    if st.session_state['repairs']:
        for i, job in enumerate(st.session_state['repairs']):
            with st.expander(f"ใบงาน: {job['job_id']} | ลูกค้า: {job['customer']} | สถานะ: [{job['status']}]"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**อุปกรณ์:** {job['device']}")
                    st.write(f"**Serial Number:** {job['serial']}")
                    st.write(f"**เบอร์โทร:** {job['phone']}")
                    st.write(f"**ช่างรับผิดชอบ:** {job['technician']}")
                with col_b:
                    new_status = st.selectbox(f"เปลี่ยนสถานะ ({job['job_id']})", ["รอซ่อม", "กำลังซ่อม", "ซ่อมเสร็จแล้ว", "ส่งคืนลูกค้าแล้ว"], index=["รอซ่อม", "กำลังซ่อม", "ซ่อมเสร็จแล้ว", "ส่งคืนลูกค้าแล้ว"].index(job['status']), key=f"status_{i}")
                    if new_status != job['status']:
                        st.session_state['repairs'][i]['status'] = new_status
                        st.success("อัปเดตสถานะเรียบร้อย!")
                        st.rerun()
    else:
        st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")

# ==========================================
# เมนูที่ 3: จัดสต็อก & Serial Number
# ==========================================
elif menu == "3. จัดสต็อก & Serial Number":
    st.title("📦 ระบบจัดการสต็อกและ Serial Number")
    
    st.subheader("รายชื่ออะไหล่และสินค้าในสต็อก")
    df_stock = pd.DataFrame(st.session_state['inventory'])
    st.dataframe(df_stock, use_container_width=True)
    
    with st.form("add_product"):
        st.subheader("นำเข้าอะไหล่/สินค้าใหม่")
        col1, col2, col3 = st.columns(3)
        with col1:
            p_name = st.text_input("ชื่อสินค้า/อะไหล่")
            p_id = st.text_input("รหัสสินค้า")
        with col2:
            cost_price = st.number_input("ราคาต้นทุน (บาท)", min_value=0.0)
            sell_price = st.number_input("ราคาขาย (บาท)", min_value=0.0)
        with col3:
            stock_qty = st.number_input("จำนวนสต็อก", min_value=1, value=1)
            serial_num = st.text_input("Serial Number (รายชิ้น)")
            
        add_btn = st.form_submit_button("บันทึกนำเข้าสินค้า")
        if add_btn:
            if p_name and p_id:
                st.session_state['inventory'].append({
                    "id": p_id, "name": p_name, "cost": cost_price, "price": sell_price, "stock": stock_qty, "serial": serial_num if serial_num else "N/A"
                })
                st.success(f"นำเข้าสินค้า {p_name} สำเร็จ!")
                st.rerun()

# ==========================================
# เมนูที่ 4: ระบบขายสินค้า (POS)
# ==========================================
elif menu == "4. ระบบขายสินค้า (POS)":
    st.title("🛒 ระบบขายสินค้าและออกเอกสารใบเสร็จ")
    
    selected_product = st.selectbox("เลือกสินค้าสำหรับขาย", st.session_state['inventory'], format_func=lambda x: f"{x['name']} - ราคา {x['price']} บาท (เหลือ {x['stock']} ชิ้น)")
    qty_to_buy = st.number_input("จำนวนที่ซื้อ", min_value=1, value=1)
    
    if st.button("ยืนยันการขาย"):
        total_price = selected_product['price'] * qty_to_buy
        st.session_state['sales'].append({
            "product": selected_product['name'],
            "qty": qty_to_buy,
            "total": total_price,
            "seller": logged_in_user,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success(f"ขายสินค้าสำเร็จ! ยอดรวม {total_price} บาท (ออกใบเสร็จรับเงิน / ใบกำกับภาษีเรียบร้อย)")

# ==========================================
# เมนูที่ 5: รายงานและบัญชี
# ==========================================
elif menu == "5. รายงานและบัญชี":
    st.title("📊 ระบบรายงาน ยอดขาย และผลกำไรช่าง")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ยอดขายสินค้าทั้งหมด")
        if st.session_state['sales']:
            df_sales = pd.DataFrame(st.session_state['sales'])
            st.dataframe(df_sales, use_container_width=True)
            total_sales = df_sales['total'].sum()
            st.metric("ยอดขายรวมทั้งสิ้น", f"{total_sales:,.2f} บาท")
        else:
            st.info("ยังไม่มีข้อมูลการขาย")
            
    with col2:
        st.subheader("สรุปงานซ่อมและกำไร")
        if st.session_state['repairs']:
            df_repairs = pd.DataFrame(st.session_state['repairs'])
            st.dataframe(df_repairs[['job_id', 'customer', 'device', 'technician', 'status']], use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อม")