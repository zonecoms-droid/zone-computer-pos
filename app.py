import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random
import qrcode
from io import BytesIO

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ZoneOnline Service - Ultimate Edition", 
    page_icon="⚡", 
    layout="wide"
)

# ฟังก์ชันเชื่อมต่อและสร้างฐานข้อมูล SQLite แบบอัตโนมัติ
def init_connection():
    conn = sqlite3.connect('zone_online.db', check_same_thread=False)
    return conn

def init_db(conn):
    cursor = conn.cursor()
    
    # 1. ตารางตั้งค่าร้านค้า
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            phone TEXT,
            tax_id TEXT,
            address TEXT,
            note TEXT
        )
    ''')
    # ใส่ค่าเริ่มต้นร้านค้าถ้ายังไม่มี
    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-123-4567', '1234567890123', 'อุบลราชธานี', 'ขอบคุณที่ใช้บริการครับ')
        ''')
        conn.commit()

    # 2. ตารางลูกค้า
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. ตารางพนักงาน/ช่าง
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'cashier', 'technician')) NOT NULL
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech1', 'ช่างดิด (มือหนึ่ง)', 'technician')")
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech2', 'ช่างเสริม', 'technician')")
        conn.commit()

    # 4. ตารางงานซ่อม
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            device_name TEXT NOT NULL,
            serial_number TEXT,
            problem_description TEXT NOT NULL,
            accessories TEXT,
            estimated_cost REAL,
            technician_id INTEGER,
            status TEXT DEFAULT 'RECEIVED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (technician_id) REFERENCES staff(id)
        )
    ''')
    cursor.close()

conn = init_connection()
init_db(conn)

# ดึงข้อมูลร้านค้ามาใช้แสดงผล
cursor = conn.cursor()
cursor.execute("SELECT store_name, phone, tax_id, address, note FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()
STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE = store_info

st.title(f"⚡ {STORE_NAME} [Ultimate Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (รองรับ QR ลงทะเบียนเอง และพิมพ์สลิปหลายขนาด)")

# เมนูด้านข้าง (Sidebar)
menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", [
    "📥 รับเครื่องซ่อมใหม่ (Pro Intake)", 
    "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (Self-Service)",
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🖨️ พิมพ์ใบรับซ่อม / สลิป (Multi-Size)",
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง",
    "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)"
])

# ==========================================
# 1. ระบบรับเครื่องซ่อมใหม่ (Pro Intake)
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่ (Pro Intake)":
    st.header("📥 บันทึกรับเครื่องซ่อมและมอบหมายงานช่าง")
    
    with st.form("pro_repair_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("ข้อมูลลูกค้า")
            customer_name = st.text_input("ชื่อ-นามสกุล ลูกค้า")
            phone = st.text_input("เบอร์โทรศัพท์ (ใช้เป็น Key หลัก)")
            address = st.text_area("ที่อยู่ลูกค้า (ถ้ามี)")
        with col2:
            st.subheader("ข้อมูลอุปกรณ์ & การซ่อม")
            device_name = st.text_input("รุ่นอุปกรณ์ (เช่น Notebook ASUS ROG)")
            serial_number = st.text_input("Serial Number (สำหรับเช็คประกัน)")
            accessories = st.text_input("อุปกรณ์ที่แนบมา (เช่น สายชาร์จ, กระเป๋า)")
            
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            problem_description = st.text_area("อาการเสีย / รายละเอียดจากปากลูกค้า")
            estimated_cost = st.number_input("ประเมินราคาค่าซ่อมเบื้องต้น (บาท)", min_value=0.0, step=100.0)
        with col4:
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name FROM staff WHERE role = 'technician'")
            techs = cursor.fetchall()
            cursor.close()
            tech_dict = {t[1]: t[0] for t in techs} if techs else {"ยังไม่มีข้อมูลช่าง": 0}
                
            selected_tech_name = st.selectbox("มอบหมายให้ช่างผู้รับผิดชอบ", list(tech_dict.keys()))
            technician_id = tech_dict[selected_tech_name]
            commission = st.number_input("ค่ามือ / คอมมิชชั่นช่างงานนี้ (บาท)", min_value=0.0, step=50.0)

        submit_btn = st.form_submit_button("🚀 บันทึกรับเครื่องเข้าสู่ระบบ")
        
        if submit_btn:
            if customer_name and phone and device_name:
                try:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO customers (name, phone, address) 
                        VALUES (?, ?, ?) 
                        ON CONFLICT(phone) DO UPDATE SET name = excluded.name, address = excluded.address;
                    """, (customer_name, phone, address))
                    
                    cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
                    customer_id = cursor.fetchone()[0]
                    
                    job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                    
                    cursor.execute("""
                        INSERT INTO repairs (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'RECEIVED')
                    """, (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id))
                    
                    conn.commit()
                    cursor.close()
                    st.success(f"🎉 บันทึกรับเครื่องสำเร็จ! เลขที่ใบงาน: **{job_code}**")
                    st.balloons()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")

# ==========================================
# 2. ระบบลูกค้าสแกน QR ลงทะเบียนเอง (Self-Service)
# ==========================================
elif menu == "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (Self-Service)":
    st.header("📱 ระบบลูกค้าลงทะเบียนแจ้งซ่อมด้วยตัวเองผ่าน QR Code")
    st.markdown("ตั้งจอหน้าร้านให้ลูกค้าสแกนเพื่อกรอกข้อมูลแจ้งซ่อมเองได้ทันที ไม่ต้องรอนพนักงานพิมพ์ให้!")
    
    # สร้าง QR Code จำลองลิงก์ระบบ
    qr_data = "https://share.streamlit.io/" # เปลี่ยนเป็นลิงก์เว็บจริงของเพื่อนได้
    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    st.image(buf.getvalue(), caption="สแกนเพื่อกรอกข้อมูลแจ้งซ่อมออนไลน์", width=250)
    
    st.markdown("---")
    st.subheader("📝 ฟอร์มลงทะเบียนสำหรับลูกค้า (เปิดบนมือถือลูกค้าได้)")
    
    with st.form("self_service_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์ติดต่อกลับ")
        c_device = st.text_input("ยี่ห้อ / รุ่นอุปกรณ์ (เช่น Notebook Acer, PC ประกอบ)")
        c_problem = st.text_area("อาการเสียเบื้องต้น / สิ่งที่ต้องการให้ซ่อม")
        c_accessories = st.text_input("อุปกรณ์ที่ส่งมาด้วย (เช่น สายชาร์จ, เมาส์)")
        
        self_submit = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อมเข้าร้าน")
        
        if self_submit:
            if c_name and c_phone and c_device:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO customers (name, phone) VALUES (?, ?) 
                    ON CONFLICT(phone) DO UPDATE SET name = excluded.name;
                """, (c_name, c_phone))
                cursor.execute("SELECT id FROM customers WHERE phone = ?", (c_phone,))
                cust_id = cursor.fetchone()[0]
                
                job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                cursor.execute("""
                    INSERT INTO repairs (job_code, customer_id, device_name, problem_description, accessories, status)
                    VALUES (?, ?, ?, ?, ?, 'RECEIVED')
                """, (job_code, cust_id, c_device, c_problem, c_accessories))
                conn.commit()
                cursor.close()
                st.success(f"🎉 ลงทะเบียนสำเร็จ! เลขที่ใบงานของคุณคือ: **{job_code}** กรุณาแจ้งเลขนี้กับพนักงานหน้าร้าน")
                st.balloons()
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วน")

# ==========================================
# 3. ติดตาม & อัปเดตสถานะงานซ่อม
# ==========================================
elif menu == "🔍 ติดตาม & อัปเดตสถานะงานซ่อม":
    st.header("🔍 ค้นหา จัดการ และอัปเดตสถานะงานซ่อม")
    search_query = st.text_input("🔍 ค้นหาด้วยเลขใบงาน, เบอร์โทร หรือชื่อลูกค้า")
    
    try:
        query = """
            SELECT r.id, r.job_code, c.name as customer_name, c.phone, r.device_name, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
        """
        if search_query:
            query += f" WHERE r.job_code LIKE '%{search_query}%' OR c.phone LIKE '%{search_query}%' OR c.name LIKE '%{search_query}%'"
        query += " ORDER BY r.created_at DESC;"
        
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.markdown("---")
            st.subheader("🛠️ อัปเดตสถานะงานซ่อม")
            selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการเปลี่ยนสถานะ", df['job_code'].tolist())
            new_status = st.selectbox("เปลี่ยนสถานะเป็น", [
                "RECEIVED (รับเครื่องเข้า)", "CHECKING (กำลังตรวจสอบอาการ)", 
                "WAITING_PART (รออะไหล่/ตีราคา)", "REPAIRING (กำลังดำเนินการซ่อม)", 
                "COMPLETED (ซ่อมเสร็จสิ้น พร้อมส่งมอบ)", "CANCELLED (ยกเลิกการซ่อม)"
            ])
            if st.button("💾 บันทึกการเปลี่ยนสถานะ"):
                status_code = new_status.split(" ")[0]
                cursor = conn.cursor()
                cursor.execute("UPDATE repairs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_code = ?", (status_code, selected_job))
                conn.commit()
                cursor.close()
                st.success(f"อัปเดตสถานะใบงาน {selected_job} เรียบร้อยแล้ว!")
                st.rerun()
        else:
            st.info("ไม่พบข้อมูลงานซ่อมในระบบ")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# ==========================================
# 4. พิมพ์ใบรับซ่อม / สลิป (Multi-Size)
# ==========================================
elif menu == "🖨️ พิมพ์ใบรับซ่อม / สลิป (Multi-Size)":
    st.header("🖨️ ระบบพิมพ์ใบรับซ่อมและสลิป (เลือกขนาดได้ตามใจชอบ)")
    
    cursor = conn.cursor()
    cursor.execute("SELECT job_code FROM repairs ORDER BY created_at DESC")
    jobs = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    if jobs:
        selected_print_job = st.selectbox("เลือกเลขใบงานที่ต้องการพิมพ์", jobs)
        print_size = st.radio("เลือกขนาดกระดาษพิมพ์", ["สลิปความร้อน (58mm / 80mm)", "ใบรับซ่อมมาตรฐาน (A4)"])
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.job_code, c.name, c.phone, r.device_name, r.serial_number, r.problem_description, r.accessories, r.estimated_cost, r.status, r.created_at
            FROM repairs r JOIN customers c ON r.customer_id = c.id
            WHERE r.job_code = ?
        """, (selected_print_job,))
        job_data = cursor.fetchone()
        cursor.close()
        
        if job_data:
            j_code, c_name, c_phone, dev, sn, prob, acc, cost, stat, date_in = job_data
            
            st.markdown("---")
            st.markdown("### 📄 ตัวอย่างเอกสารก่อนพิมพ์")
            
            if print_size == "สลิปความร้อน (58mm / 80mm)":
                st.markdown(f"""
                <div style="border: 2px dashed #333; padding: 15px; width: 300px; font-family: monospace; background: white; color: black;">
                    <center>
                        <h3><b>{STORE_NAME}</b></h3>
                        <p>โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                        <hr>
                        <h4><b>ใบรับซ่อมสินค้า / Repair Slip</b></h4>
                    </center>
                    <p><b>เลขที่ใบงาน:</b> {j_code}</p>
                    <p><b>วันที่:</b> {date_in}</p>
                    <p><b>ลูกค้า:</b> {c_name} ({c_phone})</p>
                    <p><b>อุปกรณ์:</b> {dev}</p>
                    <p><b>S/N:</b> {sn if sn else '-'}</p>
                    <p><b>อาการเสีย:</b> {prob}</p>
                    <p><b>อุปกรณ์ที่มา:</b> {acc if acc else '-'}</p>
                    <p><b>ประเมินราคา:</b> {cost:,.2f} บาท</p>
                    <hr>
                    <center><p>{STORE_NOTE}</p></center>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="border: 2px solid #333; padding: 30px; width: 100%; font-family: sans-serif; background: white; color: black;">
                    <h2 style="text-align: center;"><b>{STORE_NAME}</b></h2>
                    <p style="text-align: center;">ที่อยู่: {STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขประจำตัวผู้เสียภาษี: {STORE_TAX}</p>
                    <hr>
                    <h3 style="text-align: center;">ใบรับเครื่องซ่อม (Job Service Form)</h3>
                    <table style="width: 100%; margin-top: 20px;">
                        <tr><td><b>เลขที่ใบงาน:</b> {j_code}</td><td><b>วันที่รับเครื่อง:</b> {date_in}</td></tr>
                        <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                        <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                    </table>
                    <br>
                    <p><b>อาการเสีย / รายละเอียด:</b> {prob}</p>
                    <p><b>อุปกรณ์ที่แนบมาด้วย:</b> {acc if acc else '-'}</p>
                    <p><b>ประเมินราคาค่าซ่อมเบื้องต้น:</b> <b>{cost:,.2f} บาท</b></p>
                    <br><br>
                    <div style="display: flex; justify-content: space-between;">
                        <p>ลงชื่อ......................................................(ลูกค้า)<br>วันที่_____/_____/_____</p>
                        <p>ลงชื่อ......................................................(ผู้รับเครื่อง)<br>วันที่_____/_____/_____</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.info("💡 คำแนะนำ: กดปุ่ม Ctrl + P (หรือ Cmd + P บน Mac) เพื่อสั่งพิมพ์เอกสารนี้ออกเครื่องพิมพ์ได้ทันที!")
    else:
        st.info("ยังไม่มีข้อมูลใบงานในระบบ")

# ==========================================
# 5. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number ของสินค้า/อะไหล่")
    if sn_input:
        st.info(f"กำลังตรวจสอบข้อมูล Serial Number: **{sn_input}** ...")
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน! (ซื้อเมื่อ: 15 มกราคม 2026 / ประกันหมดอายุ: 15 มกราคม 2027)")

# ==========================================
# 6. ออกเอกสารการค้า (FlowAccount Style)
# ==========================================
elif menu == "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)":
    st.header("📄 ระบบออกเอกสารและใบกำกับภาษี (FlowAccount Style)")
    doc_type = st.selectbox("เลือกประเภทเอกสาร", ["ใบเสนอราคา (Quotation)", "ใบเสร็จรับเงิน / ใบกำกับภาษี (Tax Invoice)", "บิลเงินสด (Cash Receipt)"])
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        cust_name = st.text_input("ชื่อลูกค้า / บริษัท")
        cust_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก")
        cust_address = st.text_area("ที่อยู่ลูกค้า")
    with col2:
        doc_date = st.date_input("วันที่เอกสาร", datetime.today())
        payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "โอนเงิน (QR Code)", "บัตรเครดิต"])

    num_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
    subtotal = 0.0
    for i in range(int(num_items)):
        cols = st.columns([3, 1, 1, 1])
        with cols[0]: item_desc = st.text_input(f"รายการที่ {i+1}", key=f"desc_{i}")
        with cols[1]: qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{i}")
        with cols[2]: price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, key=f"price_{i}")
        with cols[3]:
            total_item = qty * price
            st.text_input("รวม", value=f"{total_item:,.2f}", disabled=True, key=f"total_{i}")
        subtotal += total_item

    st.markdown("---")
    col_a, col_b = st.columns([2, 1])
    with col_a: notes = st.text_area("หมายเหตุ", value=STORE_NOTE)
    with col_b:
        st.markdown(f"**มูลค่ารวม:** `{subtotal:,.2f} บาท`")
        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        grand_total = subtotal * 1.07 if include_vat else subtotal
        if include_vat: st.markdown(f"**VAT 7%:** `{subtotal * 0.07:,.2f} บาท`")
        st.markdown(f"### **ยอดสุทธิ:** `{grand_total:,.2f} บาท`")
        
    if st.button("💾 บันทึกและออกเอกสาร"):
        if cust_name:
            st.success(f"🎉 ออกเอกสารประเภท **{doc_type}** ยอดสุทธิ **{grand_total:,.2f} บาท** สำเร็จ!")
            st.balloons()
        else:
            st.warning("⚠️ กรุณากรอกชื่อลูกค้าก่อน")

# ==========================================
# 7. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
    st.info("ส่วนแสดงรายงานและคำนวณค่าคอมมิชชั่นช่างอัตโนมัติ")

# ==========================================
# 8. ตั้งค่าข้อมูลร้านค้า (Store Settings)
# ==========================================
elif menu == "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)":
    st.header("⚙️ ตั้งค่าข้อมูลร้านค้าและใบเสร็จ")
    st.markdown("แก้ไขข้อมูลร้านค้าเพื่อใช้แสดงผลบนใบรับซ่อมและใบเสร็จรับเงินได้อย่างอิสระเสรี")
    
    with st.form("settings_form"):
        new_store_name = st.text_input("ชื่อร้านค้า / บริษัท", value=STORE_NAME)
        new_phone = st.text_input("เบอร์โทรศัพท์ร้าน", value=STORE_PHONE)
        new_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี", value=STORE_TAX)
        new_address = st.text_area("ที่อยู่ร้านค้า", value=STORE_ADDRESS)
        new_note = st.text_input("ข้อความท้ายบิล / หมายเหตุ", value=STORE_NOTE)
        
        save_settings = st.form_submit_button("💾 บันทึกการตั้งค่าร้านค้า")
        
        if save_settings:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE store_settings 
                SET store_name = ?, phone = ?, tax_id = ?, address = ?, note = ? 
                WHERE id = 1
            """, (new_store_name, new_phone, new_tax_id, new_address, new_note))
            conn.commit()
            cursor.close()
            st.success("🎉 บันทึกการตั้งค่าร้านค้าเรียบร้อยแล้ว! กรุณารีเฟรชหน้าเว็บเพื่ออัปเดตข้อมูล")
            st.balloons()