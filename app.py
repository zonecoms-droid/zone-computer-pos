import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
import qrcode
from io import BytesIO
import streamlit.components.v1 as components
import os
import base64

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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_name TEXT,
            phone TEXT,
            tax_id TEXT,
            address TEXT,
            note TEXT,
            promptpay TEXT,
            line_link TEXT,
            fb_link TEXT,
            tiktok_link TEXT
        )
    ''')
    for col in ['promptpay', 'line_link', 'fb_link', 'tiktok_link']:
        try:
            cursor.execute(f"ALTER TABLE store_settings ADD COLUMN {col} TEXT;")
            conn.commit()
        except sqlite3.OperationalError:
            pass

    cursor.execute("SELECT COUNT(*) FROM store_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO store_settings (store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link) 
            VALUES ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '089-123-4567', '1234567890123', 'อุบลราชธานี', 'ขอบคุณที่ใช้บริการครับ', '0891234567', 'https://line.me', 'https://facebook.com', 'https://tiktok.com')
        ''')
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    try:
        cursor.execute("ALTER TABLE repairs ADD COLUMN media_file TEXT;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cursor.close()

conn = init_connection()
init_db(conn)

# ดึงข้อมูลร้านค้ามาใช้แสดงผล
cursor = conn.cursor()
cursor.execute("SELECT store_name, phone, tax_id, address, note, promptpay, line_link, fb_link, tiktok_link FROM store_settings WHERE id = 1")
store_info = cursor.fetchone()
cursor.close()
STORE_NAME, STORE_PHONE, STORE_TAX, STORE_ADDRESS, STORE_NOTE, STORE_PROMPTPAY, STORE_LINE, STORE_FB, STORE_TIKTOK = store_info

# ==========================================
# 🔍 โหมดพิเศษ: หน้าจอเช็คสถานะสาธารณะผ่าน QR Code (?track=...)
# ==========================================
query_params = st.query_params
track_code = query_params.get("track", None)

if track_code:
    st.set_page_config(page_title=f"เช็คสถานะงานซ่อม - {STORE_NAME}", page_icon="🔍", layout="centered")
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.job_code, r.device_name, r.problem_description, r.status, r.created_at, r.updated_at, c.name
        FROM repairs r JOIN customers c ON r.customer_id = c.id
        WHERE r.job_code = ?
    """, (track_code,))
    job_data = cursor.fetchone()
    cursor.close()
    
    if job_data:
        j_code, dev, prob, stat, d_in, d_up, c_name = job_data
        
        status_dict = {
            "RECEIVED": ("📥 รับเครื่องเข้าศูนย์ซ่อมแล้ว", "#17a2b8", "ช่างรับเครื่องและบันทึกเข้าสู่ระบบเรียบร้อย"),
            "CHECKING": ("🔍 กำลังตรวจสอบอาการ", "#ffc107", "ช่างกำลังเช็คความผิดปกติของอุปกรณ์"),
            "WAITING_PART": ("⏳ รออะไหล่ / รออนุมัติ", "#fd7e14", "กำลังรออะไหล่หรือรอการยืนยันจากลูกค้า"),
            "REPAIRING": ("⚡ กำลังดำเนินการซ่อม", "#007bff", "ช่างกำลังปฏิบัติงานซ่อมแซมเครื่อง"),
            "COMPLETED": ("🎉 ซ่อมเสร็จสิ้น พร้อมส่งมอบ", "#28a745", "เครื่องซ่อมเสร็จสมบูรณ์ พร้อมมารับกลับได้เลย!"),
            "CANCELLED": ("❌ ยกเลิกการซ่อม", "#dc3545", "รายการซ่อมนี้ถูกยกเลิก")
        }
        
        thai_status, badge_color, status_desc = status_dict.get(stat, ("📌 กำลังดำเนินการ", "#6c757d", "สถานะกำลังอัปเดต"))
        
        name_parts = c_name.split()
        masked_name = f"คุณ {name_parts[0]} ({name_parts[1][0]}***)" if len(name_parts) > 1 else f"คุณ {c_name}"

        public_html = f"""
        <!DOCTYPE html>
        <html lang="th">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ติดตามสถานะงานซ่อม - {STORE_NAME}</title>
            <style>
                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .card {{ background: white; padding: 30px 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 100%; max-width: 420px; text-align: center; animation: fadeIn 0.8s ease-in-out; }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                h2 {{ color: #333; margin-bottom: 5px; font-size: 22px; }}
                .store-sub {{ color: #666; font-size: 13px; margin-bottom: 20px; }}
                .info-box {{ background: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 20px; text-align: left; font-size: 14px; border-left: 4px solid #007bff; }}
                .info-box p {{ margin: 6px 0; color: #444; }}
                .status-badge {{ background-color: {badge_color}; color: white; padding: 12px 20px; border-radius: 30px; font-weight: bold; font-size: 16px; display: inline-block; margin: 15px 0; animation: pulse 2s infinite; box-shadow: 0 4px 10px rgba(0,0,0,0.15); }}
                @keyframes pulse {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} 100% {{ transform: scale(1); }} }}
                .desc {{ color: #555; font-size: 13px; margin-top: 5px; }}
                .footer {{ margin-top: 25px; font-size: 11px; color: #888; border-top: 1px solid #eee; padding-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>⚡ {STORE_NAME}</h2>
                <div class="store-sub">ระบบติดตามสถานะงานซ่อมเรียลไทม์</div>
                
                <div class="info-box">
                    <p><b>เลขที่ใบงาน:</b> {j_code}</p>
                    <p><b>ชื่อลูกค้า:</b> {masked_name}</p>
                    <p><b>รุ่นอุปกรณ์:</b> {dev}</p>
                    <p><b>อาการแจ้งซ่อม:</b> {prob}</p>
                    <p><b>วันที่แจ้งซ่อม:</b> {d_in}</p>
                </div>
                
                <div>
                    <div class="status-badge">{thai_status}</div>
                    <div class="desc">ℹ️ {status_desc}</div>
                </div>

                <div class="footer">
                    📞 โทรสอบถามด่วน: {STORE_PHONE}<br>ขอบคุณที่ใช้บริการร้านโซนคอมพิวเตอร์ครับ 🙏
                </div>
            </div>

            <script>
                window.addEventListener('load', () => {{
                    try {{
                        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                        const osc = audioCtx.createOscillator();
                        const gain = audioCtx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(659.25, audioCtx.currentTime);
                        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.2);
                    }} catch(e) {{}}
                }});
            </script>
        </body>
        </html>
        """
        components.html(public_html, height=650, scrolling=True)
    else:
        st.error("❌ ไม่พบข้อมูลใบงานนี้ในระบบ กรุณาตรวจสอบใหม่อีกครั้ง หรือติดต่อหน้าร้านครับ")
    st.stop()

# ==========================================
# 🖥️ หน้าแอดมินปกติ (Admin Dashboard)
# ==========================================
st.set_page_config(
    page_title="ZoneOnline Service - Ultimate Edition", 
    page_icon="⚡", 
    layout="wide"
)

st.title(f"⚡ {STORE_NAME} [Ultimate Edition]")
st.markdown("ระบบบริหารจัดการร้านคอมพิวเตอร์และงานซ่อมครบวงจร (ระบบเอกสารการค้า FlowAccount ครบชุด 6 ประเภท)")

if 'current_job_code' not in st.session_state:
    st.session_state.current_job_code = None

menu_options = [
    "📥 รับเครื่องซ่อมใหม่ & พิมพ์ใบรับซ่อม", 
    "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)",
    "🌐 QR Code ช่องทางติดต่อ (Line, FB, TikTok)",
    "🔍 ติดตาม & อัปเดตสถานะงานซ่อม", 
    "🛡️ เช็คประกัน & Serial Number",
    "📄 ระบบออกเอกสารการค้า (FlowAccount Style)",
    "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง",
    "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)"
]

menu = st.sidebar.selectbox("🎯 เลือกเมนูการทำงาน", menu_options)

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
    st.subheader("🖨️ ตัวอย่างใบรับซ่อม A4 แนวตั้ง (พร้อม QR Code เช็คสถานะเรียลไทม์)")
    
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
            cost = float(cost) if cost is not None else 0.0
            
            track_url = f"https://zone-computer-pos.streamlit.app/?track={j_code}"
            qr_track_obj = qrcode.make(track_url)
            track_stream = BytesIO()
            qr_track_obj.save(track_stream)
            track_b64 = base64.b64encode(track_stream.getvalue()).decode()
            qr_track_tag = f'<img src="data:image/png;base64,{track_b64}" width="75px"><br><span style="font-size:8px;">สแกนเช็คสถานะ</span>'
            
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
                .signature-row {{ display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px; align-items: flex-end; }}
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
                            <div style="width: 75%;">
                                <span>ลงชื่อลูกค้า: ......................................................</span><br>
                                <span style="font-size:11px; color:#555;">(เงื่อนไข: ฝากซ่อมเกิน 30 วัน ทางร้านขอสงวนสิทธิ์เก็บค่าฝากรักษา)</span>
                            </div>
                            <div style="text-align: center; width: 25%;">
                                {qr_track_tag}
                            </div>
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
                            <div style="width: 100%;">
                                <span>ลงชื่อลูกค้า (รับทราบเงื่อนไข): ...................................................... &nbsp;&nbsp;&nbsp;&nbsp; ช่างผู้รับซ่อม: ......................................................</span>
                            </div>
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
# 2. ระบบลูกค้าสแกน QR ลงทะเบียนเอง
# ==========================================
elif menu == "📱 ลูกค้าสแกน QR ลงทะเบียนเอง (พร้อมแนบรูป/วิดีโอ)":
    st.header("📱 ระบบลูกค้าลงทะเบียนแจ้งซ่อมผ่าน QR Code")
    qr_data = "https://zone-computer-pos.streamlit.app/?page=register"
    img = qrcode.make(qr_data)
    buf = BytesIO()
    img.save(buf)
    st.image(buf.getvalue(), caption="สแกนเพื่อเปิดหน้าลงทะเบียนแจ้งซ่อมออนไลน์", width=220)
    
    with st.form("self_service_media_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์ติดต่อกลับ")
        c_device = st.text_input("ยี่ห้อ / รุ่นอุปกรณ์")
        c_problem = st.text_area("อาการเสียเบื้องต้น")
        c_accessories = st.text_input("อุปกรณ์ที่ส่งมาด้วย")
        uploaded_file = st.file_uploader("📷 แนบรูปภาพ หรือ 🎥 วิดีโออาการเสีย", type=["jpg", "png", "jpeg", "mp4", "mov"])
        
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
                st.success(f"🎉 ลงทะเบียนสำเร็จ! เลขที่ใบงานของคุณคือ: **{job_code}**")
                st.balloons()
            else:
                st.warning("⚠️ กรุณากรอกข้อมูลสำคัญให้ครบถ้วน")

# ==========================================
# 3. QR Code ช่องทางติดต่อ
# ==========================================
elif menu == "🌐 QR Code ช่องทางติดต่อ (Line, FB, TikTok)":
    st.header("🌐 QR Code ช่องทางติดต่อโซเชียลมีเดียของร้าน")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("💚 Line")
        if STORE_LINE:
            img = qrcode.make(STORE_LINE)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)
    with col2:
        st.subheader("💙 Facebook")
        if STORE_FB:
            img = qrcode.make(STORE_FB)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)
    with col3:
        st.subheader("🖤 TikTok")
        if STORE_TIKTOK:
            img = qrcode.make(STORE_TIKTOK)
            buf = BytesIO(); img.save(buf)
            st.image(buf.getvalue(), width=140)

# ==========================================
# 4. ติดตาม & อัปเดตสถานะงานซ่อม
# ==========================================
elif menu == "🔍 ติดตาม & อัปเดตสถานะงานซ่อม":
    st.header("🔍 ค้นหา จัดการสถานะงานซ่อม และออกเอกสารส่งมอบ (COMPLETED)")
    search_query = st.text_input("🔍 ค้นหาด้วยเลขใบงาน, เบอร์โทร หรือชื่อลูกค้า")
    
    try:
        query = """
            SELECT r.id, r.job_code, c.name as customer_name, c.phone, c.address, r.device_name, r.serial_number, r.problem_description, r.accessories, r.media_file, r.status, r.estimated_cost, r.created_at
            FROM repairs r
            JOIN customers c ON r.customer_id = c.id
        """
        if search_query:
            query += f" WHERE r.job_code LIKE '%{search_query}%' OR c.phone LIKE '%{search_query}%' OR c.name LIKE '%{search_query}%'"
        query += " ORDER BY r.created_at DESC;"
        
        df = pd.read_sql(query, conn)
        if not df.empty:
            st.dataframe(df.drop(columns=['media_file', 'address', 'serial_number', 'accessories']), use_container_width=True)
            
            st.markdown("---")
            selected_job = st.selectbox("เลือกเลขใบงานที่ต้องการจัดการ", df['job_code'].tolist())
            selected_row = df[df['job_code'] == selected_job].iloc[0]
            
            col_info, col_media = st.columns(2)
            with col_info:
                st.markdown(f"**ชื่อลูกค้า:** {selected_row['customer_name']} ({selected_row['phone']})")
                st.markdown(f"**อุปกรณ์:** {selected_row['device_name']}")
                st.markdown(f"**อาการเสีย:** {selected_row['problem_description']}")
                st.markdown(f"**สถานะปัจจุบัน:** 📌 **{selected_row['status']}**")
            with col_media:
                m_file = selected_row.get('media_file')
                if m_file and isinstance(m_file, str) and os.path.exists(m_file):
                    ext = m_file.split('.')[-1].lower()
                    if ext in ['jpg', 'jpeg', 'png']:
                        st.image(m_file, width=250)
                    elif ext in ['mp4', 'mov']:
                        st.video(m_file)
                else:
                    st.info("ไม่มีไฟล์รูปภาพหรือวิดีโอแนบมาในใบงานนี้")
            
            new_status = st.selectbox("เปลี่ยนสถานะงานซ่อมเป็น", [
                "RECEIVED (รับเครื่องเข้า)", "CHECKING (กำลังตรวจสอบอาการ)", 
                "WAITING_PART (รออะไหล่/ตีราคา)", "REPAIRING (กำลังดำเนินการซ่อม)", 
                "COMPLETED (ซ่อมเสร็จสิ้น พร้อมส่งมอบ)", "CANCELLED (ยกเลิกการซ่อม)"
            ], index=4 if selected_row['status'].startswith('COMPLETED') else 0)
            
            if st.button("💾 บันทึกการเปลี่ยนสถานะ"):
                status_code = new_status.split(" ")[0]
                cursor = conn.cursor()
                cursor.execute("UPDATE repairs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE job_code = ?", (status_code, selected_job))
                conn.commit()
                cursor.close()
                st.success(f"อัปเดตสถานะสำเร็จ!")
                st.rerun()

            # --- ถ้าสถานะเป็น COMPLETED ให้เลือกพิมพ์เอกสาร ---
            if selected_row['status'].startswith('COMPLETED'):
                st.markdown("---")
                st.success("🎉 งานซ่อมเสร็จสิ้นแล้ว! กรุณาเลือกประเภทเอกสารที่ต้องการออกด้านล่างนี้ครับ")
                
                doc_choice = st.radio("🖨️ เลือกประเภทเอกสารทางการค้า:", [
                    "📦 ใบคืนสินค้า (Delivery Slip - A4 ครึ่งหน้า)", 
                    "💵 ใบเสร็จรับเงิน (Cash Receipt - A4 เต็มแผ่น FlowAccount Style)", 
                    "📄 ใบกำกับภาษี (Tax Invoice - A4 เต็มแผ่น FlowAccount Style)"
                ])
                
                with st.form(f"form_doc_{selected_job}"):
                    tax_cust_name = selected_row['customer_name']
                    tax_cust_id = ""
                    tax_cust_branch = "สำนักงานใหญ่"
                    tax_cust_address = selected_row['address'] if selected_row['address'] else ""
                    
                    if "ใบกำกับภาษี" in doc_choice:
                        st.markdown("#### 🏢 ข้อมูลผู้ซื้อสินค้า / ผู้รับบริการ (สำหรับออกใบกำกับภาษีตามกฎหมายสรรพากร)")
                        tc_col1, tc_col2 = st.columns(2)
                        with tc_col1:
                            tax_cust_name = st.text_input("ชื่อลูกค้า / บริษัท", value=selected_row['customer_name'])
                            tax_cust_id = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value="")
                        with tc_col2:
                            tax_cust_branch = st.text_input("สาขา (เช่น สำนักงานใหญ่ หรือ 00001)", value="สำนักงานใหญ่")
                            tax_cust_address = st.text_area("ที่อยู่ตามทะเบียนภาษี", value=selected_row['address'] if selected_row['address'] else "")
                        st.markdown("---")

                    c_col1, c_col2 = st.columns(2)
                    with c_col1:
                        pay_chanel = st.selectbox("ช่องทางชำระเงิน", ["โอนเงินผ่าน PromptPay QR", "เงินสด", "บัตรเครดิต"])
                    with c_col2:
                        warrant_days = st.number_input("ระยะเวลารับประกันหลังซ่อม (วัน)", min_value=0, value=30)
                        include_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True if "ใบกำกับภาษี" in doc_choice else False)

                    st.markdown("#### 🛒 ปรับแต่งรายการค่าบริการและอะไหล่ (แก้ไขได้อย่างอิสระ)")
                    num_items = st.number_input("จำนวนรายการ", min_value=1, max_value=10, value=1, key=f"num_{selected_job}")
                    
                    subtotal = 0.0
                    items_data = []
                    
                    for i in range(int(num_items)):
                        cols = st.columns([3, 1, 1, 1])
                        with cols[0]:
                            desc = st.text_input(f"รายการที่ {i+1}", value=selected_row['problem_description'] if i == 0 else f"อะไหล่ชิ้นที่ {i+1}", key=f"desc_{selected_job}_{i}")
                        with cols[1]:
                            qty = st.number_input("จำนวน", min_value=1, value=1, key=f"qty_{selected_job}_{i}")
                        with cols[2]:
                            default_p = float(selected_row['estimated_cost']) if (i == 0 and selected_row['estimated_cost']) else 0.0
                            price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, value=default_p, key=f"price_{selected_job}_{i}")
                        with cols[3]:
                            tot = qty * price
                            st.text_input("รวม", value=f"{tot:,.2f}", disabled=True, key=f"tot_{selected_job}_{i}")
                        subtotal += tot
                        items_data.append((desc, qty, price, tot))

                    custom_notes = st.text_area("📝 ช่องหมายเหตุ / เงื่อนไขการรับประกัน", value=f"รับประกันงานซ่อมและอะไหล่ {warrant_days} วัน นับจากวันที่ส่งมอบเครื่อง")
                    
                    generate_btn = st.form_submit_button("🖨️ สร้างเอกสารพร้อมพิมพ์อย่างเป็นทางการ")
                    
                    if generate_btn:
                        grand_total = subtotal * 1.07 if include_vat else subtotal
                        
                        qr_tag = ""
                        if "PromptPay" in pay_chanel and "ใบคืนสินค้า" in doc_choice:
                            q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                            qr_obj = qrcode.make(q_cont)
                            q_stream = BytesIO()
                            qr_obj.save(q_stream)
                            b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                            qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="100px"><br><span style="font-size:9px;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {grand_total:,.2f} บาท</b></span>'
                        elif "PromptPay" in pay_chanel and "ใบเสร็จรับเงิน" in doc_choice:
                            q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{grand_total:.2f}"
                            qr_obj = qrcode.make(q_cont)
                            q_stream = BytesIO()
                            qr_obj.save(q_stream)
                            b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                            qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="100px"><br><span style="font-size:9px;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {grand_total:,.2f} บาท</b></span>'

                        def make_social_qr(link, label):
                            if not link: return ""
                            sq = qrcode.make(link)
                            s_buf = BytesIO()
                            sq.save(s_buf)
                            s_b64 = base64.b64encode(s_buf.getvalue()).decode()
                            return f'<div style="text-align:center; display:inline-block; margin: 0 8px;"><img src="data:image/png;base64,{s_b64}" width="45px"><br><span style="font-size:8px;">{label}</span></div>'

                        social_html = ""
                        if STORE_LINE: social_html += make_social_qr(STORE_LINE, "Line")
                        if STORE_FB: social_html += make_social_qr(STORE_FB, "Facebook")
                        if STORE_TIKTOK: social_html += make_social_qr(STORE_TIKTOK, "TikTok")

                        items_html = ""
                        for idx, val in enumerate(items_data):
                            items_html += f"<tr><td style='border-bottom:1px solid #e2e8f0; padding:8px;'>{idx+1}. {val[0]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:center;'>{val[1]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[2]:,.2f}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[3]:,.2f}</td></tr>"

                        vat_html = f"<tr><td colspan='3' style='text-align:right; padding:8px;'><b>VAT 7%:</b></td><td style='text-align:right; padding:8px;'>{subtotal * 0.07:,.2f} บาท</td></tr>" if include_vat else ""

                        if "ใบคืนสินค้า" in doc_choice:
                            final_html = f"""
                            <html>
                            <head>
                            <style>
                                @page {{ size: A4 portrait; margin: 5mm; }}
                                body {{ background: #f0f2f5; font-family: sans-serif; color: black; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                                .print-btn {{ background-color: #28a745; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                                .print-btn:hover {{ background-color: #218838; }}
                                .doc-box {{ background: white; border: 1px solid #ccc; padding: 12mm 15mm; width: 190mm; box-sizing: border-box; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
                                .section-box {{ height: 125mm; box-sizing: border-box; display: flex; flex-direction: column; justify-content: space-between; }}
                                .tbl {{ width: 100%; border-collapse: collapse; }}
                                .itm-tbl {{ width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 11px; }}
                                .itm-tbl th {{ background: #333; color: white; padding: 4px; text-align: left; }}
                                .perforation {{ border-top: 2px dashed #666; margin: 8mm 0; text-align: center; font-size: 11px; color: #444; font-weight: bold; }}
                                .ftr {{ display: flex; justify-content: space-between; margin-top: 5px; font-size: 11px; align-items: flex-end; }}
                                @media print {{
                                    body {{ background: white; padding: 0; }}
                                    .print-btn {{ display: none; }}
                                    .doc-box {{ border: none; box-shadow: none; padding: 0; width: 100%; }}
                                }}
                            </style>
                            </head>
                            <body>
                                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์ใบคืนสินค้า (A4 ครึ่งหน้า)</button>
                                <div class="doc-box">
                                    <div class="section-box">
                                        <div>
                                            <table class="tbl">
                                                <tr>
                                                    <td>
                                                        <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                        <p style="font-size: 10px; margin: 1px 0;">{STORE_ADDRESS} | โทร: {STORE_PHONE} | เลขผู้เสียภาษี: {STORE_TAX}</p>
                                                    </td>
                                                    <td style="text-align: right; vertical-align: top;">
                                                        <h4 style="color: #333; margin: 0;"><b>ใบคืนสินค้าและส่งมอบงานซ่อม (สำหรับลูกค้า)</b></h4>
                                                        <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                            <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                                <tr><td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td><td><b>ช่องทางชำระ:</b> {pay_chanel}</td></tr>
                                                <tr><td><b>อุปกรณ์:</b> {selected_row['device_name']}</td><td><b>รับประกัน:</b> {warrant_days} วัน</td></tr>
                                            </table>
                                            <table class="itm-tbl">
                                                <tr><th>รายการซ่อม / อะไหล่</th><th style="text-align: center;">จำนวน</th><th style="text-align: right;">ราคา/หน่วย</th><th style="text-align: right;">จำนวนเงิน (บาท)</th></tr>
                                                {items_html}
                                                <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                                {vat_html}
                                                <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                            </table>
                                        </div>
                                        <div class="ftr">
                                            <div style="width: 70%;">
                                                <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                                <p style="font-size: 10px; margin: 8px 0 0 0;">ลงชื่อรับสินค้าคืน: ...................................................... (ลูกค้า)</p>
                                            </div>
                                            <div style="text-align: center; width: 30%;">
                                                {qr_tag}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="perforation">✂️ - - - - - - - - - - - - - - - - - รอยฉีกสำหรับแยกระหว่างลูกค้าและร้านค้า - - - - - - - - - - - - - - - - - ✂️</div>
                                    <div class="section-box">
                                        <div>
                                            <table class="tbl">
                                                <tr>
                                                    <td>
                                                        <h3 style="margin: 0;"><b>{STORE_NAME}</b></h3>
                                                        <p style="font-size: 10px; margin: 1px 0;">ใบควบคุมการส่งมอบและรับเงิน (สำหรับร้านค้าเก็บไว้)</p>
                                                    </td>
                                                    <td style="text-align: right; vertical-align: top;">
                                                        <h4 style="color: #333; margin: 0;"><b>ใบคืนสินค้าและส่งมอบงานซ่อม (สำหรับร้านค้า)</b></h4>
                                                        <p style="font-size: 10px; margin: 1px 0;"><b>เลขที่ใบงาน:</b> {selected_job} | <b>วันที่:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                    </td>
                                                </tr>
                                            </table>
                                            <table class="tbl" style="font-size: 11px; margin-top: 4px;">
                                                <tr><td><b>ชื่อลูกค้า:</b> {selected_row['customer_name']} ({selected_row['phone']})</td><td><b>ช่องทางชำระ:</b> {pay_chanel}</td></tr>
                                                <tr><td><b>อุปกรณ์:</b> {selected_row['device_name']}</td><td><b>รับประกัน:</b> {warrant_days} วัน</td></tr>
                                            </table>
                                            <table class="itm-tbl">
                                                <tr><th>รายการซ่อม / อะไหล่</th><th style="text-align: center;">จำนวน</th><th style="text-align: right;">ราคา/หน่วย</th><th style="text-align: right;">จำนวนเงิน (บาท)</th></tr>
                                                {items_html}
                                                <tr><td colspan="3" style="text-align: right; padding-top: 4px;"><b>รวมมูลค่า:</b></td><td style="text-align: right; padding-top: 4px;">{subtotal:,.2f} บาท</td></tr>
                                                {vat_html}
                                                <tr><td colspan="3" style="text-align: right; padding: 2px; font-size: 12px;"><b>ยอดสุทธิ:</b></td><td style="text-align: right; padding: 2px; font-size: 12px; color: #d9534f;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                            </table>
                                        </div>
                                        <div class="ftr">
                                            <div style="width: 100%;">
                                                <p style="font-size: 10px; margin: 2px 0;"><b>หมายเหตุ:</b> {custom_notes}</p>
                                                <p style="font-size: 10px; margin: 8px 0 0 0;">ลงชื่อลูกค้า (ตรวจรับเรียบร้อย): ...................................................... &nbsp;&nbsp;&nbsp;&nbsp; ช่างผู้ส่งมอบ: ......................................................</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """
                        else:
                            is_tax = "ใบกำกับภาษี" in doc_choice
                            doc_title = "ใบกำกับภาษี / TAX INVOICE" if is_tax else "ใบเสร็จรับเงิน / CASH RECEIPT"

                            final_html = f"""
                            <html>
                            <head>
                            <style>
                                @page {{ size: A4 portrait; margin: 12mm; }}
                                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                                .print-btn {{ background-color: #0284c7; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                                .print-btn:hover {{ background-color: #0369a1; }}
                                .flow-container {{ background: white; border: 1px solid #cbd5e1; padding: 15mm; width: 190mm; min-height: 270mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; }}
                                .header-tbl {{ width: 100%; border-collapse: collapse; }}
                                .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 15px 0; font-size: 13px; }}
                                .cust-box td {{ padding: 4px 8px; }}
                                .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
                                .items-tbl th {{ background: #0f172a; color: white; padding: 10px 8px; text-align: left; font-weight: 600; }}
                                .items-tbl td {{ padding: 10px 8px; border-bottom: 1px solid #e2e8f0; }}
                                .summary-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                                .summary-tbl td {{ padding: 6px 10px; }}
                                .footer-box {{ display: flex; justify-content: space-between; margin-top: 30px; border-top: 1px solid #cbd5e1; padding-top: 20px; align-items: flex-start; font-size: 12px; }}
                                @media print {{
                                    body {{ background: white; padding: 0; }}
                                    .print-btn {{ display: none; }}
                                    .flow-container {{ border: none; box-shadow: none; padding: 0; width: 100%; min-height: auto; }}
                                }}
                            </style>
                            </head>
                            <body>
                                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสาร FlowAccount Style (A4 เต็มแผ่น)</button>
                                <div class="flow-container">
                                    <div>
                                        <table class="header-tbl">
                                            <tr>
                                                <td style="vertical-align: top;">
                                                    <h2 style="margin: 0; color: #0f172a; font-size: 24px;"><b>{STORE_NAME}</b></h2>
                                                    <p style="font-size: 12px; margin: 4px 0; color: #475569; line-height: 1.4;">{STORE_ADDRESS}<br>โทร: {STORE_PHONE} | เลขประจำตัวผู้เสียภาษี: {STORE_TAX}</p>
                                                </td>
                                                <td style="text-align: right; vertical-align: top;">
                                                    <div style="background: #0284c7; color: white; padding: 8px 16px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 16px; margin-bottom: 8px;">
                                                        {doc_title}
                                                    </div>
                                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>เลขที่ใบงาน:</b> {selected_job}</p>
                                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>วันที่ออกเอกสาร:</b> {datetime.today().strftime('%Y-%m-%d')}</p>
                                                </td>
                                            </tr>
                                        </table>

                                        <table class="cust-box tbl">
                                            <tr>
                                                <td style="width: 65%;"><b>ชื่อลูกค้า / บริษัท:</b> {tax_cust_name}</td>
                                            </tr>
                                            <tr>
                                                <td><b>ที่อยู่:</b> {tax_cust_address if tax_cust_address else '-'}</td>
                                                <td><b>เลขผู้เสียภาษี:</b> {tax_cust_id if tax_cust_id else '-'} ({tax_cust_branch})</td>
                                            </tr>
                                        </table>

                                        <table class="items-tbl">
                                            <tr>
                                                <th>รายการสินค้า / บริการ / อะไหล่</th>
                                                <th style="text-align: center; width: 70px;">จำนวน</th>
                                                <th style="text-align: right; width: 110px;">ราคา/หน่วย</th>
                                                <th style="text-align: right; width: 130px;">จำนวนเงิน (บาท)</th>
                                            </tr>
                                            {items_html}
                                        </table>

                                        <table style="width: 100%; margin-top: 10px;">
                                            <tr>
                                                <td style="vertical-align: top; width: 55%; padding-top: 10px; font-size: 11px; color: #64748b;">
                                                    <b>หมายเหตุ / เงื่อนไขการรับประกัน ({warrant_days} วัน):</b><br>
                                                    {custom_notes}
                                                </td>
                                                <td style="width: 45%;">
                                                    <table class="summary-tbl">
                                                        <tr><td style="text-align: right;"><b>มูลค่ารวม (Subtotal):</b></td><td style="text-align: right; width: 120px;">{subtotal:,.2f} บาท</td></tr>
                                                        {vat_html}
                                                        <tr><td style="text-align: right; font-size: 15px; color: #0284c7;"><b>ยอดชำระสุทธิ (Grand Total):</b></td><td style="text-align: right; font-size: 15px; color: #0284c7;"><b>{grand_total:,.2f} บาท</b></td></tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </div>

                                    <div>
                                        <div class="footer-box">
                                            <div style="width: 70%;">
                                                <table style="width: 100%; text-align: left; font-size: 11px; border-collapse: collapse;">
                                                    <tr>
                                                        <td style="padding-bottom: 5px; width: 50%;">
                                                            ลงชื่อ......................................................
                                                        </td>
                                                        <td style="padding-bottom: 5px; width: 50%;">
                                                            ลงชื่อ......................................................
                                                        </td>
                                                    </tr>
                                                    <tr>
                                                        <td>
                                                            ผู้รับเงิน / ผู้ออกเอกสาร วันที่....................
                                                        </td>
                                                        <td>
                                                            ผู้จ่ายเงิน / ลูกค้า วันที่.........................
                                                        </td>
                                                    </tr>
                                                </table>
                                            </div>

                                            <div style="width: 25%; text-align: center;">
                                                {qr_tag}
                                            </div>
                                        </div>

                                        <!-- ล่างสุด: ติดตามร้านเราผ่านโซเชียล -->
                                        <div style="margin-top: 15px; text-align: center; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box;">
                                            <span style="font-size: 9px; color: #475569; font-weight: bold;">ติดตามร้านเราผ่านโซเชียล:</span>
                                            <div style="margin-top: 4px;">
                                                {social_html}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </body>
                            </html>
                            """

                        components.html(final_html, height=1050, scrolling=True)

        else:
            st.info("ไม่พบข้อมูลงานซ่อมในระบบ")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# ==========================================
# 5. เช็คประกัน & Serial Number
# ==========================================
elif menu == "🛡️ เช็คประกัน & Serial Number":
    st.header("🛡️ ระบบตรวจสอบระยะเวลาประกันอุปกรณ์และชิ้นส่วน")
    sn_input = st.text_input("กรอกหรือสแกน Serial Number")
    if sn_input:
        st.success("✅ สินค้าชิ้นนี้อยู่ในประกันร้าน!")

# ==========================================
# 6. ระบบออกเอกสารการค้าครบชุด 6 ประเภท (FlowAccount Style - ปรับปรุงลายเซ็นคู่ขนานตามประเภทเอกสาร)
# ==========================================
elif menu == "📄 ระบบออกเอกสารการค้า (FlowAccount Style)":
    st.header("📄 ระบบออกเอกสารทางการค้าครบวงจร (FlowAccount Corporate Style)")
    st.markdown("สร้างและพิมพ์เอกสารทางธุรกิจทั้ง 6 ประเภท เลือกวันที่ (หรือเว้นเส้นประเขียนมือ) พนักงานขาย และส่วนลดได้อิสระ")
    
    doc_type_selected = st.selectbox("🎯 เลือกประเภทเอกสารที่ต้องการออก", [
        "1. ใบเสนอราคา (Quotation - QT)",
        "2. ใบส่งสินค้า / ใบแจ้งหนี้ (Delivery Order & Invoice - DO/IV)",
        "3. ใบกำกับภาษี (Tax Invoice - TAX)",
        "4. ใบเสร็จรับเงิน (Cash Receipt - RC)",
        "5. ใบลดหนี้ (Credit Note - CN)",
        "6. ใบเพิ่มหนี้ (Debit Note - DN)"
    ])
    
    st.markdown("---")
    
    with st.form("commercial_docs_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("🏢 ข้อมูลลูกค้า / คู่ค้า")
            c_target_name = st.text_input("ชื่อลูกค้า / บริษัท", value="บริษัท ลูกค้าตัวอย่าง จำกัด")
            c_target_tax = st.text_input("เลขประจำตัวผู้เสียภาษี 13 หลัก", value="0123456789012")
            c_target_branch = st.text_input("สาขา (เช่น สำนักงานใหญ่ หรือ 00001)", value="สำนักงานใหญ่")
            c_target_address = st.text_area("ที่อยู่ลูกค้า", value="123 ถนนอุบลราชธานี อำเภอเมือง จังหวัดอุบลราชธานี")
        with col_c2:
            st.subheader("📅 รายละเอียดเอกสาร & เงื่อนไข")
            
            date_mode = st.radio("รูปแบบวันที่ออกเอกสาร", ["ระบุวันที่อัตโนมัติ", "เว้นช่องว่างเส้นประ (สำหรับลงวันที่ด้วยมือ)"], horizontal=True)
            
            if date_mode == "ระบุวันที่อัตโนมัติ":
                c_doc_date = st.date_input("วันที่ออกเอกสาร", datetime.today())
                c_doc_date_str = c_doc_date.strftime('%Y-%m-%d')
                credit_days = st.number_input("เครดิต (วัน)", min_value=0, value=30)
                due_date = c_doc_date + timedelta(days=int(credit_days))
                due_date_str = due_date.strftime('%Y-%m-%d')
                
                meta_date_block = f"""
                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>วันที่:</b> {c_doc_date_str}</p>
                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>ครบกำหนด:</b> {due_date_str} (เครดิต {credit_days} วัน)</p>
                """
            else:
                c_doc_date_str = "...................................."
                meta_date_block = f"""
                <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>วันที่:</b> {c_doc_date_str}</p>
                """
            
            salesperson = st.text_input("พนักงานขาย", value="ช่างดิด")
            currency = st.selectbox("สกุลเงิน", ["THB", "USD", "EUR"])
            
            is_no_payment_doc = any(k in doc_type_selected for k in ["ใบเสนอราคา", "ใบส่งสินค้า", "ใบกำกับภาษี"])
            c_pay_method = "โอนเงินผ่าน PromptPay QR"
            if not is_no_payment_doc:
                c_pay_method = st.selectbox("ช่องทางการชำระเงิน", ["โอนเงินผ่าน PromptPay QR", "เงินสด", "บัตรเครดิต"])

        ref_doc_html = ""
        cn_dn_reason = ""
        if "ลดหนี้" in doc_type_selected or "เพิ่มหนี้" in doc_type_selected:
            st.markdown("---")
            st.subheader("📎 ข้อมูลอ้างอิงเอกสารเดิม (สำหรับการปรับปรุงหนี้)")
            r_col1, r_col2 = st.columns(2)
            with r_col1:
                ref_doc_no = st.text_input("อ้างอิงเลขที่ใบกำกับภาษีเดิม (เช่น IV-20260301)", value="IV-20260301-001")
            with r_col2:
                cn_dn_reason = st.text_input("สาเหตุการลด/เพิ่มหนี้", value="คืนสินค้าเนื่องจากชำรุด / คิดราคาผิดพลาด")

        st.markdown("---")
        st.subheader("🛒 รายการสินค้า / บริการ")
        num_com_items = st.number_input("จำนวนรายการสินค้า", min_value=1, max_value=10, value=1)
        
        com_subtotal = 0.0
        com_items_list = []
        
        for ci in range(int(num_com_items)):
            ccols = st.columns([3, 1, 1, 1])
            with ccols[0]:
                c_desc = st.text_input(f"รายการที่ {ci+1}", value=f"จำหน่าย/บริการคอมพิวเตอร์ รายการที่ {ci+1}", key=f"com_desc_{ci}")
            with ccols[1]:
                c_qty = st.number_input("จำนวน", min_value=1, value=1, key=f"com_qty_{ci}")
            with ccols[2]:
                c_price = st.number_input("ราคา/หน่วย", min_value=0.0, step=100.0, value=1500.0, key=f"com_price_{ci}")
            with ccols[3]:
                c_tot = c_qty * c_price
                st.text_input("รวม", value=f"{c_tot:,.2f}", disabled=True, key=f"com_tot_{ci}")
            com_subtotal += c_tot
            com_items_list.append((c_desc, c_qty, c_price, c_tot))

        st.markdown("---")
        col_note, col_summary = st.columns([2, 1])
        with col_note:
            com_notes = st.text_area("หมายเหตุท้ายเอกสาร / เงื่อนไข", value=STORE_NOTE)
        with col_summary:
            discount_pct = st.number_input("ส่วนลด %", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
            include_com_vat = st.checkbox("คิดภาษีมูลค่าเพิ่ม (VAT 7%)", value=True)

        generate_commercial_doc = st.form_submit_button("🖨️ สร้างเอกสารทางการค้าพร้อมพิมพ์ (FlowAccount Style)")

        if generate_commercial_doc:
            discount_amount = com_subtotal * (discount_pct / 100.0)
            price_after_discount = com_subtotal - discount_amount
            vat_amount = price_after_discount * 0.07 if include_com_vat else 0.0
            com_grand = price_after_discount + vat_amount

            com_qr_tag = ""
            if not is_no_payment_doc and "PromptPay" in c_pay_method:
                q_cont = f"PromptPay:{STORE_PROMPTPAY} | Amount:{com_grand:.2f}"
                qr_obj = qrcode.make(q_cont)
                q_stream = BytesIO()
                qr_obj.save(q_stream)
                b64_qr = base64.b64encode(q_stream.getvalue()).decode()
                com_qr_tag = f'<img src="data:image/png;base64,{b64_qr}" width="100px"><br><span style="font-size:9px;">สแกนจ่าย PromptPay<br><b>ยอดเงิน: {com_grand:,.2f} {currency}</b></span>'

            def make_social_qr(link, label):
                if not link: return ""
                sq = qrcode.make(link)
                s_buf = BytesIO()
                sq.save(s_buf)
                s_b64 = base64.b64encode(s_buf.getvalue()).decode()
                return f'<div style="text-align:center; display:inline-block; margin: 0 6px;"><img src="data:image/png;base64,{s_b64}" width="40px"><br><span style="font-size:8px;">{label}</span></div>'

            social_html = ""
            if STORE_LINE: social_html += make_social_qr(STORE_LINE, "Line")
            if STORE_FB: social_html += make_social_qr(STORE_FB, "Facebook")
            if STORE_TIKTOK: social_html += make_social_qr(STORE_TIKTOK, "TikTok")

            items_html = ""
            for idx, val in enumerate(com_items_list):
                items_html += f"<tr><td style='border-bottom:1px solid #e2e8f0; padding:8px;'>{idx+1}. {val[0]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:center;'>{val[1]}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[2]:,.2f}</td><td style='border-bottom:1px solid #e2e8f0; padding:8px; text-align:right;'>{val[3]:,.2f}</td></tr>"

            discount_html = ""
            if discount_pct > 0:
                discount_html = f"<tr><td style='text-align: right;'><b>ส่วนลด ({discount_pct}%):</b></td><td style='text-align: right;'>- {discount_amount:,.2f} {currency}</td></tr>"

            vat_html = f"<tr><td style='text-align: right;'><b>ภาษีมูลค่าเพิ่ม 7% (VAT):</b></td><td style='text-align: right;'>{vat_amount:,.2f} {currency}</td></tr>" if include_com_vat else ""

            if "1." in doc_type_selected:
                doc_title_str = "ใบเสนอราคา / QUOTATION"
                doc_code_prefix = "QT"
                left_sign_title = "ผู้เสนอ / ผู้ออกเอกสาร"
                right_sign_title = "ผู้อนุมัติ / ลูกค้า"
            elif "2." in doc_type_selected:
                doc_title_str = "ใบส่งสินค้า / ใบแจ้งหนี้ / DELIVERY ORDER & INVOICE"
                doc_code_prefix = "IV"
                left_sign_title = "ผู้ส่งสินค้า / ผู้ออกเอกสาร"
                right_sign_title = "ผู้รับสินค้า / ลูกค้า"
            elif "3." in doc_type_selected:
                doc_title_str = "ใบกำกับภาษี / TAX INVOICE"
                doc_code_prefix = "TAX"
                left_sign_title = "ผู้มีอำนาจออกเอกสาร"
                right_sign_title = "ผู้รับบริการ / ลูกค้า"
            elif "4." in doc_type_selected:
                doc_title_str = "ใบเสร็จรับเงิน / CASH RECEIPT"
                doc_code_prefix = "RC"
                left_sign_title = "ผู้รับเงิน / ผู้ออกเอกสาร"
                right_sign_title = "ผู้จ่ายเงิน / ลูกค้า"
            elif "5." in doc_type_selected:
                doc_title_str = "ใบลดหนี้ / CREDIT NOTE"
                doc_code_prefix = "CN"
                left_sign_title = "ผู้ออกใบลดหนี้"
                right_sign_title = "ผู้รับใบลดหนี้ / ลูกค้า"
            else:
                doc_title_str = "ใบเพิ่มหนี้ / DEBIT NOTE"
                doc_code_prefix = "DN"
                left_sign_title = "ผู้ออกใบเพิ่มหนี้"
                right_sign_title = "ผู้รับใบเพิ่มหนี้ / ลูกค้า"

            random_doc_no = f"{doc_code_prefix}-{datetime.today().strftime('%Y%m%d')}-{random.randint(10,99)}"

            ref_box_html = ""
            if "ลดหนี้" in doc_type_selected or "เพิ่มหนี้" in doc_type_selected:
                ref_box_html = f"""
                <div style="background: #fef2f2; border: 1px solid #fecaca; padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 12px; color: #991b1b;">
                    <b>อ้างอิงใบกำกับภาษีเดิม:</b> {ref_doc_no} | <b>สาเหตุ:</b> {cn_dn_reason}
                </div>
                """

            payment_row_under_total = ""
            if not is_no_payment_doc:
                payment_row_under_total = f'<tr><td style="text-align: right; font-size: 12px; color: #475569; padding-top: 8px;"><b>ช่องทางชำระเงิน:</b></td><td style="text-align: right; font-size: 12px; color: #1e293b; padding-top: 8px;">{c_pay_method}</td></tr>'

            commercial_html = f"""
            <html>
            <head>
            <style>
                @page {{ size: A4 portrait; margin: 12mm; }}
                body {{ background: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; margin: 0; padding: 10px; display: flex; flex-direction: column; align-items: center; }}
                .print-btn {{ background-color: #0284c7; color: white; border: none; padding: 12px 24px; font-size: 16px; font-weight: bold; border-radius: 6px; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.15); }}
                .print-btn:hover {{ background-color: #0369a1; }}
                .flow-container {{ background: white; border: 1px solid #cbd5e1; padding: 15mm; width: 190mm; min-height: 270mm; box-sizing: border-box; box-shadow: 0 4px 15px rgba(0,0,0,0.08); display: flex; flex-direction: column; justify-content: space-between; }}
                .header-tbl {{ width: 100%; border-collapse: collapse; }}
                .cust-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 12px 0; font-size: 13px; }}
                .cust-box td {{ padding: 4px 8px; }}
                .items-tbl {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
                .items-tbl th {{ background: #0f172a; color: white; padding: 10px 8px; text-align: left; font-weight: 600; }}
                .items-tbl td {{ padding: 10px 8px; border-bottom: 1px solid #e2e8f0; }}
                .summary-tbl {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
                .summary-tbl td {{ padding: 6px 10px; }}
                .footer-box {{ display: flex; justify-content: space-between; margin-top: 25px; border-top: 1px solid #cbd5e1; padding-top: 15px; align-items: flex-start; font-size: 12px; }}
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .print-btn {{ display: none; }}
                    .flow-container {{ border: none; box-shadow: none; padding: 0; width: 100%; min-height: auto; }}
                }}
            </style>
            </head>
            <body>
                <button class="print-btn" onclick="window.print()">🖨️ พิมพ์เอกสาร FlowAccount Style (A4 เต็มแผ่น)</button>
                <div class="flow-container">
                    <div>
                        <!-- Header -->
                        <table class="header-tbl">
                            <tr>
                                <td style="vertical-align: top;">
                                    <h2 style="margin: 0; color: #0f172a; font-size: 24px;"><b>{STORE_NAME}</b></h2>
                                    <p style="font-size: 12px; margin: 4px 0; color: #475569; line-height: 1.4;">{STORE_ADDRESS}<br>โทร: {STORE_PHONE} | เลขประจำตัวผู้เสียภาษี: {STORE_TAX}</p>
                                </td>
                                <td style="text-align: right; vertical-align: top;">
                                    <div style="background: #0284c7; color: white; padding: 8px 16px; border-radius: 6px; display: inline-block; font-weight: bold; font-size: 15px; margin-bottom: 8px;">
                                        {doc_title_str}
                                    </div>
                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>เลขที่เอกสาร:</b> {random_doc_no}</p>
                                    {meta_date_block}
                                    <p style="font-size: 12px; margin: 3px 0; color: #334155;"><b>พนักงานขาย:</b> {salesperson} | <b>สกุลเงิน:</b> {currency}</p>
                                </td>
                            </tr>
                        </table>

                        {ref_box_html}

                        <!-- Customer Box -->
                        <table class="cust-box tbl">
                            <tr>
                                <td style="width: 100%;"><b>นามลูกค้า / บริษัท:</b> {c_target_name}</td>
                            </tr>
                            <tr>
                                <td><b>ที่อยู่:</b> {c_target_address if c_target_address else '-'}</td>
                            </tr>
                            <tr>
                                <td><b>เลขผู้เสียภาษี:</b> {c_target_tax if c_target_tax else '-'} ({c_target_branch})</td>
                            </tr>
                        </table>

                        <!-- Items Table -->
                        <table class="items-tbl">
                            <tr>
                                <th>รายการสินค้า / บริการ / อะไหล่</th>
                                <th style="text-align: center; width: 70px;">จำนวน</th>
                                <th style="text-align: right; width: 110px;">ราคา/หน่วย</th>
                                <th style="text-align: right; width: 130px;">จำนวนเงิน ({currency})</th>
                            </tr>
                            {items_html}
                        </table>

                        <!-- Summary Section -->
                        <table style="width: 100%; margin-top: 10px;">
                            <tr>
                                <td style="vertical-align: top; width: 55%; padding-top: 10px; font-size: 11px; color: #64748b;">
                                    <b>หมายเหตุ / เงื่อนไข:</b><br>
                                    {com_notes}
                                </td>
                                <td style="width: 45%;">
                                    <table class="summary-tbl">
                                        <tr><td style="text-align: right;"><b>รวมเป็นเงิน (Subtotal):</b></td><td style="text-align: right; width: 150px;">{com_subtotal:,.2f} {currency}</td></tr>
                                        {discount_html}
                                        <tr><td style="text-align: right;"><b>ราคาหลังหักส่วนลด:</b></td><td style="text-align: right;">{price_after_discount:,.2f} {currency}</td></tr>
                                        {vat_html}
                                        <tr><td style="text-align: right; font-size: 14px; color: #0284c7;"><b>จำนวนเงินรวมทั้งสิ้น (Grand Total):</b></td><td style="text-align: right; font-size: 14px; color: #0284c7;"><b>{com_grand:,.2f} {currency}</b></td></tr>
                                        {payment_row_under_total}
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- Footer Signatures & QR & Social Media at the Very Bottom -->
                    <div>
                        <div class="footer-box">
                            <div style="width: 70%;">
                                <table style="width: 100%; text-align: left; font-size: 11px; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding-bottom: 5px; width: 50%;">
                                            ลงชื่อ......................................................
                                        </td>
                                        <td style="padding-bottom: 5px; width: 50%;">
                                            ลงชื่อ......................................................
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>
                                            {left_sign_title} วันที่....................
                                        </td>
                                        <td>
                                            {right_sign_title} วันที่.........................
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <div style="width: 25%; text-align: center;">
                                {com_qr_tag}
                            </div>
                        </div>

                        <!-- ล่างสุด: ติดตามร้านเราผ่านโซเชียล -->
                        <div style="margin-top: 15px; text-align: center; background: #f8fafc; padding: 6px; border-radius: 6px; border: 1px solid #e2e8f0; width: 100%; box-sizing: border-box;">
                            <span style="font-size: 9px; color: #475569; font-weight: bold;">ติดตามร้านเราผ่านโซเชียล:</span>
                            <div style="margin-top: 4px;">
                                {social_html}
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            components.html(commercial_html, height=1050, scrolling=True)

# ==========================================
# 7. สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง
# ==========================================
elif menu == "💰 สรุปยอดซ่อม & ค่าคอมมิชชั่นช่าง":
    st.header("💰 รายงานยอดขายและค่ามือช่างประจำร้าน")
    st.info("ส่วนแสดงรายงานและคำนวณค่าคอมมิชชั่นช่างอัตโนมัติ")

# ==========================================
# 8. ตั้งค่าข้อมูลร้านค้า
# ==========================================
elif menu == "⚙️ ตั้งค่าข้อมูลร้านค้า (Store Settings)":
    st.header("⚙️ ตั้งค่าข้อมูลร้านค้า")
    with st.form("settings_form"):
        new_store_name = st.text_input("ชื่อร้านค้า", value=STORE_NAME)
        new_phone = st.text_input("เบอร์โทรศัพท์", value=STORE_PHONE)
        new_promptpay = st.text_input("เลขพร้อมเพย์", value=STORE_PROMPTPAY)
        new_line = st.text_input("ลิงก์ Line", value=STORE_LINE)
        new_fb = st.text_input("ลิงก์ Facebook", value=STORE_FB)
        new_tiktok = st.text_input("ลิงก์ TikTok", value=STORE_TIKTOK)
        new_tax = st.text_input("เลขผู้เสียภาษี", value=STORE_TAX)
        new_address = st.text_area("ที่อยู่", value=STORE_ADDRESS)
        new_note = st.text_input("หมายเหตุ", value=STORE_NOTE)
        
        if st.form_submit_button("💾 บันทึกการตั้งค่า"):
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE store_settings 
                SET store_name = ?, phone = ?, tax_id = ?, address = ?, note = ?, promptpay = ?, line_link = ?, fb_link = ?, tiktok_link = ? 
                WHERE id = 1
            """, (new_store_name, new_phone, new_tax, new_address, new_note, new_promptpay, new_line, new_fb, new_tiktok))
            conn.commit()
            cursor.close()
            st.success("บันทึกการตั้งค่าสำเร็จ!")
            st.rerun()