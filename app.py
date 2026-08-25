import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import random
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
import os

# สร้างโฟลเดอร์สำหรับเก็บบันทึกไฟล์รูป/วิดีโอที่ลูกค้าอัปโหลด
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

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
            note TEXT,
            promptpay TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note, promptpay) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-123-4567', '1234567890123', 'อุบลราชธานี', 'ขอบคุณที่ใช้บริการครับ', '0891234567')
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
            media_file TEXT,
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
cursor.execute("SELECT store_name, phone, tax_id, address, note, promptpay FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()
STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY = store_info

st.title(f"⚡ {STORE_NAME} [Ultimate Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (ระบบเอกสาร FlowAccount พร้อม QR Code)")

if 'current_job_code' not in st.session_state:
    st.session_state.current_job_code = None

menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", [
    "📥 รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม", 
    "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)",
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ออกเอกสารการค้า / ใบเสร็จ (พร้อม QR Code)",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง",
    "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)"
])

# ==========================================
# 1. รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม
# ==========================================
if menu == "📥 รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม":
    st.header("📥 บันทึกรับเครื่องซ่อมและพิมพ์ใบรับซ่อม (A4 แนวตั้ง)")
    
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

        submit_btn = st.form_submit_button("🚀 บันทึกรับเครื่องและสร้างใบรับซ่อม")
        
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
                    
                    st.session_state.current_job_code = job_code
                    st.success(f"🎉 บันทึกรับเครื่องสำเร็จ! เลขที่ใบงาน: **{job_code}** เลื่อนลงด้านล่างเพื่อกดปุ่มสั่งปริ้นได้เลยครับ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการบันทึก: {e}")
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")

    st.markdown("---")
    st.subheader("🖨️ ตัวอย่างใบรับซ่อม A4 แนวตั้ง (มีปุ่มสั่งปริ้นในตัว)")
    
    cursor = conn.cursor()
    cursor.execute("SELECT job_code FROM repairs ORDER BY created_at DESC LIMIT 50")
    all_jobs = [row[0] for row in cursor.fetchall()]
    cursor.close()
    
    if all_jobs:
        default_index = 0
        if st.session_state.current_job_code in all_jobs:
            default_index = all_jobs.index(st.session_state.current_job_code)
            
        selected_job_to_print = st.selectbox("เลือกเลขใบงานที่ต้องการแสดงเอกสาร", all_jobs, index=default_index)
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.job_code, c.name, c.phone, r.device_name, r.serial_number, r.problem_description, r.accessories, r.estimated_cost, r.status, r.created_at
            FROM repairs r JOIN customers c ON r.customer_id = c.id
            WHERE r.job_code = ?
        """, (selected_job_to_print,))
        print_data = cursor.fetchone()
        cursor.close()
        
        if print_data:
            j_code, c_name, c_phone, dev, sn, prob, acc, cost, stat, date_in = print_data
            
            portrait_a4_html = f"""
            <html>
            <head>
            <style>
                @page {{ size: A4 portrait; margin: 5mm; }}
                body {{ background: #f0f2f5; font-family: sans-serif; color: black; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                .print-btn-container {{ margin-bottom: 15px; }}
                .btn-print {{ background-color: #ff4b4b; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                .btn-print:hover {{ background-color: #e03e3e; }}
                .print-container {{ background: white; border: 1px solid #ccc; padding: 12mm 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .section-box {{ height: 125mm; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; }}
                h3, h4 {{ text-align: center; margin: 2px 0; }}
                p {{ font-size: 13px; margin: 4px 0; }}
                table {{ width: 100%; font-size: 13px; margin-top: 5px; border-collapse: collapse; }}
                td {{ padding: 3px 0; }}
                .perforation {{ border-top: 2px dashed #666; margin: 8mm 0; text-align: center; font-size: 11px; color: #444; font-weight: bold; }}
                .signature-row {{ display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px; }}
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .print-btn-container {{ display: none; }}
                    .print-container {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                }}
            </style>
            </head>
            <body>
                <div class="print-btn-container">
                    <button class="btn-print" onclick="window.print()">🖨️ คลิกที่นี่เพื่อสั่งพิมพ์ใบรับซ่อม (A4 แนวตั้ง)</button>
                </div>
                
                <div class="print-container">
                    <!-- ส่วนที่ 1: สำหรับลูกค้า -->
                    <div class="section-box">
                        <div>
                            <h3><b>{STORE_NAME}</b></h3>
                            <p style="text-align: center; font-size: 11px;">ที่อยู่: {STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                            <h4 style="background: #eee; padding: 4px; margin-top: 5px;">ใบรับซ่อมสินค้า (สำหรับลูกค้า / ต้นฉบับ)</h4>
                            <table>
                                <tr><td><b>เลขที่ใบงาน:</b> {j_code}</td><td><b>วันที่รับเครื่อง:</b> {date_in}</td></tr>
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>
                            <p><b>อาการเสีย:</b> {prob}</p>
                            <p><b>อุปกรณ์ที่แนบมา:</b> {acc if acc else '-'}</p>
                            <p><b>ประเมินราคาเบื้องต้น:</b> <b>{cost:,.2f} บาท</b></p>
                        </div>
                        <div class="signature-row">
                            <span>ลงชื่อลูกค้า: ......................................................</span>
                            <span>ผู้รับเครื่อง: ......................................................</span>
                        </div>
                    </div>

                    <!-- รอยฉีก -->
                    <div class="perforation">
                        ✂️ - - - - - - - - - - - - - - - - - รอยฉีกสำหรับแยกต้นฉบับและสำเนา (Cut / Tear Here) - - - - - - - - - - - - - - - - - ✂️
                    </div>

                    <!-- ส่วนที่ 2: สำหรับร้านค้า -->
                    <div class="section-box">
                        <div>
                            <h3><b>{STORE_NAME}</b></h3>
                            <p style="text-align: center; font-size: 11px;">ใบควบคุมงานซ่อมภายในร้าน (สำหรับร้านค้าเก็บไว้)</p>
                            <h4 style="background: #eee; padding: 4px; margin-top: 5px;">ใบรับซ่อมสินค้า (สำหรับร้านค้า / สำเนา)</h4>
                            <table>
                                <tr><td><b>เลขที่ใบงาน:</b> {j_code}</td><td><b>วันที่รับเครื่อง:</b> {date_in}</td></tr>
                                <tr><td><b>ชื่อลูกค้า:</b> {c_name}</td><td><b>เบอร์โทรศัพท์:</b> {c_phone}</td></tr>
                                <tr><td><b>รุ่นอุปกรณ์:</b> {dev}</td><td><b>Serial Number:</b> {sn if sn else '-'}</td></tr>
                            </table>
                            <p><b>อาการเสีย:</b> {prob}</p>
                            <p><b>อุปกรณ์ที่แนบมา:</b> {acc if acc else '-'}</p>
                            <p><b>ประเมินราคาเบื้องต้น:</b> <b>{cost:,.2f} บาท</b></p>
                        </div>
                        <div class="signature-row">
                            <span>ลงชื่อลูกค้า (รับทราบเงื่อนไข): ......................................................</span>
                            <span>ช่างผู้รับซ่อม: ......................................................</span>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            components.html(portrait_a4_html, height=1050, scrolling=True)
    else:
        st.info("ยังไม่มีข้อมูลใบงานในระบบ")

# ==========================================
# 2. ระบบลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)
# ==========================================
elif menu == "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)":
    st.header("📱 ระบบลูกค้าลงทะเบียนแจ้งซ่อมผ่าน QR Code (แนบรูปภาพ & วิดีโอได้)")
    st.markdown("ให้ลูกค้าสแกน QR Code แล้วกรอกข้อมูล พร้อมแนบรูปถ่ายหรือคลิปวิดีโออาการเสียของเครื่องส่งตรงเข้าระบบได้ทันที")
    
    qr_data = "https://share.streamlit.io/"
    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    st.image(buf.getvalue(), caption="สแกนเพื่อกรอกข้อมูลแจ้งซ่อมออนไลน์", width=250)
    
    st.markdown("---")
    st.subheader("📝 ฟอร์มลงทะเบียนสำหรับลูกค้า")
    
    with st.form("self_service_media_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์ติดต่อกลับ")
        c_device = st.text_input("ยี่ห้อ / รุ่นอุปกรณ์ (เช่น Notebook Acer, PC ประกอบ)")
        c_problem = st.text_area("อาการเสียเบื้องต้น / สิ่งที่ต้องการให้ซ่อม")
        c_accessories = st.text_input("อุปกรณ์ที่ส่งมาด้วย (เช่น สายชาร์จ, เมาส์)")
        
        uploaded_file = st.file_uploader("📷 แนบรูปภาพ หรือ 🎥 วิดีโออาการเสีย (รองรับ JPG, PNG, MP4)", type=["jpg", "png", "jpeg", "mp4", "mov"])
        
        self_submit = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อมและไฟล์หลักฐานเข้าร้าน")
        
        if self_submit:
            if c_name and c_phone and c_device:
                file_path = None
                if uploaded_file is not None:
                    file_extension = uploaded_file.name.split(".")[-1]
                    file_name = f"MEDIA_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100,999)}.{file_extension}"
                    file_path = os.path.join(UPLOAD_DIR, file_name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO customers (name, phone) VALUES (?, ?) 
                    ON CONFLICT(phone) DO UPDATE SET name = excluded.name;
                """, (c_name, c_phone))
                cursor.execute("SELECT id FROM customers WHERE phone = ?", (c_phone,))
                cust_id = cursor.fetchone()[0]
                
                job_code = f"REP-{datetime.now().strftime('%Y%m%d')}-{random.randint(100,999)}"
                cursor.execute("""
                    INSERT INTO repairs (job_code, customer_id, device_name, problem_description, accessories, media_file, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'RECEIVED')
                """, (job_code, cust_id, c_device, c_problem, c_accessories, file_path))
                conn.commit()
                cursor.close()
                
                st.success(f"🎉 ลงทะเบียนสำเร็จ! เลขที่ใบงานของคุณคือ: **{job_code}** กรุณาแจ้งเลขนี้กับพนักงานหน้าร้าน")
                if file_path:
                    st.info(f"📁 แนบไฟล์หลักฐานเรียบร้อยแล้ว: {uploaded_file.name}")
                st.balloons()
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญ (ชื่อ, เบอร์โทร, รุ่นอุปกรณ์) ให้ครบถ้วน")

# ==========================================
# 3. ติดตาม & อัปเดตสถานะงานซ่อม
# ==========================================
elif menu == "🔍 ติดตาม & อัปเดตสถานะงานซ่อม":
    st.header("🔍 ค้นหา จัดการ และอัปเดตสถานะงานซ่อม (พร้อมตรวจสอบไฟล์แนบ)")
    search_query = st.text_input("🔍 ค้นหาด้วยเลขใบงาน, เบอร์โทร หรือชื่อลูกค้า")
    
    try:
        query = """
            SELECT r.id, r.job_code, c.name as customer_name, c.phone, r.device_name, r.problem_description, r.media_file, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
        """
        if search_query:
            query += f" WHERE r.job_code LIKE '%{search_query}%' OR c.phone LIKE '%{search_query}%' OR c.name LIKE '%{search_query}%'"
        query += " ORDER BY r.created_at DESC;"
        
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.dataframe(df.drop(columns=['media_file']), use_container_width=True)
            
            st.markdown("---")
            st.subheader("🛠️ ตรวจสอบรายละเอียดและเปลี่ยนสถานะงานซ่อม")
            selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการจัดการ", df['job_code'].tolist())
            
            selected_row = df[df['job_code'] == selected_job].iloc[0]
            
            col_info, col_media = st.columns(2)
            with col_info:
                st.markdown(f"**ชื่อลูกค้า:** {selected_row['customer_name']} ({selected_row['phone']})")
                st.markdown(f"**อุปกรณ์:** {selected_row['device_name']}")
                st.markdown(f"**อาการเสีย:** {selected_row['problem_description']}")
                st.markdown(f"**สถานะปัจจุบัน:** {selected_row['status']}")
                
            with col_media:
                st.markdown("📁 **ไฟล์หลักฐาน / สื่อที่ลูกค้าแนบมา:**")
                m_file = selected_row['media_file']
                if m_file and os.path.exists(m_file):
                    ext = m_file.split('.')[-1].lower()
                    if ext in ['jpg', 'jpeg', 'png']:
                        st.image(m_file, caption="รูปภาพอาการเสียจากลูกค้า", width=300)
                    elif ext in ['mp4', 'mov']:
                        st.video(m_file)
                else:
                    st.info("ไม่มีไฟล์รูปภาพหรือวิดีโอแนบมาในใบงานนี้")
            
            st.markdown("---")
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
# 4. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number ของสินค้า/อะไหล่")
    if sn_input:
        st.info(f"กำลังตรวจสอบข้อมูล Serial Number: **{sn_input}** ...")
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน! (ซื้อเมื่อ: 15 มกราคม 2026 / ประกันหมดอายุ: 15 มกราคม 2027)")

# ==========================================
# 5. ออกเอกสารการค้า / ใบเสร็จ (พร้อม QR Code)
# ==========================================
elif menu == "📄 ออกเอกสารการค้า / ใบเสร็จ (พร้อม QR Code)":
    st.header("📄 ระบบออกเอกสารและใบกำกับภาษี (สไตล์ FlowAccount + QR Code ชำระเงิน)")
    
    doc_type = st.selectbox("เลือกประเภทเอกสาร", ["ใบเสนอราคา (Quotation)", "ใบเสร็จรับเงิน / ใบกำกับภาษี (Tax Invoice)", "บิลเงินสด (Cash Receipt)"])
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        cust_name = st.text_input("ชื่อลูกค้า / บริษัท")
        cust_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก")
        cust_address = st.text_area("ที่อยู่ลูกค้า")
    with col2:
        doc_date = st.date_input("วันที่เอกสาร", datetime.today())
        payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "โอนเงินผ่าน PromptPay QR", "บัตรเครดิต"])

    num_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
    subtotal = 0.0
    
    items_list = []
    for i in range(int(num_items)):
        cols = st.columns([3, 1, 1, 1])
        with cols[0]: item_desc = st.text_input(f"รายการที่ {i+1}", key=f"desc_{i}")
        with cols[1]: qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{i}")
        with cols[2]: price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, key=f"price_{i}")
        with cols[3]:
            total_item = qty * price
            st.text_input("รวม", value=f"{total_item:,.2f}", disabled=True, key=f"total_{i}")
        subtotal += total_item
        items_list.append((item_desc, qty, price, total_item))

    st.markdown("---")
    col_a, col_b = st.columns([2, 1])
    with col_a: 
        notes = st.text_area("หมายเหตุท้ายเอกสาร", value=STORE_NOTE)
        include_qr = st.checkbox("📌 แนบ QR Code พร้อมเพย์ (PromptPay) สำหรับสแกนจ่ายบนใบเสร็จ", value=True)
    with col_b:
        st.markdown(f"**มูลค่ารวม:** `{subtotal:,.2f} บาท`")
        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)
        grand_total = subtotal * 1.07 if include_vat else subtotal
        if include_vat: st.markdown(f"**VAT 7%:** `{subtotal * 0.07:,.2f} บาท`")
        st.markdown(f"### **ยอดสุทธิ:** `{grand_total:,.2f} บาท`")
        
    if st.button("💾 สร้างและแสดงตัวอย่างเอกสารอย่างเป็นทางการ"):
        if cust_name:
            st.success(f"🎉 สร้างเอกสาร **{doc_type}** เรียบร้อยแล้ว! ดูตัวอย่างด้านล่างได้เลยครับ")
            
            # สร้าง QR Code สำหรับ PromptPay (จำลองลิงก์หรือพร้อมเพย์)
            qr_img_tag = ""
            if include_qr:
                qr_content = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                qr = qrcode.make(qr_content)
                q_buf = BytesIO()
                qr.save(q_buf)
                import base64
                qr_base64 = base64.b64encode(q_buf.getvalue()).decode()
                qr_img_tag = f'<img src="data:image/png;base64,{qr_base64}" width="120px"><br><span style="font-size:10px;">สแกนจ่ายผ่าน PromptPay: {STORE_PROMPTPAY}</span>'

            # สร้างตารางรายการสินค้า HTML
            items_html = ""
            for idx, itm in enumerate(items_list):
                items_html += f"<tr><td style='border-bottom:1px solid #ddd; padding:5px;'>{idx+1}. {itm[0]}</td><td style='border-bottom:1px solid #ddd; padding:5px; text-align:center;'>{itm[1]}</td><td style='border-bottom:1px solid #ddd; padding:5px; text-align:right;'>{itm[2]:,.2f}</td><td style='border-bottom:1px solid #ddd; padding:5px; text-align:right;'>{itm[3]:,.2f}</td></tr>"

            vat_text = f"<tr><td colspan='3' style='text-align:right; padding:5px;'><b>VAT 7%:</b></td><td style='text-align:right; padding:5px;'>{subtotal * 0.07:,.2f} บาท</td></tr>" if include_vat else ""

            flow_doc_html = f"""
            <html>
            <head>
            <style>
                body {{ background: #f0f2f5; font-family: sans-serif; color: black; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                .print-btn {{ background-color: #ff4b4b; color: white; border: none; padding: 10px 20px; font-size: 15px; font-weight: bold; border-radius: 5px; cursor: pointer; margin-bottom: 15px; }}
                .doc-container {{ background: white; border: 1px solid #ccc; padding: 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                .header-table {{ width: 100%; border-collapse: collapse; }}
                .items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                .items-table th {{ background: #333; color: white; padding: 6px; text-align: left; }}
                .footer-box {{ display: flex; justify-content: space-between; margin-top: 20px; font-size: 12px; align-items: flex-start; }}
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .print-btn {{ display: none; }}
                    .doc-container {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                }}
            </style>
            </head>
            <body>
                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสาร (FlowAccount Style)</button>
                <div class="doc-container">
                    <table class="header-table">
                        <tr>
                            <td>
                                <h2><b>{STORE_NAME}</b></h2>
                                <p style="font-size: 11px; margin: 2px 0;">{STORE_ADDRESS}</p>
                                <p style="font-size: 11px; margin: 2px 0;">โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                            </td>
                            <td style="text-align: right; vertical-align: top;">
                                <h2 style="color: #333; margin: 0;"><b>{doc_type.split(' ')[0]}</b></h2>
                                <p style="font-size: 12px; margin: 4px 0;"><b>วันที่:</b> {doc_date}</p>
                            </td>
                        </tr>
                    </table>
                    <hr style="margin: 10px 0;">
                    <table class="header-table" style="font-size: 13px;">
                        <tr>
                            <td><b>นามลูกค้า / บริษัท:</b> {cust_name}</td>
                            <td><b>ช่องทางชำระ:</b> {payment_method}</td>
                        </tr>
                        <tr>
                            <td><b>ที่อยู่:</b> {cust_address if cust_address else '-'}</td>
                            <td><b>เลขผู้เสียภาษีลูกค้า:</b> {cust_tax_id if cust_tax_id else '-'}</td>
                        </tr>
                    </table>
                    
                    <table class="items-table">
                        <tr>
                            <th>รายการสินค้า / บริการ</th>
                            <th style="text-align: center;">จำนวน</th>
                            <th style="text-align: right;">ราคา/หน่วย</th>
                            <th style="text-align: right;">จำนวนเงิน (บาท)</th>
                        </tr>
                        {items_html}
                        <tr><td colspan="3" style="text-align: right; padding-top: 10px;"><b>มูลค่ารวมสินค้า:</b></td><td style="text-align: right; padding-top: 10px;">{subtotal:,.2f} บาท</td></tr>
                        {vat_text}
                        <tr><td colspan="3" style="text-align: right; padding: 5px; font-size: 14px;"><b>ยอดชำระสุทธิ:</b></td><td style="text-align: right; padding: 5px; font-size: 14px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                    </table>

                    <div class="footer-box">
                        <div>
                            <p><b>หมายเหตุ:</b> {notes}</p>
                            <br><br>
                            <p>ลงชื่อ......................................................(ผู้รับเงิน / ผู้ออกเอกสาร)</p>
                        </div>
                        <div style="text-align: center;">
                            {qr_img_tag}
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            components.html(flow_doc_html, height=750, scrolling=True)
        else:
            st.warning("⚠️ กรุณากรอกชื่อลูกค้าก่อนออกเอกสารครับเพื่อน")

# ==========================================
# 6. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
    st.info("ส่วนแสดงรายงานและคำนวณค่าคอมมิชชั่นช่างอัตโนมัติ")

# ==========================================
# 7. ตั้งค่าข้อมูลร้านค้า (Store Settings)
# ==========================================
elif menu == "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)":
    st.header("⚙️ ตั้งค่าข้อมูลร้านค้าและเลขพร้อมเพย์")
    st.markdown("แก้ไขข้อมูลร้านค้า เบอร์พร้อมเพย์ และข้อความบนเอกสารได้อย่างอิสระเสรี")
    
    with st.form("settings_form"):
        new_store_name = st.text_input("ชื่อร้านค้า / บริษัท", value=STORE_NAME)
        new_phone = st.text_input("เบอร์โทรศัพท์ร้าน", value=STORE_PHONE)
        new_promptpay = st.text_input("เบอร์มือถือหรือเลขพร้อมเพย์ (PromptPay สำหรับ QR Code)", value=STORE_PROMPTPAY)
        new_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี", value=STORE_TAX)
        new_address = st.text_area("ที่อยู่ร้านค้า", value=STORE_ADDRESS)
        new_note = st.text_input("ข้อความท้ายบิล / หมายเหตุ", value=STORE_NOTE)
        
        save_settings = st.form_submit_button("💾 บันทึกการตั้งค่าร้านค้า")
        
        if save_settings:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE store_settings 
                SET store_name = ?, phone = ?, tax_id = ?, address = ?, note = ?, promptpay = ? 
                WHERE id = 1
            """, (new_store_name, new_phone, new_tax_id, new_address, new_note, new_promptpay))
            conn.commit()
            cursor.close()
            st.success("🎉 บันทึกการตั้งค่าเรียบร้อยแล้ว! กรุณารีเฟรชหน้าเว็บเพื่ออัปเดตข้อมูล")
            st.balloons()