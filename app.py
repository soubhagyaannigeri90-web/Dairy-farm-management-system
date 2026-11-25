import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

DB = "dairy_farm.db"
st.set_page_config(page_title="Dairy Farm Management System", page_icon="🐄", layout="wide")

def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def setup():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS animals(
            animal_id TEXT PRIMARY KEY, name TEXT, animal_type TEXT NOT NULL,
            breed TEXT, age REAL, purchase_date TEXT, health_status TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS milk(
            id INTEGER PRIMARY KEY AUTOINCREMENT, animal_id TEXT NOT NULL,
            record_date TEXT NOT NULL, session TEXT NOT NULL, litres REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feed(
            id INTEGER PRIMARY KEY AUTOINCREMENT, record_date TEXT NOT NULL,
            animal_id TEXT, feed_type TEXT NOT NULL, quantity REAL NOT NULL,
            unit TEXT NOT NULL, cost REAL NOT NULL, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS health(
            id INTEGER PRIMARY KEY AUTOINCREMENT, animal_id TEXT NOT NULL,
            record_date TEXT NOT NULL, record_type TEXT NOT NULL,
            description TEXT, next_due_date TEXT, cost REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT, sale_date TEXT NOT NULL,
            customer TEXT NOT NULL, litres REAL NOT NULL,
            rate REAL NOT NULL, total REAL NOT NULL, payment_status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, expense_date TEXT NOT NULL,
            category TEXT NOT NULL, description TEXT, amount REAL NOT NULL
        );
        """)
        con.commit()

def run(sql, params=()):
    with connect() as con:
        con.execute(sql, params)
        con.commit()

def df(sql, params=()):
    with connect() as con:
        return pd.read_sql_query(sql, con, params=params)

def download_csv(data, filename, label):
    if not data.empty:
        st.download_button(label, data.to_csv(index=False).encode("utf-8"),
                           filename, "text/csv")

setup()
today = date.today().isoformat()
st.title("🐄 Dairy Farm Management System")
st.caption("A centralized digital platform for managing dairy farm activities.")

menu = st.sidebar.radio("MAIN MENU", [
    "Dashboard", "Animal Management", "Milk Production", "Feed Management",
    "Health & Vaccination", "Milk Sales", "Expense Management",
    "Income & Profit", "Reports", "Database Backup"
])

animals = df("SELECT animal_id FROM animals ORDER BY animal_id")
animal_ids = animals["animal_id"].tolist()

# Dashboard
if menu == "Dashboard":
    st.header("Farm Overview")
    animal_count = len(animal_ids)
    milk_today = df("SELECT COALESCE(SUM(litres),0) v FROM milk WHERE record_date=?", (today,)).iloc[0]["v"]
    sales_today = df("SELECT COALESCE(SUM(total),0) v FROM sales WHERE sale_date=?", (today,)).iloc[0]["v"]
    feed_today = df("SELECT COALESCE(SUM(cost),0) v FROM feed WHERE record_date=?", (today,)).iloc[0]["v"]
    other_exp = df("SELECT COALESCE(SUM(amount),0) v FROM expenses WHERE expense_date=?", (today,)).iloc[0]["v"]
    a,b,c,d,e = st.columns(5)
    a.metric("Animals", animal_count)
    b.metric("Milk Today", f"{milk_today:.1f} L")
    c.metric("Sales Today", f"₹{sales_today:,.0f}")
    d.metric("Feed Cost Today", f"₹{feed_today:,.0f}")
    e.metric("Other Expenses", f"₹{other_exp:,.0f}")

    st.subheader("Recent Milk Records")
    recent = df("""SELECT record_date Date, animal_id Animal, session Session, litres Litres
                   FROM milk ORDER BY id DESC LIMIT 8""")
    st.dataframe(recent, use_container_width=True)
    st.subheader("Upcoming Vaccinations / Health Follow-ups")
    upcoming = df("""SELECT animal_id Animal, record_type Type, description Details,
                            next_due_date Due_Date
                     FROM health WHERE next_due_date IS NOT NULL
                     AND next_due_date >= ? ORDER BY next_due_date LIMIT 10""", (today,))
    st.dataframe(upcoming, use_container_width=True)

# Animal management
elif menu == "Animal Management":
    st.header("🐄 Animal Management")
    t1,t2,t3 = st.tabs(["Add Animal","View Animals","Update / Delete"])
    with t1:
        with st.form("animal_add"):
            aid = st.text_input("Animal ID (e.g. C001)").strip().upper()
            name = st.text_input("Animal Name (optional)")
            typ = st.selectbox("Animal Type", ["Cow","Buffalo","Other"])
            breed = st.text_input("Breed")
            age = st.number_input("Age in years", 0.0, 30.0, 2.0, 0.5)
            pdate = st.date_input("Purchase Date")
            status = st.selectbox("Health Status", ["Healthy","Under Treatment","Pregnant","Other"])
            notes = st.text_area("Additional Notes")
            if st.form_submit_button("Save Animal"):
                if not aid:
                    st.error("Animal ID is required.")
                else:
                    try:
                        run("INSERT INTO animals VALUES(?,?,?,?,?,?,?,?)",
                            (aid,name,typ,breed,age,pdate.isoformat(),status,notes))
                        st.success("Animal saved.")
                    except sqlite3.IntegrityError:
                        st.error("Animal ID already exists.")
    with t2:
        data = df("SELECT * FROM animals ORDER BY animal_id")
        st.dataframe(data, use_container_width=True)
        download_csv(data,"animals.csv","Download animal records")
    with t3:
        if not animal_ids:
            st.info("No animals registered.")
        else:
            aid = st.selectbox("Choose animal", animal_ids, key="animal_edit")
            old = df("SELECT * FROM animals WHERE animal_id=?", (aid,)).iloc[0]
            with st.form("animal_update"):
                breed2 = st.text_input("Breed", str(old["breed"] or ""))
                age2 = st.number_input("Age", 0.0, 30.0, float(old["age"] or 0))
                status2 = st.selectbox("Health Status",
                    ["Healthy","Under Treatment","Pregnant","Other"],
                    index=["Healthy","Under Treatment","Pregnant","Other"].index(
                        old["health_status"] if old["health_status"] in
                        ["Healthy","Under Treatment","Pregnant","Other"] else "Other"))
                if st.form_submit_button("Update"):
                    run("UPDATE animals SET breed=?,age=?,health_status=? WHERE animal_id=?",
                        (breed2,age2,status2,aid))
                    st.success("Animal updated.")
            if st.button("Delete animal", key="delete_animal"):
                run("DELETE FROM animals WHERE animal_id=?", (aid,))
                st.warning("Animal deleted. Historical records are retained.")

# Milk production
# Milk production
elif menu == "Milk Production":
    st.header("🥛 Milk Production")

    if not animal_ids:
        st.warning("Register animals first.")
    else:
        st.subheader("Add Milk Production")

        with st.form("milk_add"):
            aid = st.selectbox("Animal", animal_ids)
            rdate = st.date_input("Production Date", value=date.today())
            session = st.selectbox("Session", ["Morning", "Evening"])
            litres = st.number_input(
                "Milk quantity (litres)", min_value=0.0, step=0.5
            )

            save = st.form_submit_button("Save Production")

            if save:
                if litres <= 0:
                    st.error("Enter a quantity greater than zero.")
                else:
                    existing = df(
                        """SELECT id FROM milk
                           WHERE animal_id=? AND record_date=? AND session=?""",
                        (aid, rdate.isoformat(), session)
                    )

                    if not existing.empty:
                        st.error(
                            "This animal already has a record for this date "
                            "and session. Edit the existing record below."
                        )
                    else:
                        run(
                            """INSERT INTO milk
                               (animal_id, record_date, session, litres)
                               VALUES (?, ?, ?, ?)""",
                            (aid, rdate.isoformat(), session, litres)
                        )
                        st.success("Milk record saved successfully.")
                        st.rerun()

        st.divider()

        # Select date to view and edit
        st.subheader("View and Edit Milk Records")

        selected_date = st.date_input(
            "Select date to view or edit records",
            value=date.today(),
            key="milk_selected_date"
        )

        selected_day = selected_date.isoformat()

        data = df(
            """SELECT id, animal_id, record_date, session, litres
               FROM milk
               WHERE record_date=?
               ORDER BY id""",
            (selected_day,)
        )

        if data.empty:
            st.info("No milk records found for this date.")
        else:
            st.write(
                "Click the Session or Litres cells to edit them. "
                "Then click Save Changes."
            )

            editable_data = data.rename(columns={
                "id": "ID",
                "animal_id": "Animal ID",
                "record_date": "Record Date",
                "session": "Session",
                "litres": "Litres"
            })

            edited_data = st.data_editor(
                editable_data,
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=["ID", "Animal ID", "Record Date"],
                column_config={
                    "Session": st.column_config.SelectboxColumn(
                        "Session",
                        options=["Morning", "Evening"],
                        required=True
                    ),
                    "Litres": st.column_config.NumberColumn(
                        "Litres",
                        min_value=0.01,
                        step=0.5,
                        format="%.2f"
                    )
                },
                key="milk_editable_table"
            )

            if st.button("Save Changes", type="primary"):
                # Check for duplicate animal/date/session combinations
                duplicate = edited_data.duplicated(
                    subset=["Animal ID", "Record Date", "Session"],
                    keep=False
                )

                if duplicate.any():
                    st.error(
                        "Duplicate session found. An animal cannot have "
                        "two records for the same date and session."
                    )

                elif (edited_data["Litres"] <= 0).any():
                    st.error("Litres must be greater than zero.")

                else:
                    try:
                        with connect() as con:
                            for _, row in edited_data.iterrows():
                                con.execute(
                                    """UPDATE milk
                                       SET session=?, litres=?
                                       WHERE id=?""",
                                    (
                                        row["Session"],
                                        float(row["Litres"]),
                                        int(row["ID"])
                                    )
                                )

                        st.success("Milk records updated successfully!")
                        st.rerun()

                    except sqlite3.Error as error:
                        st.error(f"Unable to update records: {error}")

            # Automatic calculations for selected date
            st.subheader("Daily Milk Calculation")

            morning_total = data.loc[
                data["session"] == "Morning", "litres"
            ].sum()

            evening_total = data.loc[
                data["session"] == "Evening", "litres"
            ].sum()

            total_litres = morning_total + evening_total

            a, b, c = st.columns(3)
            a.metric("Morning Milk", f"{morning_total:.2f} L")
            b.metric("Evening Milk", f"{evening_total:.2f} L")
            c.metric("Total Milk", f"{total_litres:.2f} L")

            download_csv(
                data,
                "milk_production.csv",
                "Download selected date's milk records"
            )

# Feed management
elif menu == "Feed Management":
    st.header("🌾 Feed Management")

    if not animal_ids:
        st.warning("Register animals first.")
    else:
        # 1. ADD NEW FEED RECORD
        st.subheader("➕ Add Feed Record")

        with st.form("feed_add_form"):
            col1, col2 = st.columns(2)

            with col1:
                feed_animal = st.selectbox("Animal ID", animal_ids)
                feed_date = st.date_input("Feed Date")
                feed_name = st.text_input("Feed Name / Type")

            with col2:
                feed_quantity = st.number_input(
                    "Quantity", min_value=0.0, step=0.5
                )
                feed_unit = st.selectbox(
                    "Unit", ["kg", "grams", "litres", "bags", "packets"]
                )
                feed_cost = st.number_input(
                    "Feed Cost (₹)", min_value=0.0, step=10.0
                )

            feed_notes = st.text_area("Notes")

            save_feed = st.form_submit_button("💾 Save Feed Record")

            if save_feed:
                if not feed_name.strip():
                    st.error("Please enter the feed name.")
                elif feed_quantity <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    run(
                        """INSERT INTO feed
                        (record_date, animal_id, feed_type,
                         quantity, unit, cost, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            feed_date.isoformat(),
                            feed_animal,
                            feed_name.strip(),
                            feed_quantity,
                            feed_unit,
                            feed_cost,
                            feed_notes
                        )
                    )
                    st.success("Feed record saved successfully!")
                    st.rerun()

        st.divider()

        # 2. VIEW FEED RECORDS BY DATE
        st.subheader("📋 Saved Feed Records")

        selected_feed_date = st.date_input(
            "Select date to view or edit feed records",
            value=date.today(),
            key="feed_view_date"
        )

        selected_day = selected_feed_date.isoformat()

        feed_data = df(
            """SELECT id, record_date, animal_id, feed_type,
                      quantity, unit, cost, notes
               FROM feed
               WHERE record_date = ?
               ORDER BY id DESC""",
            (selected_day,)
        )

        if feed_data.empty:
            st.info("No feed records found for this date.")
        else:
            # 3. MAKE THE SAVED TABLE EDITABLE
            st.write("Edit the details directly in the table.")
            
            editable_feed = feed_data.copy()
            editable_feed["Delete"] = False

            edited_feed = st.data_editor(
                editable_feed,
                use_container_width=True,
                hide_index=True,
                key=f"feed_editor_{selected_day}",
                column_config={
                    "id": st.column_config.NumberColumn(
                        "ID",
                        disabled=True
                    ),
                    "record_date": st.column_config.TextColumn(
                        "Feed Date"
                    ),
                    "animal_id": st.column_config.SelectboxColumn(
                        "Animal ID",
                        options=animal_ids
                    ),
                    "feed_type": st.column_config.TextColumn(
                        "Feed Name / Type"
                    ),
                    "quantity": st.column_config.NumberColumn(
                        "Quantity",
                        min_value=0.01,
                        step=0.5
                    ),
                    "unit": st.column_config.SelectboxColumn(
                        "Unit",
                        options=[
                            "kg", "grams", "litres",
                            "bags", "packets"
                        ]
                    ),
                    "cost": st.column_config.NumberColumn(
                        "Cost (₹)",
                        min_value=0.0,
                        step=10.0
                    ),
                    "notes": st.column_config.TextColumn("Notes"),
                    "Delete": st.column_config.CheckboxColumn(
                        "Select to Delete",
                        default=False
                    )
                },
                disabled=["id"]
            )

            st.caption(
                "To edit: change the required cells and click Save Changes. "
                "To delete: tick the Delete box and click Delete Selected."
            )

            col1, col2 = st.columns(2)

            # 4. SAVE EDITED RECORDS
            with col1:
                if st.button("💾 Save Changes", key="save_feed_changes"):
                    valid = True

                    for _, row in edited_feed.iterrows():
                        if bool(row["Delete"]):
                            continue

                        if (
                            not str(row["feed_type"]).strip()
                            or float(row["quantity"]) <= 0
                            or float(row["cost"]) < 0
                            or str(row["animal_id"]) not in animal_ids
                        ):
                            valid = False
                            break

                    if not valid:
                        st.error(
                            "Check the feed name, animal, quantity "
                            "and cost before saving."
                        )
                    else:
                        with connect() as con:
                            for _, row in edited_feed.iterrows():
                                if bool(row["Delete"]):
                                    continue

                                con.execute(
                                    """UPDATE feed
                                       SET record_date=?,
                                           animal_id=?,
                                           feed_type=?,
                                           quantity=?,
                                           unit=?,
                                           cost=?,
                                           notes=?
                                       WHERE id=?""",
                                    (
                                        str(row["record_date"]),
                                        str(row["animal_id"]),
                                        str(row["feed_type"]).strip(),
                                        float(row["quantity"]),
                                        str(row["unit"]),
                                        float(row["cost"]),
                                        "" if pd.isna(row["notes"])
                                        else str(row["notes"]),
                                        int(row["id"])
                                    )
                                )

                        st.success("Feed records updated successfully!")
                        st.rerun()

            # 5. DELETE SELECTED RECORDS
            with col2:
                if st.button(
                    "🗑️ Delete Selected",
                    key="delete_feed_records"
                ):
                    delete_ids = edited_feed.loc[
                        edited_feed["Delete"] == True, "id"
                    ].tolist()

                    if not delete_ids:
                        st.warning("Please tick at least one Delete box.")
                    else:
                        with connect() as con:
                            for record_id in delete_ids:
                                con.execute(
                                    "DELETE FROM feed WHERE id=?",
                                    (int(record_id),)
                                )

                        st.success(
                            f"{len(delete_ids)} feed record(s) deleted."
                        )
                        st.rerun()

            # 6. DOWNLOAD RECORDS
            download_csv(
                feed_data,
                "feed_management.csv",
                "Download Feed Records"
            )

# Health and vaccination
elif menu == "Health & Vaccination":
    st.header("💉 Animal Health & Vaccination")
    if not animal_ids:
        st.warning("Register animals first.")
    else:
        with st.form("health_add"):
            aid = st.selectbox("Animal",animal_ids)
            rdate = st.date_input("Record Date")
            rtype = st.selectbox("Record Type",["Vaccination","Medical Treatment","Check-up","Deworming","Other"])
            desc = st.text_area("Vaccine / medicine / health details")
            due = st.date_input("Next due date (select today if not applicable)")
            cost = st.number_input("Treatment cost (₹)",0.0,step=10.0)
            if st.form_submit_button("Save health record"):
                due_value = None if due == date.today() else due.isoformat()
                run("""INSERT INTO health(animal_id,record_date,record_type,description,next_due_date,cost)
                       VALUES(?,?,?,?,?,?)""",
                    (aid,rdate.isoformat(),rtype,desc,due_value,cost))
                st.success("Health record saved.")
    data = df("SELECT * FROM health ORDER BY record_date DESC,id DESC")
    st.dataframe(data,use_container_width=True)
    download_csv(data,"health_vaccination.csv","Download health records")

# Sales
elif menu == "Milk Sales":
    st.header("💰 Milk Sales")
    with st.form("sale_add"):
        sdate = st.date_input("Sale Date")
        customer = st.text_input("Customer Name")
        litres = st.number_input("Quantity sold (litres)",0.0,step=0.5)
        rate = st.number_input("Rate per litre (₹)",0.0,value=40.0,step=1.0)
        status = st.selectbox("Payment Status",["Paid","Pending","Partially Paid"])
        st.write(f"Total amount: ₹{litres*rate:,.2f}")
        if st.form_submit_button("Save sale"):
            if not customer.strip() or litres<=0 or rate<=0:
                st.error("Enter valid customer, quantity and rate.")
            else:
                run("""INSERT INTO sales(sale_date,customer,litres,rate,total,payment_status)
                       VALUES(?,?,?,?,?,?)""",
                    (sdate.isoformat(),customer.strip(),litres,rate,litres*rate,status))
                st.success("Sale saved.")
    data=df("SELECT * FROM sales ORDER BY sale_date DESC,id DESC")
    st.dataframe(data,use_container_width=True)
    download_csv(data,"sales.csv","Download sales")

# Expenses
elif menu == "Expense Management":
    st.header("📒 Other Farm Expenses")
    st.caption("Feed costs and health treatment costs are recorded in their own modules.")
    with st.form("expense_add"):
        edate=st.date_input("Expense Date")
        category=st.selectbox("Category",["Labour","Electricity","Transport","Equipment","Water","Maintenance","Other"])
        desc=st.text_input("Description")
        amount=st.number_input("Amount (₹)",0.0,step=50.0)
        if st.form_submit_button("Save expense"):
            if amount<=0: st.error("Amount must be greater than zero.")
            else:
                run("INSERT INTO expenses(expense_date,category,description,amount) VALUES(?,?,?,?)",
                    (edate.isoformat(),category,desc,amount))
                st.success("Expense saved.")
    data=df("SELECT * FROM expenses ORDER BY expense_date DESC,id DESC")
    st.dataframe(data,use_container_width=True)
    download_csv(data,"expenses.csv","Download expenses")

# Income and profit
elif menu == "Income & Profit":
    st.header("📈 Income & Profit Analysis")
    start=st.date_input("From",date.today().replace(day=1),key="profit_start")
    end=st.date_input("To",date.today(),key="profit_end")
    if start>end:
        st.error("Start date must not be after end date.")
    else:
        s,e=start.isoformat(),end.isoformat()
        revenue=float(df("SELECT COALESCE(SUM(total),0) v FROM sales WHERE sale_date BETWEEN ? AND ?",(s,e)).iloc[0]["v"])
        feed_cost=float(df("SELECT COALESCE(SUM(cost),0) v FROM feed WHERE record_date BETWEEN ? AND ?",(s,e)).iloc[0]["v"])
        health_cost=float(df("SELECT COALESCE(SUM(cost),0) v FROM health WHERE record_date BETWEEN ? AND ?",(s,e)).iloc[0]["v"])
        other_cost=float(df("SELECT COALESCE(SUM(amount),0) v FROM expenses WHERE expense_date BETWEEN ? AND ?",(s,e)).iloc[0]["v"])
        total_cost=feed_cost+health_cost+other_cost
        profit=revenue-total_cost
        a,b,c,d=st.columns(4)
        a.metric("Recorded Sales",f"₹{revenue:,.2f}")
        b.metric("Total Costs",f"₹{total_cost:,.2f}")
        c.metric("Estimated Profit / Loss",f"₹{profit:,.2f}")
        d.metric("Pending Sales",f"₹{float(df('SELECT COALESCE(SUM(total),0) v FROM sales WHERE sale_date BETWEEN ? AND ? AND payment_status != ?',(s,e,'Paid')).iloc[0]['v']):,.2f}")
        st.write("Cost breakdown")
        st.dataframe(pd.DataFrame({"Cost Type":["Feed","Health","Other"],"Amount (₹)":[feed_cost,health_cost,other_cost]}),use_container_width=True)
        st.info("This is an estimate based on recorded sales and costs. It is not audited accounting profit; unpaid sales are included in recorded sales.")

# Reports
elif menu == "Reports":
    st.header("📊 Farm Reports")
    start=st.date_input("Report from",date.today().replace(day=1),key="rep_start")
    end=st.date_input("Report to",date.today(),key="rep_end")
    if start>end: st.error("Invalid date range.")
    else:
        s,e=start.isoformat(),end.isoformat()
        milk=df("""SELECT record_date Date,SUM(litres) Litres FROM milk
                   WHERE record_date BETWEEN ? AND ? GROUP BY record_date ORDER BY record_date""",(s,e))
        sales=df("""SELECT sale_date Date,SUM(total) Sales,SUM(litres) Litres_Sold FROM sales
                    WHERE sale_date BETWEEN ? AND ? GROUP BY sale_date ORDER BY sale_date""",(s,e))
        feed=df("""SELECT feed_type Feed,SUM(quantity) Quantity,unit Unit,SUM(cost) Cost
                   FROM feed WHERE record_date BETWEEN ? AND ? GROUP BY feed_type,unit""",(s,e))
        st.subheader("Daily Milk Production")
        if milk.empty: st.info("No milk data for this period.")
        else:
            st.line_chart(milk.set_index("Date")["Litres"])
            st.dataframe(milk,use_container_width=True)
        st.subheader("Sales Report"); st.dataframe(sales,use_container_width=True)
        st.subheader("Feed Usage Report"); st.dataframe(feed,use_container_width=True)
        download_csv(milk,"milk_report.csv","Download milk report")
        download_csv(sales,"sales_report.csv","Download sales report")
        download_csv(feed,"feed_report.csv","Download feed report")

# Backup
elif menu == "Database Backup":
    st.header("🗄️ Database Backup")
    if os.path.exists(DB):
        with open(DB,"rb") as f:
            st.download_button("Download complete database",f,"dairy_farm_backup.db","application/octet-stream")
    st.warning("Download backups regularly. Do not delete dairy_farm.db while the app is running.")

st.sidebar.divider()
st.sidebar.caption("Dairy Farm Management System | Python • Streamlit • Pandas • SQLite")