import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import qrcode
from promptpay import qrcode as pp_qrcode
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Zone Computer & Service", layout="wide")

# 1. ตั้งค่าฐานข้อมูล SQLite
def init_db():
    conn = sqlite3.connect('computer_shop.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            category TEXT,
            qty INTEGER,
            price REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            customer TEXT,
            item TEXT,
            subtotal REAL,
            discount REAL,
            total REAL,
            payment TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            customer TEXT,
            phone TEXT,
            model TEXT,
            issue TEXT,
            price REAL,
            status TEXT
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# เติมข้อมูลตั้งต้นหากว่างเปล่า
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

st.title("💻 ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส (Online POS & Repair)")

# ตั้งค่าเบอร์ PromptPay สำหรับรับเงินของร้านที่ Sidebar
st.sidebar.markdown("### ⚙️ ตั้งค่าร้านค้า")
shop_promptpay = st.sidebar.text_input("เบอร์โทรพร้อมเพย์ (รับเงิน)", value="0812345678")

menu = st.sidebar.selectbox(
    "เลือกเมนูการทำงาน", 
    [
        "🛒 ระบบขายหน้าร้าน (POS & QR ชำระเงิน)", 
        "📦 จัดการสต็อกสินค้า",
        "📝 ระบบรับและติดตามงานซ่อม (พร้อม QR ลูกค้า)",
        "📊 สรุปยอดขายรายวัน",
        "⚙️ ระบบหลังบ้าน (Admin / แก้ไขข้อมูล)"
    ]
)

# ----------------------------------------------------
# 1. ระบบขายหน้าร้าน (POS) + QR Code ชำระเงิน PromptPay
# ----------------------------------------------------
if menu == "🛒 ระบบขายหน้าร้าน (POS & QR ชำระเงิน)":
    st.subheader("🛒 ระบบขายหน้าร้าน & สร้าง QR Code พร้อมเพย์อัตโนมัติ")
    
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
        
        payment_method = st.selectbox("ช่องทางการชำระเงิน", ["เงินสด", "QR Code โอนเงิน (PromptPay)", "บัตรเครดิต"])

    if payment_method == "QR Code โอนเงิน (PromptPay)":
        st.markdown("---")
        st.info(f"📱 **สแกน QR Code เพื่อชำระเงินยอดสุทธิ: {net_total:,.2f} บาท**")
        try:
            payload = pp_qrcode.generate_payload(shop_promptpay, float(net_total))
            qr_img = pp_qrcode.to_image(payload)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            st.image(buf.getvalue(), width=250, caption=f"พร้อมเพย์: {shop_promptpay} (ยอด {net_total:,.2f} บ.)")
        except Exception as e:
            st.error(f"ไม่สามารถสร้าง QR Code ได้ กรุณาตรวจสอบเบอร์พร้อมเพย์ (Error: {e})")

    if st.button("💾 ยืนยันการขาย (ตัดสต็อก & บันทึกบิล)"):
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

# ----------------------------------------------------
# 2. จัดการสต็อกสินค้า
# ----------------------------------------------------
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

# ----------------------------------------------------
# 3. ระบบรับและติดตามงานซ่อม + QR Code ลูกค้า
# ----------------------------------------------------
elif menu == "📝 ระบบรับและติดตามงานซ่อม (พร้อม QR ลูกค้า)":
    st.subheader("📝 ระบบจัดการงานซ่อม & สร้าง QR Code สำหรับลูกค้า")
    
    tab1, tab2 = st.tabs(["รับเครื่องเข้าซ่อม & ออก QR Code", "รายการและอัปเดตสถานะงานซ่อม"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            r_name = st.text_input("ชื่อ-นามสกุลลูกค้า")
            r_phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
        with c2:
            r_model = st.text_input("รุ่นคอมพิวเตอร์ / โน้ตบุ๊ก")
            r_price = st.number_input("ประเมินราคาซ่อมเบื้องต้น (บาท)", min_value=0.0, value=500.0)
        
        r_issue = st.text_area("อาการเสียและตำหนิภายนอกเครื่อง")
        
        if st.button("บันทึกรับเครื่องซ่อม"):
            if r_name and r_phone:
                r_date = datetime.now().strftime("%Y-%m-%d %H:%M")
                initial_status = "รอตรวจสอบ"
                cursor.execute(
                    "INSERT INTO repairs (date, customer, phone, model, issue, price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (r_date, r_name, r_phone, r_model, r_issue, r_price, initial_status)
                )
                conn.commit()
                st.success(f"✅ บันทึกรับเครื่องของคุณ {r_name} เรียบร้อยแล้ว")
                
                st.markdown("---")
                st.markdown("### 🖨️ QR Code ใบรับเครื่องซ่อม (สำหรับให้ลูกค้าสแกน)")
                ticket_info = f"ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส\nชื่อลูกค้า: {r_name}\nเบอร์โทร: {r_phone}\nรุ่น: {r_model}\nอาการ: {r_issue}\nสถานะ: รอตรวจสอบ"
                
                qr = qrcode.QRCode(version=1, box_size=8, border=2)
                qr.add_data(ticket_info)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buf = BytesIO()
                img.save(buf, format="PNG")
                st.image(buf.getvalue(), width=200, caption=f"QR Code ข้อมูลงานซ่อม: {r_name}")
            else:
                st.error("กรุณากรอกชื่อและเบอร์โทรศัพท์ลูกค้าให้ครบถ้วน")
                
    with tab2:
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            st.dataframe(repairs_df, use_container_width=True)
            
            st.markdown("### ⚙️ อัปเดตสถานะงานซ่อมด่วน")
            repair_ids = repairs_df["id"].tolist()
            selected_repair_id = st.selectbox("เลือกรหัสงานซ่อมที่ต้องการอัปเดต", repair_ids)
            
            current_status_row = repairs_df[repairs_df["id"] == selected_repair_id].iloc[0]
            st.info(f"ลูกค้า: {current_status_row['customer']} | รุ่น: {current_status_row['model']} | สถานะปัจจุบัน: **{current_status_row['status']}**")
            
            new_status = st.selectbox("เปลี่ยนสถานะเป็น", ["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"])
            if st.button("อัปเดตสถานะงานซ่อม"):
                cursor.execute("UPDATE repairs SET status = ? WHERE id = ?", (new_status, selected_repair_id))
                conn.commit()
                st.success("อัปเดตสถานะสำเร็จ!")
                st.rerun()

# ----------------------------------------------------
# 4. สรุปยอดขายรายวัน
# ----------------------------------------------------
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

# ----------------------------------------------------
# 5. ระบบหลังบ้าน (Admin / แก้ไขและจัดการข้อมูล)
# ----------------------------------------------------
elif menu == "⚙️ ระบบหลังบ้าน (Admin / แก้ไขข้อมูล)":
    st.subheader("⚙️ ระบบหลังบ้าน - บริหารจัดการและแก้ไขข้อมูล")
    
    admin_tab1, admin_tab2 = st.tabs(["📦 แก้ไข/ลบ ข้อมูลสินค้าในสต็อก", "📝 แก้ไข/ลบ ข้อมูลงานซ่อม"])
    
    # --- Tab 1: จัดการสต็อกสินค้า ---
    with admin_tab1:
        st.markdown("### ✏️ แก้ไขข้อมูล หรือ ลบสินค้าในคลัง")
        inv_df = pd.read_sql("SELECT * FROM inventory", conn)
        
        if not inv_df.empty:
            selected_item_name = st.selectbox("เลือกสินค้าที่ต้องการจัดการ", inv_df["name"].tolist(), key="admin_inv_select")
            item_info = inv_df[inv_df["name"] == selected_item_name].iloc[0]
            
            with st.form("edit_inventory_form"):
                ed_code = st.text_input("รหัสสินค้า", value=item_info["code"])
                ed_name = st.text_input("ชื่อสินค้า", value=item_info["name"])
                ed_category = st.text_input("ประเภท", value=item_info["category"])
                ed_qty = st.number_input("จำนวนคงเหลือในสต็อก", min_value=0, value=int(item_info["qty"]))
                ed_price = st.number_input("ราคาขาย (บาท)", min_value=0.0, value=float(item_info["price"]))
                
                col_btn1, col_btn2 = st.columns(2)
                update_btn = col_btn1.form_submit_button("💾 บันทึกการแก้ไขข้อมูล")
                delete_btn = col_btn2.form_submit_button("🗑️ ลบสินค้านี้ออกจากระบบ")
                
                if update_btn:
                    cursor.execute(
                        "UPDATE inventory SET code=?, name=?, category=?, qty=?, price=? WHERE id=?",
                        (ed_code, ed_name, ed_category, ed_qty, ed_price, item_info["id"])
                    )
                    conn.commit()
                    st.success(f"อัปเดตข้อมูลสินค้า '{ed_name}' สำเร็จ!")
                    st.rerun()
                    
                if delete_btn:
                    cursor.execute("DELETE FROM inventory WHERE id=?", (item_info["id"],))
                    conn.commit()
                    st.warning(f"ลบสินค้า '{item_info['name']}' ออกจากระบบเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ไม่มีสินค้าในคลัง")

    # --- Tab 2: จัดการงานซ่อม ---
    with admin_tab2:
        st.markdown("### ✏️ แก้ไขข้อมูลรายละเอียดงานซ่อม หรือ ลบรายการซ่อม")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        
        if not repairs_df.empty:
            repair_display_list = [f"ID: {row['id']} | ลูกค้า: {row['customer']} | รุ่น: {row['model']}" for index, row in repairs_df.iterrows()]
            selected_rep_str = st.selectbox("เลือกรายการซ่อมที่ต้องการจัดการ", repair_display_list, key="admin_rep_select")
            
            # ดึง ID ออกมาจากข้อความที่เลือก
            rep_id = int(selected_rep_str.split(" | ")[0].replace("ID: ", ""))
            rep_info = repairs_df[repairs_df["id"] == rep_id].iloc[0]
            
            with st.form("edit_repair_form"):
                ed_cust = st.text_input("ชื่อลูกค้า", value=rep_info["customer"])
                ed_phone = st.text_input("เบอร์โทรศัพท์", value=rep_info["phone"])
                ed_model = st.text_input("รุ่นคอมพิวเตอร์", value=rep_info["model"])
                ed_issue = st.text_area("อาการเสีย", value=rep_info["issue"])
                ed_price = st.number_input("ราคาประเมินซ่อม (บาท)", min_value=0.0, value=float(rep_info["price"]))
                ed_status = st.selectbox("สถานะงานซ่อม", ["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"], index=["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"].index(rep_info["status"]) if rep_info["status"] in ["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"] else 0)
                
                col_r1, col_r2 = st.columns(2)
                update_rep_btn = col_r1.form_submit_button("💾 บันทึกการแก้ไขงานซ่อม")
                delete_rep_btn = col_r2.form_submit_button("🗑️ ลบประวัติงานซ่อมนี้")
                
                if update_rep_btn:
                    cursor.execute(
                        "UPDATE repairs SET customer=?, phone=?, model=?, issue=?, price=?, status=? WHERE id=?",
                        (ed_cust, ed_phone, ed_model, ed_issue, ed_price, ed_status, rep_id)
                    )
                    conn.commit()
                    st.success("อัปเดตข้อมูลงานซ่อมสำเร็จ!")
                    st.rerun()
                    
                if delete_rep_btn:
                    cursor.execute("DELETE FROM repairs WHERE id=?", (rep_id,))
                    conn.commit()
                    st.warning("ลบประวัติงานซ่อมเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ยังไม่มีประวัติงานซ่อมในระบบ")
