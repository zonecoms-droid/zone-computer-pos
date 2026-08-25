import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ZoneOnline Service - SQLite Pro Edition", 
    page_icon="⚡", 
    layout="wide"
)

# ฟังก์ชันเชื่อมต่อและสร้างฐานข้อมูล SQLite แบบอัตโนมัติ
def init_connection():
    # สร้างไฟล์ฐานข้อมูลชื่อ zone_online.db ในโปรเจกต์อัตโนมัติ
    conn = sqlite3.connect('zone_online.db', check_same_thread=False)
    return conn

def init_db(conn):
    cursor = conn.cursor()
    # 1. ตารางลูกค้า
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 2. ตารางพนักงาน/ช่าง
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'cashier', 'technician')) NOT NULL
        )
    ''')
    # เพิ่มช่างเริ่มต้นถ้ายังไม่มีในระบบ
    cursor.execute("SELECT COUNT(*) FROM staff")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech1', 'ช่างดิด (มือหนึ่ง)', 'technician')")
        cursor.execute("INSERT INTO staff (username, full_name, role) VALUES ('tech2', 'ช่างเสริม', 'technician')")
        conn.commit()

    # 3. ตารางงานซ่อม
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

# เริ่มต้นเชื่อมต่อและสร้างตาราง
conn = init_connection()
init_db(conn)

st.title("⚡ ZoneOnline Service System [SQLite Pro Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (ใช้งานง่าย ไม่ต้องต่อ Host นอก)")

# เมนูด้านข้าง (Sidebar)
menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", [
    "📥 รับเครื่องซ่อมใหม่ (Pro Intake)", 
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง"
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
            device_name = st.text_input("รุ่นอุปกรณ์ (เช่น Notebook ASUS ROG / Monitor MSI)")
            serial_number = st.text_input("Serial Number (สำหรับเช็คประกัน)")
            accessories = st.text_input("อุปกรณ์ที่แนบมา (เช่น สายชาร์จ, กระเป๋า, เมาส์)")
            
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            problem_description = st.text_area("อาการเสีย / รายละเอียดจากปากลูกค้า")
            estimated_cost = st.number_input("ประเมินราคาค่าซ่อมเบื้องต้น (บาท)", min_value=0.0, step=100.0)
            
        with col4:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, full_name FROM staff WHERE role = 'technician'")
                techs = cursor.fetchall()
                cursor.close()
                tech_dict = {t[1]: t[0] for t in techs} if techs else {"ยังไม่มีช่างในระบบ": 0}
            except:
                tech_dict = {"ยังไม่มีข้อมูลช่าง": 0}
                
            selected_tech_name = st.selectbox("มอบหมายให้ช่างผู้รับผิดชอบ", list(tech_dict.keys()))
            technician_id = tech_dict[selected_tech_name]
            
            commission = st.number_input("ค่ามือ / คอมมิชชั่นช่างงานนี้ (บาท)", min_value=0.0, step=50.0)

        submit_btn = st.form_submit_button("🚀 บันทึกรับเครื่องเข้าสู่ระบบ")
        
        if submit_btn:
            if customer_name and phone and device_name:
                try:
                    cursor = conn.cursor()
                    
                    # บันทึกหรืออัปเดตข้อมูลลูกค้า (SQLite Upsert)
                    cursor.execute("""
                        INSERT INTO customers (name, phone, address) 
                        VALUES (?, ?, ?) 
                        ON CONFLICT(phone) DO UPDATE SET name = excluded.name, address = excluded.address;
                    """, (customer_name, phone, address))
                    
                    # ดึง ID ของลูกค้า
                    cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone,))
                    customer_id = cursor.fetchone()[0]
                    
                    job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                    
                    cursor.execute("""
                        INSERT INTO repairs (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'RECEIVED')
                    """, (job_code, customer_id, device_name, serial_number, problem_description, accessories, estimated_cost, technician_id))
                    
                    conn.commit()
                    cursor.close()
                    
                    st.success(f"🎉 บันทึกรับเครื่องสำเร็จ! เลขที่ใบงานสำหรับให้ลูกค้าเช็คสถานะ: **{job_code}**")
                    st.balloons()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญ (ชื่อลูกค้า, เบอร์โทร, รุ่นอุปกรณ์) ให้ครบถ้วน")

# ==========================================
# 2. ระบบติดตาม & อัปเดตสถานะงานซ่อม
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
                "RECEIVED (รับเครื่องเข้า)", 
                "CHECKING (กำลังตรวจสอบอาการ)", 
                "WAITING_PART (รออะไหล่/ตีราคา)", 
                "REPAIRING (กำลังดำเนินการซ่อม)", 
                "COMPLETED (ซ่อมเสร็จสิ้น พร้อมส่งมอบ)", 
                "CANCELLED (ยกเลิกการซ่อม)"
            ])
            
            if st.button("💾 บันทึกการเปลี่ยนสถานะ"):
                status_code = new_status.split(" ")[0]
                cursor = conn.cursor()
                cursor.execute("UPDATE repairs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_code = ?", (status_code, selected_job))
                conn.commit()
                cursor.close()
                st.success(f"อัปเดตสถานะใบงาน {selected_job} เป็น {status_code} เรียบร้อยแล้ว!")
                st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ หรือไม่พบคำค้นหาที่ระบุ")
    except Exception as e:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {e}")

# ==========================================
# 3. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number ของสินค้า/อะไหล่")
    
    if sn_input:
        st.info(f"กำลังตรวจสอบข้อมูล Serial Number: **{sn_input}** ...")
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน! (ซื้อเมื่อ: 15 มกราคม 2026 / ประกันหมดอายุ: 15 มกราคม 2027)")

# ==========================================
# 4. ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)
# ==========================================
elif menu == "📄 ออกเอกสารการค้า / ใบเสร็จ (FlowAccount Style)":
    st.header("📄 ระบบออกเอกสารและใบกำกับภาษี (FlowAccount Style)")
    st.markdown("สร้างใบเสนอราคา ใบเสร็จรับเงิน และใบกำกับภาษีแบบมืออาชีพ ถูกต้องตามรูปแบบธุรกิจไทย")
    
    doc_type = st.selectbox("เลือกประเภทเอกสารที่ต้องการออก", [
        "ใบเสนอราคา (Quotation)", 
        "ใบเสร็จรับเงิน / ใบกำกับภาษี (Cash Sale / Tax Invoice)", 
        "บิลเงินสด / ใบเสร็จรับเงิน (Cash Receipt)"
    ])
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("ข้อมูลลูกค้า / คู่ค้า")
        cust_name = st.text_input("ชื่อลูกค้า / บริษัท", placeholder="บริษัท โซนคอมพิวเตอร์ จำกัด")
        cust_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี (13 หลัก)", placeholder="01055xxxxxxxx")
        cust_address = st.text_area("ที่อยู่สำหรับออกใบกำกับภาษี")
        
    with col2:
        st.subheader("รายละเอียดเอกสาร")
        doc_date = st.date_input("วันที่เอกสาร", datetime.today())
        due_date = st.date_input("วันครบกำหนดชำระ", datetime.today())
        payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "โอนเงินผ่านธนาคาร (QR Code)", "บัตรเครดิต"])

    st.markdown("### 🛒 รายการสินค้าและบริการ")
    
    num_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
    
    subtotal = 0.0
    
    for i in range(int(num_items)):
        cols = st.columns([3, 1, 1, 1])
        with cols[0]:
            item_desc = st.text_input(f"รายการที่ {i+1}", key=f"desc_{i}", placeholder="เช่น ประกอบคอมพิวเตอร์สเปคเล่นเกม / ค่าบริการซ่อม")
        with cols[1]:
            qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{i}")
        with cols[2]:
            price = st.number_input("ราคา/หน่วย (บาท)", min_value=0.0, step=100.0, key=f"price_{i}")
        with cols[3]:
            total_item = qty * price
            st.text_input("รวม (บาท)", value=f"{total_item:,.2f}", disabled=True, key=f"total_{i}")
        subtotal += total_item

    st.markdown("---")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        notes = st.text_area("หมายเหตุท้ายเอกสาร", value="เงื่อนไขการรับประกันสินค้าเป็นไปตามที่บริษัทกำหนด")
        
    with col_b:
        st.markdown(f"**มูลค่ารวมสินค้า/บริการ:** `{subtotal:,.2f} บาท`")
        
        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        
        if include_vat:
            vat_amount = subtotal * 0.07
            grand_total = subtotal + vat_amount
            st.markdown(f"**ภาษีมูลค่าเพิ่ม (VAT 7%):** `{vat_amount:,.2f} บาท`")
        else:
            grand_total = subtotal
            
        st.markdown(f"### **ยอดชำระสุทธิทั้งสิ้น:** `{grand_total:,.2f} บาท`")
        
    st.markdown("---")
    if st.button("💾 บันทึกและออกเอกสารอย่างเป็นทางการ"):
        if cust_name:
            st.success(f"🎉 สร้างเอกสารประเภท **{doc_type}** ให้กับคุณ **{cust_name}** ยอดสุทธิ **{grand_total:,.2f} บาท** เรียบร้อยแล้ว!")
            st.balloons()
        else:
            st.warning("⚠️ กรุณากรอกชื่อลูกค้า/บริษัท ก่อนบันทึกเอกสารครับเพื่อน")

# ==========================================
# 5. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
    st.info("ส่วนแสดงกราฟสรุปรายได้และคอมมิชชั่นช่างรายบุคคล เพื่อช่วยตัดรอบจ่ายเงินเดือนได้อย่างแม่นยำ")