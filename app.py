import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import qrcode
from promptpay import qrcode as pp_qrcode
from io import BytesIO
from PIL import Image
import os
import base64

st.set_page_config(page_title="Zone Computer & Service", layout="wide")

# 1. ตั้งค่าฐานข้อมูล SQLite
def init_db():
    conn = sqlite3.connect('computer_shop.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # ตารางสต็อกสินค้า
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
    
    # ตารางประวัติการขาย POS
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
    
    # ตารางงานซ่อม
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

    # ตารางเก็บบันทึกเอกสารทางการ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT,
            doc_no TEXT,
            date TEXT,
            customer TEXT,
            address TEXT,
            tax_id TEXT,
            grand_total REAL
        )
    ''')

    # ตารางตั้งค่าข้อมูลร้านค้าและโลโก้
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT,
            address TEXT,
            tax_id TEXT,
            promptpay TEXT,
            logo_path TEXT
        )
    ''')

    # ตารางจัดการข้อมูลพนักงาน
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            phone TEXT,
            status TEXT
        )
    ''')
    
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# เติมข้อมูลตั้งต้นสต็อกหากว่างเปล่า
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

# เติมข้อมูลตั้งต้นร้านค้าหากว่างเปล่า
cursor.execute('SELECT COUNT(*) FROM shop_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('''
        INSERT INTO shop_settings (shop_name, address, tax_id, promptpay, logo_path)
        VALUES (?, ?, ?, ?, ?)
    ''', ("ร้านโซนคอมพิวเตอร์แอนด์เซอร์วิส", "123/4 ถ.อุปราช ต.ในเมือง อ.เมือง จ.อุบลราชธานี 34000", "1340999999999", "0812345678", ""))
    conn.commit()

# เติมข้อมูลพนักงานตั้งต้นหากว่างเปล่า
cursor.execute('SELECT COUNT(*) FROM staff')
if cursor.fetchone()[0] == 0:
    default_staff = [
        ("ช่างดิด", "ช่างเทคนิค / เจ้าของร้าน", "0812345678", "ปฏิบัติงาน"),
        ("คุณแอดมิน", "ฝ่ายขายและบริการหน้าร้าน", "0898765432", "ปฏิบัติงาน")
    ]
    cursor.executemany("INSERT INTO staff (name, role, phone, status) VALUES (?, ?, ?, ?)", default_staff)
    conn.commit()

# ดึงข้อมูลร้านค้าปัจจุบันจากฐานข้อมูล
cursor.execute('SELECT shop_name, address, tax_id, promptpay, logo_path FROM shop_settings WHERE id=1')
shop_info = cursor.fetchone()
shop_name, shop_address, shop_tax_id, shop_promptpay, shop_logo_path = shop_info

st.title(f"💻 {shop_name} (Online POS & Document System)")

# เมนูหลักด้านข้าง
menu = st.sidebar.selectbox(
    "เลือกเมนูการทำงาน", 
    [
        "🛒 ระบบขายหน้าร้าน (POS & QR ชำระเงิน)", 
        "📄 ระบบออกเอกสารทางการ",
        "📦 จัดการสต็อกสินค้า",
        "📝 ระบบรับและติดตามงานซ่อม",
        "📊 สรุปยอดขายรายวัน",
        "⚙️ ระบบหลังบ้าน (Admin & ตั้งค่าระบบ)"
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
            st.error(f"ไม่สามารถสร้าง QR Code ได้ กรุณาตรวจสอบเบอร์พร้อมเพย์ที่ระบบหลังบ้าน (Error: {e})")

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
# 2. ระบบออกเอกสารทางการ (แยกประเภทเอกสารชัดเจน)
# ----------------------------------------------------
elif menu == "📄 ระบบออกเอกสารทางการ":
    st.subheader("📄 ระบบออกเอกสารทางการ (ใบเสนอราคา / ใบส่งสินค้า / ใบกำกับภาษี / ใบเสร็จรับเงิน)")
    
    doc_type = st.selectbox(
        "เลือกประเภทเอกสารที่ต้องการออก",
        [
            "ใบเสนอราคา (Quotation)",
            "ใบส่งสินค้า / ใบส่งของ (Delivery Note)",
            "ใบกำกับภาษี (Tax Invoice)",
            "ใบเสร็จรับเงิน (Receipt)"
        ]
    )
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        c_name = st.text_input("ชื่อลูกค้า / บริษัท", value="บริษัท ลูกค้าตัวอย่าง จำกัด")
        c_address = st.text_area("ที่อยู่ลูกค้า", value="99/9 ถ.สุขุมวิท กรุงเทพฯ")
    with col2:
        c_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษีลูกค้า (ถ้ามี)", value="0105555555555")
        doc_date = st.date_input("วันที่เอกสาร", datetime.now())
        
        # กำหนด Prefix เลขที่เอกสารตามประเภทที่เลือก
        prefix_dict = {
            "ใบเสนอราคา (Quotation)": "QT",
            "ใบส่งสินค้า / ใบส่งของ (Delivery Note)": "DL",
            "ใบกำกับภาษี (Tax Invoice)": "TX",
            "ใบเสร็จรับเงิน (Receipt)": "RC"
        }
        default_doc_no = f"{prefix_dict[doc_type]}-{datetime.now().strftime('%Y%m%d%H%M')}"
        doc_no = st.text_input("เลขที่เอกสาร", value=default_doc_no)

    st.markdown("### 🛒 รายการสินค้าในเอกสาร")
    
    inv_df = pd.read_sql("SELECT * FROM inventory", conn)
    item_options = inv_df["name"].tolist()
    
    selected_doc_item = st.selectbox("เลือกสินค้าจากคลัง", item_options, key="doc_item_sel")
    item_row = inv_df[inv_df["name"] == selected_doc_item].iloc[0]
    
    doc_price = st.number_input("ราคาต่อหน่วย (บาท)", min_value=0.0, value=float(item_row["price"]), key="doc_p")
    doc_qty = st.number_input("จำนวน", min_value=1, value=1, key="doc_q")
    
    item_total = doc_price * doc_qty
    
    if 'doc_items' not in st.session_state:
        st.session_state.doc_items = []
        
    if st.button("➕ เพิ่มรายการนี้ลงในเอกสาร"):
        st.session_state.doc_items.append({
            "name": selected_doc_item,
            "price": doc_price,
            "qty": doc_qty,
            "total": item_total
        })
        st.success("เพิ่มรายการสำเร็จ!")
        
    if len(st.session_state.doc_items) > 0:
        df_items_display = pd.DataFrame(st.session_state.doc_items)
        st.dataframe(df_items_display, use_container_width=True)
        
        if st.button("🗑️ ล้างรายการทั้งหมด"):
            st.session_state.doc_items = []
            st.rerun()
            
        sub_sum = df_items_display["total"].sum()
        
        # ตั้งค่าคำนวณ VAT 7% เป็นค่าเริ่มต้นเฉพาะกรณี "ใบกำกับภาษี"
        default_vat_status = True if doc_type == "ใบกำกับภาษี (Tax Invoice)" else False
        include_vat = st.checkbox("คำนวณ VAT 7% (ภาษีมูลค่าเพิ่ม)", value=default_vat_status)
        
        if include_vat:
            vat_amount = sub_sum * 0.07
            grand_total = sub_sum + vat_amount
        else:
            vat_amount = 0.0
            grand_total = sub_sum
            
        st.markdown(f"**รวมเป็นเงิน (Subtotal):** {sub_sum:,.2f} บาท")
        if include_vat:
            st.markdown(f"**ภาษีมูลค่าเพิ่ม VAT 7%:** {vat_amount:,.2f} บาท")
        st.markdown(f"### **ยอดรวมสุทธิทั้งสิ้น (Grand Total): {grand_total:,.2f} บาท**")
        
        if st.button("💾 บันทึกและแสดงตัวอย่างเอกสารทางการ"):
            cursor.execute(
                "INSERT INTO documents (doc_type, doc_no, date, customer, address, tax_id, grand_total) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (doc_type, doc_no, str(doc_date), c_name, c_address, c_tax_id, grand_total)
            )
            conn.commit()
            st.success("บันทึกเอกสารเข้าระบบเรียบร้อย!")
            
            st.markdown("---")
            
            logo_html = ""
            if shop_logo_path and os.path.exists(shop_logo_path):
                with open(shop_logo_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                logo_html = f'<img src="data:image/png;base64,{encoded_string}" style="max-height: 70px; margin-bottom: 5px;"><br>'

            vat_row_html = f"<tr><td><b>VAT 7%:</b></td><td style='text-align: right;'>{vat_amount:,.2f} บาท</td></tr>" if include_vat else ""

            st.markdown(f"""
            <div style="border: 2px solid #333; padding: 25px; border-radius: 8px; background-color: #fff; color: #000;">
                <div style="text-align: center;">
                    {logo_html}
                    <h2 style="margin: 0;">{shop_name}</h2>
                    <p style="font-size: 13px; color: #555; margin: 2px 0;">{shop_address} | โทร. {shop_promptpay} | เลขประจำตัวผู้เสียภาษี: {shop_tax_id}</p>
                </div>
                <hr style="border: 1px solid #333; margin: 15px 0;">
                <h3 style="text-align: center; background-color: #eee; padding: 5px;">{doc_type.upper()}</h3>
                
                <table style="width: 100%; margin-bottom: 15px; font-size: 14px;">
                    <tr>
                        <td style="width: 60%;"><b>นามลูกค้า:</b> {c_name}<br><b>ที่อยู่:</b> {c_address}<br><b>เลขประจำตัวผู้เสียภาษี:</b> {c_tax_id}</td>
                        <td style="width: 40%; text-align: right;"><b>เลขที่เอกสาร:</b> {doc_no}<br><b>วันที่:</b> {doc_date}</td>
                    </tr>
                </table>
                
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
                    <thead>
                        <tr style="background-color: #333; color: #fff;">
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">ลำดับ</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">รายการสินค้า / บริการ</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: center;">จำนวน</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">ราคาต่อหน่วย</th>
                            <th style="border: 1px solid #ddd; padding: 8px; text-align: right;">จำนวนเงิน</th>
                        </tr>
                    </thead>
                    <tbody>
            """, unsafe_allow_html=True)
            
            for idx, row in df_items_display.iterrows():
                st.markdown(f"""
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 8px;">{idx+1}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{row['name']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{row['qty']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{row['price']:,.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">{row['total']:,.2f}</td>
                    </tr>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
                    </tbody>
                </table>
                
                <div style="float: right; width: 350px; font-size: 14px;">
                    <table style="width: 100%;">
                        <tr><td><b>รวมเป็นเงิน:</b></td><td style="text-align: right;">{sub_sum:,.2f} บาท</td></tr>
                        {vat_row_html}
                        <tr style="font-size: 16px; border-top: 1px solid #333;"><td><b>ยอดรวมสุทธิ:</b></td><td style="text-align: right;"><b>{grand_total:,.2f} บาท</b></td></tr>
                    </table>
                </div>
                <div style="clear: both;"></div>
                
                <br><br>
                <table style="width: 100%; text-align: center; font-size: 13px; margin-top: 40px;">
                    <tr>
                        <td>____________________________________<br>ผู้จัดทำ / Authorized Signature</td>
                        <td>____________________________________<br>ผู้รับสินค้า / Received By</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            st.info("💡 สามารถกดสั่งพิมพ์ (Print) หน้านี้ผ่านเบราว์เซอร์เพื่อพิมพ์ออกเครื่องพิมพ์ A4 ได้ทันทีครับ")

# ----------------------------------------------------
# 3. จัดการสต็อกสินค้า
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
# 4. ระบบรับและติดตามงานซ่อม
# ----------------------------------------------------
elif menu == "📝 ระบบรับและติดตามงานซ่อม":
    st.subheader("📝 ระบบจัดการงานซ่อม (รับเครื่อง & ติดตามสถานะ)")
    
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
                ticket_info = f"{shop_name}\nชื่อลูกค้า: {r_name}\nเบอร์โทร: {r_phone}\nรุ่น: {r_model}\nอาการ: {r_issue}\nสถานะ: รอตรวจสอบ"
                
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
            
            st.markdown("### ⚙️ อัปเดตสถานะงานซ่อม")
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
# 5. สรุปยอดขายรายวัน
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
# 6. ระบบหลังบ้าน (Admin & Management Hub)
# ----------------------------------------------------
elif menu == "⚙️ ระบบหลังบ้าน (Admin & ตั้งค่าระบบ)":
    st.subheader("⚙️ ระบบหลังบ้าน - จัดการร้านค้า สินค้า งานซ่อม และพนักงาน")
    
    b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs([
        "🏪 ตั้งค่าข้อมูลร้านค้า & โลโก้", 
        "📦 จัดการสต็อกสินค้า", 
        "📝 จัดการงานซ่อม", 
        "👥 จัดการพนักงาน"
    ])
    
    # --- Tab 1: ตั้งค่าร้านค้า & โลโก้ ---
    with b_tab1:
        st.markdown("### 🏪 ตั้งค่าชื่อร้าน ที่อยู่ โลโก้ และช่องทางชำระเงิน")
        col_l1, col_l2 = st.columns([1, 2])
        
        with col_l1:
            st.markdown("#### โลโก้ร้านปัจจุบัน")
            if shop_logo_path and os.path.exists(shop_logo_path):
                st.image(shop_logo_path, width=200, caption="โลโก้ร้านค้า")
            else:
                st.info("ยังไม่มีการอัปโหลดโลโก้ร้านค้า")
            uploaded_logo = st.file_uploader("อัปโหลดโลโก้ใหม่ (PNG/JPG)", type=["png", "jpg", "jpeg"], key="admin_logo_up")
            
        with col_l2:
            with st.form("shop_setting_form"):
                new_shop_name = st.text_input("ชื่อร้านค้า", value=shop_name)
                new_address = st.text_area("ที่อยู่ร้านค้า", value=shop_address)
                new_tax_id = st.text_input("เลขประจำตัวผู้เสียภาษี", value=shop_tax_id)
                new_promptpay = st.text_input("เบอร์พร้อมเพย์ (สำหรับรับเงิน POS)", value=shop_promptpay)
                
                save_shop_btn = st.form_submit_button("💾 บันทึกการเปลี่ยนแปลงข้อมูลร้าน")
                
                if save_shop_btn:
                    saved_path = shop_logo_path
                    if uploaded_logo is not None:
                        saved_path = "shop_logo.png"
                        img = Image.open(uploaded_logo)
                        img.save(saved_path)
                    
                    cursor.execute('''
                        UPDATE shop_settings 
                        SET shop_name=?, address=?, tax_id=?, promptpay=?, logo_path=? 
                        WHERE id=1
                    ''', (new_shop_name, new_address, new_tax_id, new_promptpay, saved_path))
                    conn.commit()
                    st.success("บันทึกข้อมูลร้านค้าและโลโก้สำเร็จ! กำลังรีเฟรช...")
                    st.rerun()

    # --- Tab 2: จัดการสต็อกสินค้า ---
    with b_tab2:
        st.markdown("### 📦 แก้ไข หรือ ลบรายการสินค้าในคลัง")
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
                    cursor.execute("UPDATE inventory SET code=?, name=?, category=?, qty=?, price=? WHERE id=?", (ed_code, ed_name, ed_category, ed_qty, ed_price, item_info["id"]))
                    conn.commit()
                    st.success("อัปเดตข้อมูลสินค้าสำเร็จ!")
                    st.rerun()
                if delete_btn:
                    cursor.execute("DELETE FROM inventory WHERE id=?", (item_info["id"],))
                    conn.commit()
                    st.warning("ลบสินค้าเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ไม่มีสินค้าในคลัง")

    # --- Tab 3: จัดการงานซ่อม ---
    with b_tab3:
        st.markdown("### 📝 แก้ไขรายละเอียด หรือ ลบประวัติงานซ่อม")
        repairs_df = pd.read_sql("SELECT * FROM repairs", conn)
        if not repairs_df.empty:
            repair_display_list = [f"ID: {row['id']} | ลูกค้า: {row['customer']} | รุ่น: {row['model']}" for index, row in repairs_df.iterrows()]
            selected_rep_str = st.selectbox("เลือกรายการซ่อมที่ต้องการจัดการ", repair_display_list, key="admin_rep_select")
            rep_id = int(selected_rep_str.split(" | ")[0].replace("ID: ", ""))
            rep_info = repairs_df[repairs_df["id"] == rep_id].iloc[0]
            
            with st.form("edit_repair_form"):
                ed_cust = st.text_input("ชื่อร้าน/ลูกค้า", value=rep_info["customer"])
                ed_phone = st.text_input("เบอร์โทรศัพท์", value=rep_info["phone"])
                ed_model = st.text_input("รุ่นคอมพิวเตอร์", value=rep_info["model"])
                ed_issue = st.text_area("อาการเสีย", value=rep_info["issue"])
                ed_price = st.number_input("ราคาประเมินซ่อม (บาท)", min_value=0.0, value=float(rep_info["price"]))
                ed_status = st.selectbox("สถานะงานซ่อม", ["รอตรวจสอบ", "กำลังดำเนินการซ่อม", "ซ่อมเสร็จรอรับเครื่อง", "ส่งมอบเรียบร้อย"])
                
                col_r1, col_r2 = st.columns(2)
                update_rep_btn = col_r1.form_submit_button("💾 บันทึกการแก้ไขงานซ่อม")
                delete_rep_btn = col_r2.form_submit_button("🗑️ ลบประวัติงานซ่อมนี้")
                
                if update_rep_btn:
                    cursor.execute("UPDATE repairs SET customer=?, phone=?, model=?, issue=?, price=?, status=? WHERE id=?", (ed_cust, ed_phone, ed_model, ed_issue, ed_price, ed_status, rep_id))
                    conn.commit()
                    st.success("อัปเดตงานซ่อมสำเร็จ!")
                    st.rerun()
                if delete_rep_btn:
                    cursor.execute("DELETE FROM repairs WHERE id=?", (rep_id,))
                    conn.commit()
                    st.warning("ลบประวัติงานซ่อมเรียบร้อยแล้ว!")
                    st.rerun()
        else:
            st.info("ยังไม่มีประวัติงานซ่อมในระบบ")

    # --- Tab 4: จัดการพนักงาน ---
    with b_tab4:
        st.markdown("### 👥 ระบบจัดการข้อมูลพนักงานในร้าน")
        
        staff_df = pd.read_sql("SELECT * FROM staff", conn)
        st.dataframe(staff_df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### ➕ เพิ่มพนักงานใหม่ / ✏️ แก้ไขข้อมูลพนักงาน")
        
        staff_action = st.radio("เลือกการทำงาน", ["เพิ่มพนักงานใหม่", "แก้ไข/ลบ พนักงานที่มีอยู่"], horizontal=True)
        
        if staff_action == "เพิ่มพนักงานใหม่":
            with st.form("add_staff_form"):
                st_name = st.text_input("ชื่อ-นามสกุลพนักงาน")
                st_role = st.text_input("ตำแหน่ง (เช่น ช่างเทคนิค, ฝ่ายขาย)")
                st_phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
                st_status = st.selectbox("สถานะการทำงาน", ["ปฏิบัติงาน", "ลาพักผ่อน", "ลาออก"])
                
                add_staff_btn = st.form_submit_button("💾 บันทึกเพิ่มพนักงานใหม่")
                if add_staff_btn:
                    if st_name and st_phone:
                        cursor.execute("INSERT INTO staff (name, role, phone, status) VALUES (?, ?, ?, ?)", (st_name, st_role, st_phone, st_status))
                        conn.commit()
                        st.success(f"เพิ่มพนักงาน '{st_name}' สำเร็จ!")
                        st.rerun()
                    else:
                        st.error("กรุณากรอกชื่อและเบอร์โทรศัพท์ให้ครบถ้วน")
        else:
            if not staff_df.empty:
                st_list = [f"ID: {row['id']} | ชื่อ: {row['name']} ({row['role']})" for index, row in staff_df.iterrows()]
                selected_st_str = st.selectbox("เลือกพนักงานที่ต้องการจัดการ", st_list)
                st_id = int(selected_st_str.split(" | ")[0].replace("ID: ", ""))
                st_info = staff_df[staff_df["id"] == st_id].iloc[0]
                
                with st.form("edit_staff_form"):
                    ed_st_name = st.text_input("ชื่อ-นามสกุลพนักงาน", value=st_info["name"])
                    ed_st_role = st.text_input("ตำแหน่ง", value=st_info["role"])
                    ed_st_phone = st.text_input("เบอร์โทรศัพท์", value=st_info["phone"])
                    ed_st_status = st.selectbox("สถานะการทำงาน", ["ปฏิบัติงาน", "ลาพักผ่อน", "ลาออก"], index=["ปฏิบัติงาน", "ลาพักผ่อน", "ลาออก"].index(st_info["status"]) if st_info["status"] in ["ปฏิบัติงาน", "ลาพักผ่อน", "ลาออก"] else 0)
                    
                    col_s1, col_s2 = st.columns(2)
                    up_staff_btn = col_s1.form_submit_button("💾 บันทึกการแก้ไขข้อมูลพนักงาน")
                    del_staff_btn = col_s2.form_submit_button("🗑️ ลบพนักงานนี้ออกจากระบบ")
                    
                    if up_staff_btn:
                        cursor.execute("UPDATE staff SET name=?, role=?, phone=?, status=? WHERE id=?", (ed_st_name, ed_st_role, ed_st_phone, ed_st_status, st_id))
                        conn.commit()
                        st.success("อัปเดตข้อมูลพนักงานสำเร็จ!")
                        st.rerun()
                    if del_staff_btn:
                        cursor.execute("DELETE FROM staff WHERE id=?", (st_id,))
                        conn.commit()
                        st.warning("ลบข้อมูลพนักงานเรียบร้อยแล้ว!")
                        st.rerun()
            else:
                st.info("ยังไม่มีข้อมูลพนักงานในระบบ")