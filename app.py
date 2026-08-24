import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import qrcode
from io import BytesIO

st.set_page_config(page_title="Zone Computer & Service", layout="wide")

# 1. ตั้งค่าฐานข้อมูล SQLite
def init_db():
    conn = sqlite3.connect('computer_shop.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, name TEXT, category TEXT, qty INTEGER, price REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, customer TEXT, item TEXT, subtotal REAL, discount REAL, total REAL, payment TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, customer TEXT, phone TEXT, model TEXT, issue TEXT, price REAL, status TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# เติมข้อมูลเริ่มต้นสต็อก
cursor.execute('SELECT COUNT(*) FROM inventory')
if cursor.fetchone()[0] == 0:
    default_items = [
        ("P001", "SSD 500GB M.2 NVMe", "อะไหล่", 12, 1550),
        ("P002", "RAM DDR4 16GB", "อะไหล่", 8, 1450),
        ("P003", "Thermal Paste (ซิลิโคน)", "อุปกรณ์เสริม", 25, 150),
        ("P004", "Power Supply 650W", "อะไหล่", 5, 1890),
        ("S001", "ค่าบริการซ่อม / ลงโปรแกรม", "บริการ", 999, 500)
    ]
    cursor.executemany("INSERT INTO inventory (code, name, category, qty, price) VALUES (?, ?, ?, ?, ?)", default_items)
    conn.commit()

# ฟังก์ชันสร้างรูป QR Code
def make_qr(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ตรวจสอบ URL Query Parameter (เพื่อแยกหน้าสำหรับลูกค้าสแกน vs หน้าเจ้าของร้าน)
query_params = st.query_params
mode = query_params.get("mode", "")

# ----------------------------------------------------
# 📱 โหมดที่ 1: หน้าลงทะเบียนซ่อมสำหรับลูกค้า (เมื่อสแกน QR Code)
# ----------------------------------------------------
if mode == "register":
    st.title("🛠️ ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส")
    st.subheader("📝 ลงทะเบียนแจ้งซ่อมเครื่องด้วยตนเอง")
    st.write("กรุณากรอกข้อมูลด้านล่างให้ครบถ้วน เพื่อให้ช่างตรวจสอบอาการเบื้องต้นครับ")
    
    with st.form("customer_repair_form"):
        cust_name = st.text_input("ชื่อ-นามสกุลของคุณ")
        cust_phone = st.text_input("เบอร์โทรศัพท์ที่ติดต่อได้")
        cust_model = st.text_input("รุ่นคอมพิวเตอร์ / โน้ตบุ๊ก (เช่น ASUS TUF / Acer Aspire)")
        cust_issue = st.text_area("อาการเสีย / ปัญหาที่พบ (เช่น เปิดไม่ติด จอฟ้า เครื่องช้า คีย์บอร์ดเสีย)")
        
        submitted = st.form_submit_button("📤 ส่งข้อมูลแจ้งซ่อม")
        
        if submitted:
            if cust_name and cust_phone and cust_model:
                r_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                initial_status = "รอตรวจสอบ (ลูกค้ายื่นคำขอเอง)"
                
                cursor.execute(
                    "INSERT INTO repairs (date, customer, phone, model, issue, price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (r_date, cust_name, cust_phone, cust_model, cust_issue, 0.0, initial_status)
                )
                conn.commit()
                st.success("🎉 ส่งข้อมูลแจ้งซ่อมสำเร็จ! ทางร้านได้รับข้อมูลเรียบร้อยแล้ว สามารถนำเครื่องมาส่งที่ร้านหรือรอช่างติดต่อกลับได้เลยครับ")
            else:
                st.error("❌ กรุณากรอกชื่อ เบอร์โทรศัพท์ และรุ่นคอมพิวเตอร์ให้ครบถ้วน")

# ----------------------------------------------------
# 💻 โหมดที่ 2: หน้าหลักสำหรับเจ้าของร้าน (POS, สต็อก, จัดการซ่อม, QR Code)
# ----------------------------------------------------
else:
    st.title("💻 ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส (Admin Dashboard)")
    
    menu = st.sidebar.selectbox(
        "เลือกเมนูการทำงาน", 
        [
            "🛒 ระบบขายหน้าร้าน (POS)", 
            "📦 จัดการสต็อกสินค้า",
            "📝 ระบบจัดการงานซ่อม",
            "🖨️ QR Code สำหรับให้ลูกค้าสแกนซ่อม",
            "📊 สรุปยอดขายรายวัน"
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
            unit_price = item_row["price"]
            current_stock = item_row["qty"]
            
            if selected_item != "ค่าบริการซ่อม / ลงโปรแกรม":
                st.info(f"📦 สต็อกคงเหลือ: **{current_stock} ชิ้น**")
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
            
            st.write(f"ยอดรวมก่อนลด: **{subtotal:,.2f} บาท**")
            if discount_amount > 0:
                st.warning(f"ส่วนลด: **-{discount_amount:,.2f} บาท**")
            st.success(f"### ยอดสุทธิที่ต้องชำระ: {net_total:,.2f} บาท")
            
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
                    "INSERT INTO sales (date, customer, item, subtotal, discount, total, payment) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (sale_date, cust_name, item_desc, subtotal, discount_amount, net_total, payment_method)
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

    # 2. จัดการสต็อกสินค้า
    elif menu == "📦 จัดการสต็อกสินค้า":
        st.subheader("📦 คลังสินค้าและอะไหล่")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        st.dataframe(inv_df, use_container_width=True)
        
        with st.expander("➕ เพิ่มสินค้าหรืออะไหล่ใหม่เข้าสต็อก"):
            new_id = st.text_input("รหัสสินค้า (เช่น P005)")
            new_name = st.text_input("ชื่อสินค้า / อะไหล่")
            new_cat = st.selectbox("ประเภท", ["อะไหล่", "อุปกรณ์เสริม", "บริการ", "คอมพิวเตอร์ประกอบ"])
            new_qty = st.number_input("จำนวนเริ่มต้นในสต็อก", min_value=1, value=10)
            new_price = st.number_input("ราคาขาย (บาท)", min_value=0.0, value=500.0)
            
            if st.button("บันทึกเพิ่มสินค้าใหม่"):
                if new_id and new_name:
                    cursor.execute(
                        "INSERT INTO inventory (code, name, category, qty, price) VALUES (?, ?, ?, ?, ?)",
                        (new_id, new_name, new_cat, new_qty, new_price)
                    )
                    conn.commit()
                    st.success("เพิ่มสินค้าใหม่สำเร็จ!")
                    st.rerun()
                else:
                    st.warning("กรุณากรอกรหัสและชื่อสินค้าให้ครบถ้วน")

    # 3. จัดการงานซ่อม
    elif menu == "📝 ระบบจัดการงานซ่อม":
        st.subheader("📝 รายการงานซ่อมทั้งหมดในร้าน")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df, use_container_width=True)
            
            st.markdown("### ⚙️ ประเมินราคา & อัปเดตสถานะงานซ่อม")
            repair_ids = repairs_df["id"].tolist()
            selected_repair_id = st.selectbox("เลือกรหัสงานซ่อมที่ต้องการจัดการ", repair_ids)
            
            current_row = repairs_df[repairs_df["id"] == selected_repair_id].iloc[0]
            st.info(f"ลูกค้า: {current_row['customer']} ({current_row['phone']}) | รุ่น: {current_row['model']}\n\nอาการ: {current_row['issue']}")
            
            new_price = st.number_input("กำหนดราคาประเมินซ่อม (บาท)", min_value=0.0, value=float(current_row['price']))
            new_status = st.selectbox("เปลี่ยนสถานะงานซ่อม", ["รอตรวจสอบ (ลูกค้ายื่นคำขอเอง)", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"])
            
            if st.button("บันทึกอัปเดตข้อมูลงานซ่อม"):
                cursor.execute("UPDATE repairs SET price = ?, status = ? WHERE id = ?", (new_price, new_status, selected_repair_id))
                conn.commit()
                st.success("อัปเดตข้อมูลงานซ่อมสำเร็จ!")
                st.rerun()
        else:
            st.info("ยังไม่มีประวัติงานซ่อมในระบบ")

    # 4. QR Code สำหรับให้ลูกค้าสแกน (ดึง URL อัตโนมัติด้วย st.context.url)
    elif menu == "🖨️ QR Code สำหรับให้ลูกค้าสแกนซ่อม":
        st.subheader("🖨️ สร้าง QR Code สำหรับตั้งหน้าร้าน")
        st.write("ระบบดึงลิงก์เว็บไซต์ของร้านคุณมาสร้าง QR Code ให้ทันทีโดยอัตโนมัติ สามารถบันทึกภาพไปปริ้นท์ใช้งานได้เลยครับ")
        
        # ดึง URL ปัจจุบันของแอปแบบอัตโนมัติ
        current_url = st.context.url
        target_url = f"{current_url.strip('/')}/?mode=register"
        
        st.info(f"🔗 ลิงก์สำหรับให้ลูกค้าสแกน: `{target_url}`")
        
        # สร้างและแสดง QR Code
        qr_bytes = make_qr(target_url)
        st.image(qr_bytes, caption="สแกนเพื่อลงทะเบียนแจ้งซ่อม ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส", width=300)
        st.success("✅ สร้าง QR Code สำเร็จ! คลิกขวาที่รูป QR Code เพื่อบันทึกภาพนำไปปริ้นท์ตั้งหน้าร้านได้ทันที")

    # 5. สรุปยอดขายรายวัน
    elif menu == "📊 สรุปยอดขายรายวัน":
        st.subheader("📊 รายงานสรุปยอดขายและบริการ")
        sales_df = pd.read_sql("SELECT * FROM sales", conn)
        
        if not sales_df.empty:
            st.dataframe(sales_df, use_container_width=True)
            total_revenue = sales_df["total"].sum()
            total_transactions = len(sales_df)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("ยอดขายรวมสุทธิ", f"{total_revenue:,.2f} บาท")
            col2.metric("จำนวนบิลขาย", f"{total_transactions} รายการ")
            col3.metric("ยอดเฉลี่ยต่อบิล", f"{(total_revenue/total_transactions if total_transactions > 0 else 0):,.2f} บาท")
        else:
            st.info("ยังไม่มีประวัติการขายในระบบ")