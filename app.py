import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import base64
from io import BytesIO

# พยายามโหลด qrcode ถ้าไม่มีให้ข้ามเพื่อป้องกันหน้าขาว
try:
    import qrcode
    HAS_QR = True
except ImportError:
    HAS_QR = False

st.set_page_config(
    page_title="ServiceTicker Pro - Enterprise Edition",
    layout="wide",
    page_icon="💻"
)

# --- CSS สำหรับจัดการการพิมพ์ ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }
    @media print {
        header, footer, [data-testid="stSidebar"], .stButton, .stSelectbox, .stRadio, .no-print {
            display: none !important;
        }
        body {
            background-color: white !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- 1. DATABASE SETUP ---
def init_db():
    try:
        conn = sqlite3.connect('serviceticker_v8.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shop_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_name TEXT, tax_id TEXT, address TEXT, phone TEXT, email TEXT, footer_message TEXT, promptpay TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE, password TEXT, fullname TEXT, role TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT, name TEXT, serial_no TEXT, category TEXT, 
                buy_price REAL, sell_price REAL, qty INTEGER, status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_no TEXT UNIQUE, date TEXT, customer TEXT, phone TEXT, 
                device_model TEXT, serial_no TEXT, issue TEXT, 
                parts_cost REAL, labor_cost REAL, total_price REAL, 
                status TEXT, technician TEXT, payment_status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_no TEXT, date TEXT, customer TEXT, item TEXT, 
                qty INTEGER, total REAL, profit REAL, payment_method TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_no TEXT, date TEXT, customer TEXT, item TEXT, 
                serial_no TEXT, issue TEXT, status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, username TEXT, action TEXT
            )
        ''')
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Database Error: {e}")
        return None

conn = init_db()
if conn is None:
    st.stop()

cursor = conn.cursor()

# Seed default data
cursor.execute('SELECT COUNT(*) FROM shop_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('''
        INSERT INTO shop_settings (shop_name, tax_id, address, phone, email, footer_message, promptpay)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส', '0123456789000', '123/45 ถนนพหลโยธิน แขวงสามเสนใน เขตพญาไท กรุงเทพฯ 10400', '02-xxx-xxxx', 'zone@email.com', '*ขอบคุณที่ใช้บริการครับ เงื่อนไขการรับประกันเป็นไปตามที่ร้านกำหนด*', '0812345678'))
    conn.commit()

cursor.execute('SELECT COUNT(*) FROM users')
if cursor.fetchone()[0] == 0:
    default_users = [
        ('admin', '1234', 'ผู้ดูแลระบบสูงสุด (Admin)', 'Admin'),
        ('tech1', '1234', 'ช่างสมชาย (Technician)', 'Technician'),
        ('cashier', '1234', 'พนักงานแคชเชียร์ (Cashier)', 'Cashier')
    ]
    cursor.executemany("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)", default_users)
    conn.commit()

cursor.execute('SELECT COUNT(*) FROM inventory')
if cursor.fetchone()[0] == 0:
    default_stock = [
        ('P001', 'SSD 500GB M.2 NVMe', 'SN-SSD500-001', 'อะไหล่', 1100, 1550, 10, 'In Stock'),
        ('P002', 'RAM DDR4 16GB', 'SN-RAM16-002', 'อะไหล่', 1000, 1450, 8, 'In Stock'),
        ('P003', 'Thermal Paste MX-4', 'N/A', 'อุปกรณ์เสริม', 80, 150, 25, 'In Stock')
    ]
    cursor.executemany("INSERT INTO inventory (code, name, serial_no, category, buy_price, sell_price, qty, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", default_stock)
    conn.commit()

def get_shop_info():
    df = pd.read_sql("SELECT * FROM shop_settings WHERE id=1", conn)
    if not df.empty:
        return df.iloc[0]
    return {
        "shop_name": "ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส",
        "tax_id": "0123456789000",
        "address": "123/45 ถนนพหลโยธิน กรุงเทพฯ",
        "phone": "02-xxx-xxxx",
        "email": "zone@email.com",
        "footer_message": "*ขอบคุณที่ใช้บริการครับ*",
        "promptpay": "0812345678"
    }

def make_qr(url):
    if not HAS_QR:
        return None
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def render_print_button(html_content, label="🖨️ เปิดหน้าต่างพิมพ์เอกสาร (Print)"):
    b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    href = f'''
        <a href="data:text/html;charset=utf-8;base64,{b64}" target="_blank" style="display:inline-block; background-color:#1E3A8A; color:white; padding:10px 20px; border-radius:5px; text-decoration:none; font-weight:bold; font-family:'Kanit',sans-serif; margin: 10px 0;">
            {label}
        </a>
    '''
    st.markdown(href, unsafe_allow_html=True)

shop_info = get_shop_info()

# Safe Query Params
try:
    mode = st.query_params.get("mode", "")
except:
    mode = ""

# ====================================================
# 📱 MOBILE PORTAL: ลูกค้าสแกนลงทะเบียนซ่อมเอง
# ====================================================
if mode == "register":
    st.title(f"🛠️ {shop_info['shop_name']}")
    st.subheader("📝 ลงทะเบียนแจ้งซ่อมด้วยตนเอง")
    with st.form("cust_reg_form"):
        c_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        c_phone = st.text_input("เบอร์โทรศัพท์มือถือ")
        c_model = st.text_input("รุ่นคอมพิวเตอร์ / โน้ตบุ๊ก")
        c_sn = st.text_input("Serial Number (ถ้ามี)")
        c_issue = st.text_area("อาการเสีย / ปัญหาที่พบ")
        
        submitted = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อม")
        if submitted:
            if c_name and c_phone and c_model:
                cursor.execute("SELECT COUNT(*) FROM repairs")
                cnt = cursor.fetchone()[0] + 1
                j_no = f"JOB-{datetime.now().strftime('%y%m')}-{str(cnt).zfill(3)}"
                d_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                cursor.execute("""
                    INSERT INTO repairs (job_no, date, customer, phone, device_model, serial_no, issue, parts_cost, labor_cost, total_price, status, technician, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 'รอตรวจสอบ', ?, 'ยังไม่ชำระ')
                """, (j_no, d_str, c_name, c_phone, c_model, c_sn, c_issue))
                conn.commit()
                st.success(f"🎉 ลงทะเบียนแจ้งซ่อมสำเร็จ! เลขที่ใบงานของคุณคือ: **{j_no}**")
            else:
                st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
    st.stop()

# ====================================================
# 🔐 LOGIN SYSTEM
# ====================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>💻 {shop_info['shop_name']}</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("เข้าสู่ระบบ", use_container_width=True)
            if submit:
                cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
                user = cursor.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = {"id": user[0], "username": user[1], "name": user[3], "role": user[4]}
                    st.success("เข้าสู่ระบบสำเร็จ!")
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        st.info("💡 **ทดสอบระบบ:** Admin: `admin`/`1234` | ช่าง: `tech1`/`1234` | แคชเชียร์: `cashier`/`1234`")
    st.stop()

# ====================================================
# 🛠️ SIDEBAR NAVIGATION
# ====================================================
current_user = st.session_state.user

with st.sidebar:
    st.markdown(f"### 👤 ผู้ใช้งาน: {current_user['name']}")
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
    st.markdown("---")
    
    menu = st.sidebar.radio("เลือกเมนูการทำงาน", [
        "🛠️ ระบบรับ-ส่งงานซ่อม",
        "🧾 ออกใบเสร็จรับเงิน (Dynamic Items & QR)",
        "⚙️ จัดการข้อมูลร้านค้า (Shop Admin)",
        "⚙️ ระบบจัดการหลังบ้าน (Master Back-office)",
        "📄 ออกเอกสาร & ฟอร์มทางธุรกิจ (A4)",
        "📱 QR Code สำหรับลูกค้าสแกนซ่อม",
        "📦 สต็อกสินค้า & Serial Number (S/N)",
        "🔄 ระบบเคลมสินค้า (Claims)",
        "🛒 ระบบขายหน้าร้าน (POS)",
        "💰 งานบัญชี & ลูกหนี้คงค้าง",
        "📊 รายงานสรุปผล (Reports)",
        "📋 ตรวจสอบการเข้าใช้งาน (Audit Log)"
    ])

# ----------------------------------------------------
# 1. ระบบรับ-ส่งงานซ่อม
# ----------------------------------------------------
if menu == "🛠️ ระบบรับ-ส่งงานซ่อม":
    st.subheader("🛠️ ระบบบริหารจัดการงานซ่อมคอมพิวเตอร์")
    
    tab1, tab2 = st.tabs(["รับเครื่องเข้าซ่อม (หน้าร้าน)", "ติดตาม & จัดการสถานะซ่อม"])
    
    with tab1:
        with st.form("new_repair"):
            col1, col2 = st.columns(2)
            with col1:
                cust_name = st.text_input("ชื่อ-นามสกุลลูกค้า")
                cust_phone = st.text_input("เบอร์โทรศัพท์")
                device_model = st.text_input("รุ่นอุปกรณ์ (เช่น ASUS TUF Gaming)")
            with col2:
                serial_no = st.text_input("Serial Number (S/N) อุปกรณ์", value="N/A")
                tech_list = [u[3] for u in cursor.execute("SELECT * FROM users WHERE role='Technician'").fetchall()]
                technician = st.selectbox("มอบหมายช่างผู้รับผิดชอบ", tech_list if tech_list else ["ช่างทั่วไป"])
                issue = st.text_area("อาการเสีย / ตำหนิภายนอก")
                
            submitted = st.form_submit_button("บันทึกรับเครื่องซ่อม")
            if submitted and cust_name and cust_phone:
                cursor.execute("SELECT COUNT(*) FROM repairs")
                job_count = cursor.fetchone()[0] + 1
                job_no = f"JOB-{datetime.now().strftime('%y%m')}-{str(job_count).zfill(3)}"
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                cursor.execute("""
                    INSERT INTO repairs (job_no, date, customer, phone, device_model, serial_no, issue, parts_cost, labor_cost, total_price, status, technician, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 'รอตรวจสอบ', ?, 'ยังไม่ชำระ')
                """, (job_no, date_str, cust_name, cust_phone, device_model, serial_no, issue, technician))
                conn.commit()
                st.session_state['last_saved_job'] = job_no
                st.success(f"บันทึกรับซ่อมสำเร็จ! เลขที่ใบงาน: **{job_no}**")

        if 'last_saved_job' in st.session_state:
            st.markdown("---")
            st.markdown(f"### 🖨️ พิมพ์ใบรับซ่อมสำหรับใบงานล่าสุด: `{st.session_state['last_saved_job']}`")
            j_data = pd.read_sql(f"SELECT * FROM repairs WHERE job_no='{st.session_state['last_saved_job']}'", conn).iloc[0]
            
            html_print = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>Print Job {j_data['job_no']}</title>
            <style>body{{font-family:'Kanit',sans-serif; padding:20px; color:#000;}} table{{width:100%; border-collapse:collapse; margin-top:10px;}} td, th{{border:1px solid #333; padding:8px; font-size:14px;}} .no-border td{{border:none;}}</style>
            </head>
            <body onload="window.print()">
                <h2 style="text-align:center; margin:0;">{shop_info['shop_name']}</h2>
                <p style="text-align:center; font-size:12px;">ที่อยู่: {shop_info['address']} | โทร. {shop_info['phone']} | Tax ID: {shop_info['tax_id']}</p>
                <h3 style="text-align:center; border-bottom:2px solid #000; padding-bottom:5px;">ใบรับซ่อมสินค้า / SERVICE RECEIPT</h3>
                <table class="no-border" style="margin-top:15px;">
                    <tr><td><b>เลขที่ใบงาน:</b> {j_data['job_no']}</td><td><b>วันที่รับ:</b> {j_data['date']}</td></tr>
                    <tr><td><b>ชื่อลูกค้า:</b> {j_data['customer']}</td><td><b>เบอร์โทร:</b> {j_data['phone']}</td></tr>
                    <tr><td><b>รุ่นอุปกรณ์:</b> {j_data['device_model']}</td><td><b>Serial No:</b> {j_data['serial_no']}</td></tr>
                    <tr><td colspan="2"><b>อาการเสีย:</b> {j_data['issue']}</td></tr>
                    <tr><td><b>ช่างผู้รับผิดชอบ:</b> {j_data['technician']}</td><td><b>สถานะ:</b> {j_data['status']}</td></tr>
                </table>
                <br><br><br>
                <table class="no-border" style="text-align:center; margin-top:30px;">
                    <tr><td>___________________________________<br>ลงชื่อ ผู้รับเครื่อง (ร้าน)</td><td>___________________________________<br>ลงชื่อ ลูกค้าผู้ส่งซ่อม</td></tr>
                </table>
            </body>
            </html>
            """
            render_print_button(html_print, "🖨️ เปิดหน้าต่างพิมพ์ใบรับซ่อม (Print)")
                
    with tab2:
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df[['job_no', 'date', 'customer', 'device_model', 'serial_no', 'status', 'technician', 'total_price']], use_container_width=True)
            
            selected_job = st.selectbox("เลือกเลขที่ใบงานซ่อม", repairs_df['job_no'].tolist(), key="sel_job_print")
            row = repairs_df[repairs_df['job_no'] == selected_job].iloc[0]
            
            shortcut_doc = st.selectbox("เลือกประเภทเอกสารที่ต้องการพิมพ์", [
                "ใบรับซ่อม", "ใบประเมินราคา", "ใบเสนอราคา", "ใบส่งของ", "ใบกำกับภาษี", "บิลเงินสด", "ใบเสร็จรับเงิน"
            ])
            
            html_doc = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>{shortcut_doc} - {row['job_no']}</title>
            <style>body{{font-family:'Kanit',sans-serif; padding:30px; color:#000;}} table{{width:100%; border-collapse:collapse; margin-top:15px;}} th, td{{border:1px solid #333; padding:10px; font-size:14px;}} .no-border td{{border:none;}}</style>
            </head>
            <body onload="window.print()">
                <table class="no-border">
                    <tr>
                        <td><h2 style="margin:0;">{shop_info['shop_name']}</h2><p style="font-size:12px; margin:0;">{shop_info['address']}<br>โทร: {shop_info['phone']} | Tax ID: {shop_info['tax_id']}</p></td>
                        <td style="text-align:right;"><h2 style="color:#1E3A8A; margin:0;">{shortcut_doc.upper()}</h2><p style="font-size:12px; margin:0;"><b>เลขที่:</b> DOC-{row['job_no']}<br><b>วันที่:</b> {datetime.now().strftime('%Y-%m-%d')}</p></td>
                    </tr>
                </table>
                <hr style="margin:15px 0;">
                <p style="font-size:14px;"><b>นามลูกค้า:</b> {row['customer']} &nbsp;&nbsp;|&nbsp;&nbsp; <b>เบอร์โทร:</b> {row['phone']}</p>
                <table>
                    <tr style="background:#f2f2f2;"><th style="text-align:left; width:10%;">ลำดับ</th><th style="text-align:left; width:50%;">รายการ</th><th style="text-align:center; width:10%;">จำนวน</th><th style="text-align:right; width:15%;">ราคาต่อหน่วย</th><th style="text-align:right; width:15%;">จำนวนเงิน</th></tr>
                    <tr><td>1</td><td>ค่าบริการตรวจเช็คและซ่อมอุปกรณ์ ({row['device_model']} - S/N: {row['serial_no']})</td><td style="text-align:center;">1</td><td style="text-align:right;">{row['total_price']:,.2f}</td><td style="text-align:right;">{row['total_price']:,.2f}</td></tr>
                </table>
                <br><div style="text-align:right; font-size:16px;"><p><b>ยอดรวมทั้งสิ้น:</b> {row['total_price']:,.2f} บาท</p></div>
                <br><br>
                <table class="no-border" style="margin-top:30px; text-align:center;">
                    <tr><td>___________________________________<br>ผู้มีอำนาจลงนาม / ผู้ออกเอกสาร</td><td>___________________________________<br>ผู้รับสินค้า / ลูกค้า</td></tr>
                </table>
            </body>
            </html>
            """
            render_print_button(html_doc, f"🖨️ เปิดหน้าต่างพิมพ์ {shortcut_doc} (Print)")
            
            st.markdown("---")
            st.markdown("### ⚙️ อัปเดตสถานะและค่าบริการ")
            with st.form("update_repair"):
                new_status = st.selectbox("สถานะงานซ่อม", ["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"], 
                                         index=["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"].index(row['status']) if row['status'] in ["รอตรวจสอบ", "กำลังซ่อม", "รออะไหล่", "ซ่อมเสร็จรอส่งมอบ", "ส่งมอบแล้วยกเลิก"] else 0)
                parts_cost = st.number_input("ต้นทุนอะไหล่ (บาท)", min_value=0.0, value=float(row['parts_cost']))
                labor_cost = st.number_input("ค่าบริการ / ค่าแรง (บาท)", min_value=0.0, value=float(row['labor_cost']))
                total_price = parts_cost + labor_cost
                payment_status = st.selectbox("สถานะการชำระเงิน", ["ยังไม่ชำระ", "ชำระแล้ว (เงินสด/โอน)", "ค้างชำระ (ลูกหนี้)"], index=0 if row['payment_status']=='ยังไม่ชำระ' else 1)
                
                if st.form_submit_button("บันทึกการอัปเดต"):
                    cursor.execute("UPDATE repairs SET status=?, parts_cost=?, labor_cost=?, total_price=?, payment_status=? WHERE job_no=?",
                                   (new_status, parts_cost, labor_cost, total_price, payment_status, selected_job))
                    conn.commit()
                    st.success("อัปเดตข้อมูลงานซ่อมสำเร็จ!")
                    st.rerun()
        else:
            st.info("ยังไม่มีข้อมูลงานซ่อมในระบบ")

# ----------------------------------------------------
# 2. ออกใบเสร็จรับเงิน
# ----------------------------------------------------
elif menu == "🧾 ออกใบเสร็จรับเงิน (Dynamic Items & QR)":
    st.subheader("🧾 ระบบออกใบเสร็จรับเงิน / ใบกำกับภาษี")
    if 'receipt_items' not in st.session_state:
        st.session_state.receipt_items = [{"item": "ค่าบริการตรวจเช็คและซ่อมคอมพิวเตอร์", "qty": 1, "price": 500.0}]
        
    c_name_input = st.text_input("ชื่อ-นามสกุลลูกค้า / บริษัท", value="ลูกค้าทั่วไป")
    
    with st.form("add_item_form", clear_on_submit=True):
        col_i1, col_i2, col_i3 = st.columns([3, 1, 1])
        with col_i1:
            new_item_name = st.text_input("ชื่อรายการสินค้า หรือค่าบริการซ่อม")
        with col_i2:
            new_item_qty = st.number_input("จำนวน", min_value=1, value=1)
        with col_i3:
            new_item_price = st.number_input("ราคาต่อหน่วย (บาท)", min_value=0.0, value=0.0)
            
        if st.form_submit_button("➕ เพิ่มรายการ") and new_item_name:
            st.session_state.receipt_items.append({"item": new_item_name, "qty": new_item_qty, "price": new_item_price})
            st.rerun()
            
    if st.session_state.receipt_items:
        st.dataframe(pd.DataFrame(st.session_state.receipt_items), use_container_width=True)
        sub_total = sum([item['qty'] * item['price'] for item in st.session_state.receipt_items])
        vat_7 = sub_total * 0.07
        net_total = sub_total + vat_7
        
        st.markdown(f"### 💰 ยอดชำระสุทธิ: **{net_total:,.2f} บาท** (รวม VAT 7%)")
        
        qr_bytes = make_qr(f"PromptPay:{shop_info['promptpay']}|Amount:{net_total:.2f}")
        
        rows_html = "".join([f"<tr><td>{i['item']}</td><td style='text-align:center;'>{i['qty']}</td><td style='text-align:right;'>{(i['qty']*i['price']):,.2f}</td></tr>" for i in st.session_state.receipt_items])
        html_receipt = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>Receipt</title>
        <style>body{{font-family:'Kanit',sans-serif; padding:30px; color:#000;}} table{{width:100%; border-collapse:collapse; margin-top:10px;}} th, td{{border:1px solid #333; padding:8px; font-size:13px;}}</style>
        </head>
        <body onload="window.print()">
            <h3 style="text-align:center; margin:0;">{shop_info['shop_name']}</h3>
            <p style="text-align:center; font-size:12px; margin:2px;">{shop_info['address']}<br>โทร: {shop_info['phone']} | Tax ID: {shop_info['tax_id']}</p>
            <h3 style="text-align:center; margin: 10px 0; border-bottom: 2px solid #000; padding-bottom: 3px;">ใบเสร็จรับเงิน / RECEIPT</h3>
            <p><b>ลูกค้า:</b> {c_name_input} &nbsp;&nbsp;|&nbsp;&nbsp; <b>วันที่:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <table>
                <tr style="background:#eee;"><th style="text-align:left;">รายการ</th><th style="text-align:center;">จำนวน</th><th style="text-align:right;">ราคา</th></tr>
                {rows_html}
            </table>
            <p style="text-align:right; margin-top:10px; font-size:14px;">
                <b>รวมเป็นเงิน:</b> {sub_total:,.2f} บาท<br><b>ภาษีมูลค่าเพิ่ม (7%):</b> {vat_7:,.2f} บาท<br><b style="font-size:16px;">ยอดสุทธิ: {net_total:,.2f} บาท</b>
            </p>
            <center><p style="font-size:12px; color:#555;">{shop_info['footer_message']}</p></center>
        </body>
        </html>
        """
        render_print_button(html_receipt, "🖨️ เปิดหน้าต่างพิมพ์ใบเสร็จ (Print)")
        
        if qr_bytes:
            st.image(qr_bytes, caption=f"PromptPay: {shop_info['promptpay']}", width=200)

# ----------------------------------------------------
# 3. Shop Admin & Back-office อื่นๆ
# ----------------------------------------------------
elif menu == "⚙️ จัดการข้อมูลร้านค้า (Shop Admin)":
    st.subheader("⚙️ ระบบจัดการข้อมูลร้านค้า")
    current_shop = get_shop_info()
    with st.form("shop_admin_form"):
        s_name = st.text_input("ชื่อร้านค้า", value=current_shop['shop_name'])
        s_tax = st.text_input("Tax ID", value=current_shop['tax_id'])
        s_addr = st.text_area("ที่อยู่", value=current_shop['address'])
        s_phone = st.text_input("เบอร์โทร", value=current_shop['phone'])
        s_email = st.text_input("อีเมล", value=current_shop['email'])
        s_promptpay = st.text_input("พร้อมเพย์", value=current_shop['promptpay'])
        s_footer = st.text_input("ข้อความท้ายบิล", value=current_shop['footer_message'])
        
        if st.form_submit_button("💾 บันทึก"):
            cursor.execute("UPDATE shop_settings SET shop_name=?, tax_id=?, address=?, phone=?, email=?, footer_message=?, promptpay=? WHERE id=1",
                           (s_name, s_tax, s_addr, s_phone, s_email, s_footer, s_promptpay))
            conn.commit()
            st.success("บันทึกสำเร็จ!")
            st.rerun()

elif menu == "⚙️ ระบบจัดการหลังบ้าน (Master Back-office)":
    st.subheader("⚙️ ระบบจัดการหลังบ้าน")
    st.dataframe(pd.read_sql("SELECT * FROM repairs", conn), use_container_width=True)

elif menu == "📄 ออกเอกสาร & ฟอร์มทางธุรกิจ (A4)":
    st.subheader("📄 ออกเอกสาร A4")
    rep_list = pd.read_sql("SELECT job_no, customer FROM repairs", conn)
    if not rep_list.empty:
        target_job = st.selectbox("เลือกใบงาน", rep_list['job_no'].tolist())
        j_data = pd.read_sql(f"SELECT * FROM repairs WHERE job_no='{target_job}'", conn).iloc[0]
        html_a4 = f"<h3>{shop_info['shop_name']} - {j_data['customer']}</h3><p>ยอดเงิน: {j_data['total_price']:,.2f} บาท</p>"
        render_print_button(html_a4, "🖨️ พิมพ์เอกสาร A4")

elif menu == "📱 QR Code สำหรับลูกค้าสแกนซ่อม":
    st.subheader("📱 QR Code ลงทะเบียนซ่อม")
    try:
        current_url = st.context.url.split("?")[0].strip('/')
    except:
        current_url = "http://localhost:8501"
    qr_b = make_qr(f"{current_url}/?mode=register")
    if qr_b:
        st.image(qr_b, width=250)

elif menu == "📦 สต็อกสินค้า & Serial Number (S/N)":
    st.dataframe(pd.read_sql("SELECT * FROM inventory", conn), use_container_width=True)

elif menu == "🔄 ระบบเคลมสินค้า (Claims)":
    st.dataframe(pd.read_sql("SELECT * FROM claims", conn), use_container_width=True)

elif menu == "🛒 ระบบขายหน้าร้าน (POS)":
    st.dataframe(pd.read_sql("SELECT * FROM sales", conn), use_container_width=True)

elif menu == "💰 งานบัญชี & ลูกหนี้คงค้าง":
    st.dataframe(pd.read_sql("SELECT * FROM repairs WHERE payment_status='ค้างชำระ (ลูกหนี้)'", conn), use_container_width=True)

elif menu == "📊 รายงานสรุปผล (Reports)":
    st.dataframe(pd.read_sql("SELECT * FROM sales", conn), use_container_width=True)

elif menu == "📋 ตรวจสอบการเข้าใช้งาน (Audit Log)":
    st.dataframe(pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", conn), use_container_width=True)