import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import qrcode
from io import BytesIO

st.set_page_config(page_title="Zone Computer & Service Pro", layout="wide")

# 1. ตั้งค่าฐานข้อมูล SQLite (รองรับทุกตารางแบบครบถ้วน)
def init_db():
    conn = sqlite3.connect('computer_shop_pro.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # ตารางสต็อกสินค้า (เพิ่มราคาทุน)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT, category TEXT, qty INTEGER, buy_price REAL, price REAL
        )
    ''')
    # ตารางประวัติการขาย
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, customer TEXT, item TEXT, subtotal REAL, discount REAL, total REAL, profit REAL, payment TEXT
        )
    ''')
    # ตารางงานซ่อม
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, customer TEXT, phone TEXT, model TEXT, serial_no TEXT, issue TEXT, parts_fee REAL, labor_fee REAL, total_price REAL, status TEXT, technician TEXT
        )
    ''')
    # ตารางบันทึกรายจ่ายของร้าน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, description TEXT, amount REAL
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# เติมข้อมูลเริ่มต้นหากฐานข้อมูลว่าง
cursor.execute('SELECT COUNT(*) FROM inventory')
if cursor.fetchone()[0] == 0:
    default_items = [
        ("P001", "SSD 500GB M.2 NVMe", "อะไหล่", 12, 1100, 1550),
        ("P002", "RAM DDR4 16GB", "อะไหล่", 8, 1000, 1450),
        ("P003", "Thermal Paste (ซิลิโคน)", "อุปกรณ์เสริม", 25, 80, 150),
        ("P004", "Power Supply 650W", "อะไหล่", 5, 1300, 1890),
        ("S001", "ค่าบริการซ่อม / ลงโปรแกรม", "บริการ", 999, 0, 500)
    ]
    cursor.executemany("INSERT INTO inventory (code, name, category, qty, buy_price, price) VALUES (?, ?, ?, ?, ?, ?)", default_items)
    conn.commit()

# ฟังก์ชันสร้าง QR Code
def make_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ตรวจสอบ URL Query Parameter สำหรับโหมดลูกค้า
query_params = st.query_params
mode = query_params.get("mode", "")

# ----------------------------------------------------
# 📱 โหมดที่ 1: ลูกค้าสแกนลงทะเบียนซ่อม
# ----------------------------------------------------
if mode == "register":
    st.title("🛠️ ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส")
    st.subheader("📝 ลงทะเบียนแจ้งซ่อมเครื่องด้วยตนเอง")
    st.write("กรุณากรอกข้อมูลด้านล่างให้ครบถ้วน เพื่อให้ช่างตรวจสอบอาการเบื้องต้นครับ")
    
    with st.form("customer_repair_form"):
        cust_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        cust_phone = st.text_input("เบอร์โทรศัพท์ที่ติดต่อได้")
        cust_model = st.text_input("รุ่นคอมพิวเตอร์ / โน้ตบุ๊ก (เช่น ASUS TUF / Acer Aspire)")
        cust_serial = st.text_input("หมายเลขเครื่อง / Serial Number (ถ้ามี)")
        cust_issue = st.text_area("อาการเสีย / ปัญหาที่พบ (เช่น เปิดไม่ติด จอฟ้า เครื่องช้า)")
        
        submitted = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อม")
        
        if submitted:
            if cust_name and cust_phone and cust_model:
                r_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                cursor.execute(
                    "INSERT INTO repairs (date, customer, phone, model, serial_no, issue, parts_fee, labor_fee, total_price, status, technician) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (r_date, cust_name, cust_phone, cust_model, cust_serial, cust_issue, 0.0, 0.0, 0.0, "รอตรวจสอบ", "ยังไม่ระบุ")
                )
                conn.commit()
                st.success("🎉 ส่งข้อมูลแจ้งซ่อมสำเร็จ! ทางร้านได้รับข้อมูลเรียบร้อยแล้ว สามารถนำเครื่องมาส่งที่ร้านได้เลยครับ")
            else:
                st.error("❌ กรุณากรอกชื่อ เบอร์โทรศัพท์ และรุ่นคอมพิวเตอร์ให้ครบถ้วน")
                
    st.markdown("---")
    if st.button("🔐 กลับสู่ระบบหลังบ้าน (Admin)"):
        st.query_params.clear()
        st.rerun()

# ----------------------------------------------------
# 🔍 โหมดที่ 2: ลูกค้าตรวจสอบสถานะซ่อมด้วยเบอร์โทร
# ----------------------------------------------------
elif mode == "track":
    st.title("🔍 ตรวจสอบสถานะงานซ่อมออนไลน์")
    st.write("กรอกเบอร์โทรศัพท์ของคุณเพื่อเช็คสถานะเครื่องซ่อมปัจจุบัน")
    
    search_phone = st.text_input("เบอร์โทรศัพท์มือถือ")
    if search_phone:
        repairs_df = pd.read_sql(f"SELECT * FROM repairs WHERE phone LIKE '%{search_phone}%'", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df[["date", "model", "issue", "total_price", "status", "technician"]], use_container_width=True)
        else:
            st.warning("ไม่พบข้อมูลงานซ่อมที่ตรงกับเบอร์โทรศัพท์นี้")
            
    st.markdown("---")
    if st.button("🔐 กลับสู่ระบบหลังบ้าน (Admin)"):
        st.query_params.clear()
        st.rerun()

# ----------------------------------------------------
# 💻 โหมดที่ 3: ระบบหลังบ้านแอดมิน (Admin Dashboard)
# ----------------------------------------------------
else:
    st.title("💻 ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส (Pro Management System)")
    
    menu = st.sidebar.selectbox(
        "เลือกเมนูการทำงาน", 
        [
            "🛒 ระบบขายหน้าร้าน (POS)", 
            "📦 จัดการสต็อกสินค้า & ทุน",
            "📝 ระบบจัดการงานซ่อม",
            "👥 ค้นหาประวัติลูกค้า (CRM)",
            "💵 บันทึกรายจ่าย & สรุปบัญชี",
            "📊 รายงานสรุปยอดขายและกำไร",
            "🖨️ QR Code สำหรับลูกค้าสแกน"
        ]
    )

    # 1. ระบบ POS
    if menu == "🛒 ระบบขายหน้าร้าน (POS)":
        st.subheader("🛒 ระบบขายหน้าร้าน & ตัดสต็อกอัตโนมัติ")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        
        col1, col2 = st.columns(2)
        with col1:
            cust_name = st.text_input("ชื่อ-นามสกุลลูกค้า", value="ลูกค้าทั่วไป")
            item_options = inv_df["name"].tolist()
            selected_item = st.selectbox("เลือกสินค้า / บริการ", item_options)
            
            item_row = inv_df[inv_df["name"] == selected_item].iloc[0]
            item_id = item_row["id"]
            buy_price = item_row["buy_price"]
            unit_price = item_row["price"]
            current_stock = item_row["qty"]
            
            if selected_item != "ค่าบริการซ่อม / ลงโปรแกรม":
                st.info(f"📦 สต็อกคงเหลือ: **{current_stock} ชิ้น** | ต้นทุน: {buy_price:,.2f} บาท")
                max_qty = int(current_stock) if current_stock > 0 else 1
            else:
                max_qty = 100

            price = st.number_input("ราคาขายต่อหน่วย (บาท)", min_value=0.0, value=float(unit_price))
            qty = st.number_input("จำนวนที่ซื้อ", min_value=1, max_value=max_qty, value=1)
        
        with col2:
            st.markdown("### 💰 คำนวณส่วนลด & ยอดชำระ")
            discount_type = st.radio("ประเภทส่วนลด", ["ไม่มีส่วนลด", "ส่วนลดเงินสด (บาท)", "ส่วนลดเปอร์เซ็นต์ (%)"])
            
            subtotal = price * qty
            discount_amount = 0.0
            
            if discount_type == "ส่วนลดเงินสด (บาท)":
                discount_amount = st.number_input("ระบุจำนวนเงินส่วนลด (บาท)", min_value=0.0, value=0.0)
            elif discount_type == "ส่วนลดเปอร์เซ็นต์ (%)":
                disc_pct = st.number_input("ระบุเปอร์เซ็นต์ส่วนลด (%)", min_value=0.0, max_value=100.0, value=0.0)
                discount_amount = subtotal * (disc_pct / 100.0)
                
            net_total = subtotal - discount_amount
            est_profit = net_total - (buy_price * qty)
            
            st.write(f"ยอดรวมก่อนลด: **{subtotal:,.2f} บาท**")
            if discount_amount > 0:
                st.warning(f"ส่วนลด: **-{discount_amount:,.2f} บาท**")
            st.success(f"### ยอดสุทธิที่ต้องชำระ: {net_total:,.2f} บาท")
            st.caption(f"💡 กำไรประมาณการจากรายการนี้: {est_profit:,.2f} บาท")
            
            payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "QR Code โอนเงิน", "บัตรเครดิต"])
            
        if st.button("💾 ยืนยันการขาย (ตัดสต็อก & ออกใบเสร็จ)"):
            if selected_item != "ค่าบริการซ่อม / ลงโปรแกรม" and current_stock < qty:
                st.error("❌ สต็อกสินค้าไม่เพียงพอ ไม่สามารถทำรายการได้!")
            else:
                if selected_item != "ค่าบริการซ่อม / ลงโปรแกรม":
                    new_stock = current_stock - qty
                    cursor.execute("UPDATE inventory SET qty = ? WHERE id = ?", (new_stock, item_id))
                
                sale_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                item_desc = f"{selected_item} (x{qty})"
                cursor.execute(
                    "INSERT INTO sales (date, customer, item, subtotal, discount, total, profit, payment) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (sale_date, cust_name, item_desc, subtotal, discount_amount, net_total, est_profit, payment_method)
                )
                conn.commit()
                st.success("✅ บันทึกการขายและตัดสต็อกอัตโนมัติสำเร็จ!")
                
                st.markdown("---")
                st.markdown("### 🧾 ใบเสร็จรับเงิน / Tax Invoice (อย่างย่อย)")
                st.code(f"""
========================================
       ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส       
   โทร. 0xx-xxx-xxxx | บริการซ่อมและจำหน่าย 
========================================
วันที่: {sale_date}
ลูกค้า: {cust_name}
----------------------------------------
รายการ: {selected_item} 
จำนวน: {qty} ชิ้น  |  ราคาหน่วยละ: {price:,.2f} บาท
----------------------------------------
รวมเป็นเงิน: {subtotal:,.2f} บาท
ส่วนลด: -{discount_amount:,.2f} บาท
ยอดรวมสุทธิ: {net_total:,.2f} บาท
ชำระผ่าน: {payment_method}
========================================
        *ขอบคุณที่ใช้บริการครับ*         
========================================
                """, language="text")

    # 2. จัดการสต็อกสินค้า & ทุน
    elif menu == "📦 จัดการสต็อกสินค้า & ทุน":
        st.subheader("📦 คลังสินค้า อะไหล่ และต้นทุน")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        st.dataframe(inv_df, use_container_width=True)
        
        with st.expander("➕ เพิ่มสินค้าหรืออะไหล่ใหม่เข้าสต็อก"):
            new_id = st.text_input("รหัสสินค้า (เช่น P005)")
            new_name = st.text_input("ชื่อสินค้า / อะไหล่")
            new_cat = st.selectbox("ประเภท", ["อะไหล่", "อุปกรณ์เสริม", "บริการ", "คอมพิวเตอร์ประกอบ"])
            new_qty = st.number_input("จำนวนเริ่มต้นในสต็อก", min_value=1, value=10)
            new_buy_price = st.number_input("ราคาทุนต่อหน่วย (บาท)", min_value=0.0, value=100.0)
            new_price = st.number_input("ราคาขายต่อหน่วย (บาท)", min_value=0.0, value=500.0)
            
            if st.button("บันทึกเพิ่มสินค้าใหม่"):
                if new_id and new_name:
                    cursor.execute(
                        "INSERT INTO inventory (code, name, category, qty, buy_price, price) VALUES (?, ?, ?, ?, ?, ?)",
                        (new_id, new_name, new_cat, new_qty, new_buy_price, new_price)
                    )
                    conn.commit()
                    st.success("เพิ่มสินค้าใหม่สำเร็จ!")
                    st.rerun()
                else:
                    st.warning("กรุณากรอกรหัสและชื่อสินค้าให้ครบถ้วน")

    # 3. จัดการงานซ่อม
    elif menu == "📝 ระบบจัดการงานซ่อม":
        st.subheader("📝 ระบบจัดการงานซ่อมทั้งหมดในร้าน")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df, use_container_width=True)
            
            st.markdown("### ⚙️ จัดการ & อัปเดตงานซ่อม")
            repair_ids = repairs_df["id"].tolist()
            selected_repair_id = st.selectbox("เลือกรหัสงานซ่อมที่ต้องการจัดการ", repair_ids)
            
            current_row = repairs_df[repairs_df["id"] == selected_repair_id].iloc[0]
            st.info(f"ลูกค้า: {current_row['customer']} ({current_row['phone']}) | รุ่น: {current_row['model']} | S/N: {current_row['serial_no']}\n\nอาการ: {current_row['issue']}")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                parts_fee = st.number_input("ค่าอะไหล่ (บาท)", min_value=0.0, value=float(current_row['parts_fee']))
            with c2:
                labor_fee = st.number_input("ค่าแรงช่าง (บาท)", min_value=0.0, value=float(current_row['labor_fee']))
            with c3:
                tech_name = st.text_input("ช่างผู้รับผิดชอบ", value=str(current_row['technician']))
            
            total_repair_price = parts_fee + labor_fee
            st.write(f"ยอดรวมค่าซ่อมสุทธิ: **{total_repair_price:,.2f} บาท**")
            
            new_status = st.selectbox("เปลี่ยนสถานะงานซ่อม", ["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อยยกเลิก"])
            
            if st.button("บันทึกการอัปเดตงานซ่อม"):
                cursor.execute(
                    "UPDATE repairs SET parts_fee = ?, labor_fee = ?, total_price = ?, status = ?, technician = ? WHERE id = ?",
                    (parts_fee, labor_fee, total_repair_price, new_status, tech_name, selected_repair_id)
                )
                conn.commit()
                st.success("อัปเดตงานซ่อมสำเร็จ!")
                st.rerun()
        else:
            st.info("ยังไม่มีประวัติงานซ่อมในระบบ")

    # 4. CRM ค้นหาประวัติลูกค้า
    elif menu == "👥 ค้นหาประวัติลูกค้า (CRM)":
        st.subheader("👥 ค้นหาประวัติการซื้อและการซ่อมของลูกค้า")
        search_key = st.text_input("ค้นหาด้วยชื่อลูกค้า หรือ เบอร์โทรศัพท์")
        if search_key:
            st.markdown("#### 🛒 ประวัติการซื้อสินค้า")
            cust_sales = pd.read_sql(f"SELECT * FROM sales WHERE customer LIKE '%{search_key}%'", conn)
            st.dataframe(cust_sales, use_container_width=True)
            
            st.markdown("#### 🛠️ ประวัติการส่งซ่อมเครื่อง")
            cust_repairs = pd.read_sql(f"SELECT * FROM repairs WHERE customer LIKE '%{search_key}%' OR phone LIKE '%{search_key}%'", conn)
            st.dataframe(cust_repairs, use_container_width=True)

    # 5. บันทึกรายจ่าย
    elif menu == "💵 บันทึกรายจ่าย & สรุปบัญชี":
        st.subheader("💵 บันทึกรายจ่ายของร้าน (ค่าเช่า ค่าไฟ ค่าอะไหล่ซื้อเข้า ฯลฯ)")
        with st.form("expense_form"):
            exp_date = datetime.now().strftime("%Y-%m-%d")
            exp_desc = st.text_input("รายการรายจ่าย")
            exp_amount = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, value=0.0)
            submitted_exp = st.form_submit_button("บันทึกรายจ่าย")
            if submitted_exp and exp_desc:
                cursor.execute("INSERT INTO expenses (date, description, amount) VALUES (?, ?, ?)", (exp_date, exp_desc, exp_amount))
                conn.commit()
                st.success("บันทึกรายจ่ายสำเร็จ!")
                
        st.markdown("---")
        st.markdown("#### รายการรายจ่ายทั้งหมด")
        exp_df = pd.read_sql("SELECT * FROM expenses", conn)
        st.dataframe(exp_df, use_container_width=True)

    # 6. สรุปยอดขายและกำไร
    elif menu == "📊 รายงานสรุปยอดขายและกำไร":
        st.subheader("📊 รายงานสรุปยอดขาย กำไร และรายจ่าย")
        sales_df = pd.read_sql("SELECT * FROM sales", conn)
        expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
        
        total_revenue = sales_df["total"].sum() if not sales_df.empty else 0
        total_profit = sales_df["profit"].sum() if not sales_df.empty else 0
        total_expense = expenses_df["amount"].sum() if not expenses_df.empty else 0
        net_net_profit = total_profit - total_expense
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ยอดขายรวม", f"{total_revenue:,.2f} บาท")
        c2.metric("กำไรเบื้องต้นจากขาย", f"{total_profit:,.2f} บาท")
        c3.metric("รายจ่ายร้านรวม", f"{total_expense:,.2f} บาท")
        c4.metric("กำไรสุทธิแท้จริง", f"{net_net_profit:,.2f} บาท", delta=f"{net_net_profit:,.2f}")
        
        st.markdown("---")
        st.markdown("#### 📋 ประวัติการขายทั้งหมด")
        if not sales_df.empty:
            st.dataframe(sales_df, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการขาย")

    # 7. QR Code สำหรับลูกค้า
    elif menu == "🖨️ QR Code สำหรับลูกค้าสแกน":
        st.subheader("🖨️ สร้าง QR Code สำหรับให้ลูกค้าใช้งานบนมือถือ")
        st.write("คุณสามารถปริ้นท์ป้ายเหล่านี้ตั้งไว้ที่เคาน์เตอร์ร้านได้เลยครับ")
        
        current_url = st.context.url
        base_clean = current_url.split("?")[0].strip('/')
        
        col_qr1, col_qr2 = st.columns(2)
        
        with col_qr1:
            st.markdown("### 1. QR Code ลงทะเบียนซ่อม")
            reg_url = f"{base_clean}/?mode=register"
            st.info(f"ลิงก์: `{reg_url}`")
            st.image(make_qr(reg_url), caption="สแกนเพื่อลงทะเบียนแจ้งซ่อม", width=250)
            
        with col_qr2:
            st.markdown("### 2. QR Code เช็คสถานะซ่อม")
            track_url = f"{base_clean}/?mode=track"
            st.info(f"ลิงก์: `{track_url}`")
            st.image(make_qr(track_url), caption="สแกนเพื่อเช็คสถานะซ่อมด้วยเบอร์โทร", width=250)