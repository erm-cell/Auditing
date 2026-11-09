
import streamlit as st
import pandas as pd

from datetime import date, datetime
from sqlalchemy import func

from database import (
    SessionLocal,
    MoneyRecord,
    Product,
    StockMovement,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Business Tracker",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

TODAY = date.today()


# =========================================================
# DARK THEME AND CSS
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #090D16;
        color: #F4F7FB;
    }

    [data-testid="stSidebar"] {
        background-color: #111A28;
        border-right: 1px solid #263449;
    }

    [data-testid="stHeader"] {
        background-color: #090D16;
    }

    h1, h2, h3, h4, p, label, span {
        color: #F4F7FB;
    }

    [data-testid="stMetric"] {
        background-color: #111A28;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 16px;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    [data-testid="stMetricLabel"] {
        color: #AAB8CA;
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        background-color: #111A28;
        color: #FFFFFF;
        border: 1px solid #34445C;
    }

    div[data-baseweb="select"] > div {
        background-color: #111A28;
        color: #FFFFFF;
        border-color: #34445C;
    }

    .stButton button,
    .stFormSubmitButton button {
        background-color: #3478F6;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    .stButton button:hover,
    .stFormSubmitButton button:hover {
        background-color: #2464D8;
        color: white;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #263449;
        border-radius: 10px;
    }

    hr {
        border-color: #263449;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(amount):
    """Format a number as Indonesian Rupiah."""
    try:
        amount = float(amount or 0)
    except (TypeError, ValueError):
        amount = 0

    return f"Rp {amount:,.0f}".replace(",", ".")


def show_error(message):
    st.error(message)


def get_records():
    db = SessionLocal()
    try:
        return (
            db.query(MoneyRecord)
            .order_by(
                MoneyRecord.record_date.desc(),
                MoneyRecord.id.desc(),
            )
            .all()
        )
    finally:
        db.close()


def get_products():
    db = SessionLocal()
    try:
        return (
            db.query(Product)
            .order_by(Product.name)
            .all()
        )
    finally:
        db.close()


def get_movements():
    db = SessionLocal()
    try:
        return (
            db.query(StockMovement)
            .order_by(
                StockMovement.id.desc()
            )
            .all()
        )
    finally:
        db.close()


def records_to_dataframe(records):
    rows = []

    for record in records:
        rows.append({
            "ID": record.id,
            "Type": record.record_type,
            "Amount": record.amount,
            "Category": record.category,
            "Date": record.record_date,
            "Description": record.description or "",
        })

    return pd.DataFrame(rows)


def products_to_dataframe(products, movements):
    rows = []

    for product in products:
        product_movements = [
            movement
            for movement in movements
            if movement.product_id == product.id
        ]

        sold_quantity = sum(
            movement.quantity
            for movement in product_movements
            if movement.kind == "Sale"
        )

        restocked_quantity = sum(
            movement.quantity
            for movement in product_movements
            if movement.kind == "Restock"
        )

        used_quantity = sum(
            movement.quantity
            for movement in product_movements
            if movement.kind in ["Used", "Damaged"]
        )

        opening_quantity = sum(
            movement.quantity
            for movement in product_movements
            if movement.kind == "Initial stock"
        )

        rows.append({
            "Product": product.name,
            "Cost per item": product.unit_cost,
            "Selling price": product.selling_price,
            "Starting stock": opening_quantity,
            "Restocked": restocked_quantity,
            "Sold": sold_quantity,
            "Used / Damaged": used_quantity,
            "Remaining stock": product.stock,
            "Sales value": sold_quantity * product.selling_price,
        })

    return pd.DataFrame(rows)


def movement_to_dataframe(movements, products):
    product_names = {
        product.id: product.name
        for product in products
    }

    rows = []

    for movement in movements:
        rows.append({
            "Product": product_names.get(
                movement.product_id,
                "Unknown product",
            ),
            "Movement": movement.kind,
            "Quantity": movement.quantity,
            "Cost per item": movement.unit_cost,
            "Date": movement.movement_date,
            "Notes": movement.notes or "",
        })

    return pd.DataFrame(rows)


# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

st.sidebar.title("Business Tracker")
st.sidebar.caption("Manage your business finances and stock.")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Products & stock",
        "Sales",
        "Income & expenses",
        "Download reports",
    ],
)

st.sidebar.divider()
st.sidebar.caption("Business management dashboard")


# =========================================================
# OVERVIEW
# =========================================================

if page == "Overview":

    st.title("Overview")
    st.caption("Your business performance at a glance.")

    records = get_records()
    products = get_products()
    movements = get_movements()

    current_month_records = [
        record
        for record in records
        if record.record_date.year == TODAY.year
        and record.record_date.month == TODAY.month
    ]

    total_income = sum(
        record.amount
        for record in current_month_records
        if record.record_type == "Income"
    )

    total_expenses = sum(
        record.amount
        for record in current_month_records
        if record.record_type == "Expense"
    )

    profit = total_income - total_expenses

    total_stock = sum(
        product.stock
        for product in products
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Monthly income",
        money(total_income),
    )

    col2.metric(
        "Monthly expenses",
        money(total_expenses),
    )

    col3.metric(
        "Monthly balance",
        money(profit),
    )

    col4.metric(
        "Items in stock",
        f"{total_stock:,}".replace(",", "."),
    )

    st.divider()

    st.subheader("Recent transactions")

    if records:
        recent = records[:10]

        recent_df = records_to_dataframe(recent)

        recent_df["Amount"] = recent_df["Amount"].apply(money)

        st.dataframe(
            recent_df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No income or expense records yet.")

    st.divider()

    st.subheader("Product stock")

    if products:
        inventory_df = products_to_dataframe(
            products,
            movements,
        )

        st.dataframe(
            inventory_df[
                [
                    "Product",
                    "Sold",
                    "Remaining stock",
                    "Sales value",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Add your first product to start tracking stock.")


# =========================================================
# PRODUCTS AND STOCK
# =========================================================

elif page == "Products & stock":

    st.title("Products & stock")
    st.caption("Manage your products, prices, and inventory.")

    products = get_products()
    movements = get_movements()

    tab1, tab2, tab3 = st.tabs([
        "Product list",
        "Add product",
        "Manage stock",
    ])

    # -----------------------------------------------------
    # PRODUCT LIST
    # -----------------------------------------------------

    with tab1:

        st.subheader("Your products")

        if products:
            inventory_df = products_to_dataframe(
                products,
                movements,
            )

            display_df = inventory_df.copy()

            display_df["Cost per item"] = (
                display_df["Cost per item"].apply(money)
            )

            display_df["Selling price"] = (
                display_df["Selling price"].apply(money)
            )

            display_df["Sales value"] = (
                display_df["Sales value"].apply(money)
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            st.subheader("Edit product details")

            product_map = {
                product.id: product
                for product in products
            }

            selected_id = st.selectbox(
                "Select a product",
                options=list(product_map.keys()),
                format_func=lambda product_id: (
                    product_map[product_id].name
                ),
            )

            selected_product = product_map[selected_id]

            with st.form("edit_product_form"):

                new_name = st.text_input(
                    "Product name",
                    value=selected_product.name,
                )

                new_cost = st.number_input(
                    "Cost per item (Rp)",
                    min_value=0.0,
                    value=float(selected_product.unit_cost),
                    step=1000.0,
                )

                new_price = st.number_input(
                    "Selling price per item (Rp)",
                    min_value=0.0,
                    value=float(selected_product.selling_price),
                    step=1000.0,
                )

                update_product = st.form_submit_button(
                    "Save product changes"
                )

                if update_product:

                    if not new_name.strip():
                        show_error("Product name cannot be empty.")

                    else:
                        db = SessionLocal()

                        try:
                            product = db.get(
                                Product,
                                selected_id,
                            )

                            product.name = new_name.strip()
                            product.unit_cost = new_cost
                            product.selling_price = new_price

                            db.commit()

                            st.success("Product updated successfully.")
                            st.rerun()

                        except Exception as error:
                            db.rollback()
                            show_error(str(error))

                        finally:
                            db.close()

        else:
            st.info("You have not added any products yet.")

    # -----------------------------------------------------
    # ADD PRODUCT
    # -----------------------------------------------------

    with tab2:

        st.subheader("Add a new product")

        with st.form("add_product_form"):

            product_name = st.text_input("Product name")

            unit_cost = st.number_input(
                "Cost per item (Rp)",
                min_value=0.0,
                value=0.0,
                step=1000.0,
            )

            selling_price = st.number_input(
                "Selling price per item (Rp)",
                min_value=0.0,
                value=0.0,
                step=1000.0,
            )

            starting_stock = st.number_input(
                "Starting stock",
                min_value=0,
                value=0,
                step=1,
            )

            add_product_button = st.form_submit_button(
                "Add product"
            )

            if add_product_button:

                if not product_name.strip():
                    show_error("Please enter a product name.")

                else:
                    db = SessionLocal()

                    try:
                        existing = (
                            db.query(Product)
                            .filter(
                                func.lower(Product.name)
                                == product_name.strip().lower()
                            )
                            .first()
                        )

                        if existing:
                            show_error(
                                "A product with this name already exists."
                            )

                        else:
                            product = Product(
                                name=product_name.strip(),
                                unit_cost=unit_cost,
                                selling_price=selling_price,
                                stock=starting_stock,
                            )

                            db.add(product)
                            db.flush()

                            if starting_stock > 0:
                                movement = StockMovement(
                                    product_id=product.id,
                                    kind="Initial stock",
                                    quantity=starting_stock,
                                    unit_cost=unit_cost,
                                    movement_date=TODAY,
                                    notes="Starting stock",
                                )

                                db.add(movement)

                            db.commit()

                            st.success("Product added successfully.")
                            st.rerun()

                    except Exception as error:
                        db.rollback()
                        show_error(str(error))

                    finally:
                        db.close()

    # -----------------------------------------------------
    # MANAGE STOCK
    # -----------------------------------------------------

    with tab3:

        st.subheader("Update stock")

        if not products:
            st.info("Add a product before managing stock.")

        else:

            product_map = {
                product.id: product
                for product in products
            }

            selected_id = st.selectbox(
                "Choose product",
                options=list(product_map.keys()),
                format_func=lambda product_id: (
                    product_map[product_id].name
                ),
                key="stock_product",
            )

            selected_product = product_map[selected_id]

            st.metric(
                "Current stock",
                selected_product.stock,
            )

            stock_action = st.radio(
                "Stock action",
                [
                    "Restock",
                    "Used",
                    "Damaged",
                ],
                horizontal=True,
            )

            with st.form("stock_update_form"):

                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=1,
                    step=1,
                )

                if stock_action == "Restock":

                    restock_cost = st.number_input(
                        "Cost per item (Rp)",
                        min_value=0.0,
                        value=float(selected_product.unit_cost),
                        step=1000.0,
                    )

                else:
                    restock_cost = float(
                        selected_product.unit_cost
                    )

                stock_notes = st.text_input(
                    "Notes (optional)"
                )

                update_stock_button = st.form_submit_button(
                    "Update stock"
                )

                if update_stock_button:

                    db = SessionLocal()

                    try:
                        product = db.get(
                            Product,
                            selected_id,
                        )

                        if (
                            stock_action != "Restock"
                            and quantity > product.stock
                        ):
                            show_error(
                                "Quantity cannot be greater than current stock."
                            )

                        else:

                            if stock_action == "Restock":

                                old_stock = product.stock
                                new_stock = old_stock + quantity

                                if new_stock > 0:
                                    product.unit_cost = (
                                        (
                                            old_stock * product.unit_cost
                                            + quantity * restock_cost
                                        )
                                        / new_stock
                                    )

                                product.stock = new_stock

                            else:
                                product.stock -= quantity

                            movement = StockMovement(
                                product_id=selected_id,
                                kind=stock_action,
                                quantity=quantity,
                                unit_cost=restock_cost,
                                movement_date=TODAY,
                                notes=stock_notes,
                            )

                            db.add(movement)

                            # A restock is recorded as a cash expense.
                            # Used and damaged stock are tracked as
                            # inventory movements, not additional expenses.

                            if stock_action == "Restock":
                                expense = MoneyRecord(
                                    record_type="Expense",
                                    amount=quantity * restock_cost,
                                    category="Stock purchase",
                                    record_date=TODAY,
                                    description=(
                                        f"Restocked {quantity} "
                                        f"x {product.name}"
                                    ),
                                )

                                db.add(expense)

                            db.commit()

                            st.success(
                                f"{stock_action} stock updated successfully."
                            )

                            st.rerun()

                    except Exception as error:
                        db.rollback()
                        show_error(str(error))

                    finally:
                        db.close()

        st.divider()

        st.subheader("Stock movement history")

        if movements:

            movement_df = movement_to_dataframe(
                movements,
                products,
            )

            movement_df["Cost per item"] = (
                movement_df["Cost per item"].apply(money)
            )

            st.dataframe(
                movement_df,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("No stock movements recorded yet.")


# =========================================================
# SALES
# =========================================================

elif page == "Sales":

    st.title("Sales")
    st.caption("Record sales and track the value of your products sold.")

    products = get_products()
    movements = get_movements()

    if not products:
        st.info("Add a product before recording a sale.")

    else:

        product_map = {
            product.id: product
            for product in products
        }

        st.subheader("Record a sale")

        selected_id = st.selectbox(
            "Select product",
            options=list(product_map.keys()),
            format_func=lambda product_id: (
                f"{product_map[product_id].name} "
                f"— Stock: {product_map[product_id].stock}"
            ),
        )

        selected_product = product_map[selected_id]

        st.write(
            f"**Selling price:** {money(selected_product.selling_price)}"
        )

        st.write(
            f"**Available stock:** {selected_product.stock}"
        )

        with st.form("record_sale_form"):

            sale_quantity = st.number_input(
                "Quantity sold",
                min_value=1,
                value=1,
                step=1,
            )

            sale_date = st.date_input(
                "Sale date",
                value=TODAY,
            )

            sale_description = st.text_input(
                "Notes (optional)"
            )

            sale_button = st.form_submit_button(
                "Record sale"
            )

            if sale_button:

                db = SessionLocal()

                try:
                    product = db.get(
                        Product,
                        selected_id,
                    )

                    if sale_quantity > product.stock:
                        show_error(
                            "Not enough stock available."
                        )

                    else:

                        sale_value = (
                            sale_quantity
                            * product.selling_price
                        )

                        product.stock -= sale_quantity

                        movement = StockMovement(
                            product_id=selected_id,
                            kind="Sale",
                            quantity=sale_quantity,
                            unit_cost=product.unit_cost,
                            movement_date=sale_date,
                            notes=sale_description,
                        )

                        income = MoneyRecord(
                            record_type="Income",
                            amount=sale_value,
                            category="Sales",
                            record_date=sale_date,
                            description=(
                                f"{sale_quantity} x {product.name}"
                                + (
                                    f" - {sale_description}"
                                    if sale_description.strip()
                                    else ""
                                )
                            ),
                        )

                        db.add(movement)
                        db.add(income)

                        db.commit()

                        st.success(
                            f"Sale recorded. Total: {money(sale_value)}"
                        )

                        st.rerun()

                except Exception as error:
                    db.rollback()
                    show_error(str(error))

                finally:
                    db.close()

    st.divider()

    st.subheader("Sales history")

    sales_movements = [
        movement
        for movement in movements
        if movement.kind == "Sale"
    ]

    if sales_movements:

        product_names = {
            product.id: product.name
            for product in products
        }

        sales_rows = []

        for movement in sales_movements:

            product = next(
                (
                    item
                    for item in products
                    if item.id == movement.product_id
                ),
                None,
            )

            if product is None:
                continue

            sales_rows.append({
                "Product": product_names.get(
                    movement.product_id,
                    "Unknown product",
                ),
                "Quantity sold": movement.quantity,
                "Date": movement.movement_date,
                "Cost used": money(
                    movement.quantity * movement.unit_cost
                ),
                "Notes": movement.notes or "",
            })

        sales_df = pd.DataFrame(sales_rows)

        st.dataframe(
            sales_df,
            use_container_width=True,
            hide_index=True,
        )

        total_sold = sum(
            movement.quantity
            for movement in sales_movements
        )

        total_cost = sum(
            movement.quantity * movement.unit_cost
            for movement in sales_movements
        )

        col1, col2 = st.columns(2)

        col1.metric(
            "Total items sold",
            total_sold,
        )

        col2.metric(
            "Recorded cost of sold stock",
            money(total_cost),
        )

    else:
        st.info("No sales recorded yet.")


# =========================================================
# INCOME AND EXPENSES
# =========================================================

elif page == "Income & expenses":

    st.title("Income & expenses")
    st.caption("Track your business money and correct existing entries.")

    records = get_records()

    # -----------------------------------------------------
    # ADD NEW RECORD
    # -----------------------------------------------------

    st.subheader("Add a transaction")

    with st.form("add_money_record_form"):

        record_type = st.selectbox(
            "Transaction type",
            [
                "Income",
                "Expense",
            ],
        )

        amount = st.number_input(
            "Amount (Rp)",
            min_value=0.0,
            value=0.0,
            step=1000.0,
        )

        category = st.text_input(
            "Category",
            placeholder="Example: Sales, Rent, Supplies",
        )

        record_date = st.date_input(
            "Date",
            value=TODAY,
        )

        description = st.text_input(
            "Description (optional)",
        )

        add_record_button = st.form_submit_button(
            "Add transaction"
        )

        if add_record_button:

            if amount <= 0:
                show_error("Amount must be greater than zero.")

            elif not category.strip():
                show_error("Please enter a category.")

            else:
                db = SessionLocal()

                try:
                    new_record = MoneyRecord(
                        record_type=record_type,
                        amount=amount,
                        category=category.strip(),
                        record_date=record_date,
                        description=description.strip(),
                    )

                    db.add(new_record)
                    db.commit()

                    st.success("Transaction added successfully.")
                    st.rerun()

                except Exception as error:
                    db.rollback()
                    show_error(str(error))

                finally:
                    db.close()

    st.divider()

    # -----------------------------------------------------
    # FILTER RECORDS
    # -----------------------------------------------------

    st.subheader("Transaction history")

    records = get_records()

    if records:

        col1, col2 = st.columns(2)

        with col1:
            filter_type = st.selectbox(
                "Filter by type",
                [
                    "All",
                    "Income",
                    "Expense",
                ],
            )

        with col2:
            filter_month = st.selectbox(
                "Filter by month",
                ["All"] + [
                    f"{year}-{month:02d}"
                    for year, month in sorted(
                        {
                            (
                                record.record_date.year,
                                record.record_date.month,
                            )
                            for record in records
                        },
                        reverse=True,
                    )
                ],
            )

        filtered = records

        if filter_type != "All":
            filtered = [
                record
                for record in filtered
                if record.record_type == filter_type
            ]

        if filter_month != "All":
            year, month = map(
                int,
                filter_month.split("-"),
            )

            filtered = [
                record
                for record in filtered
                if (
                    record.record_date.year == year
                    and record.record_date.month == month
                )
            ]

        if filtered:

            table_df = records_to_dataframe(filtered)

            table_df["Amount"] = (
                table_df["Amount"].apply(money)
            )

            st.dataframe(
                table_df.drop(columns=["ID"]),
                use_container_width=True,
                hide_index=True,
            )

            income_total = sum(
                record.amount
                for record in filtered
                if record.record_type == "Income"
            )

            expense_total = sum(
                record.amount
                for record in filtered
                if record.record_type == "Expense"
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Income",
                money(income_total),
            )

            col2.metric(
                "Expenses",
                money(expense_total),
            )

            col3.metric(
                "Balance",
                money(income_total - expense_total),
            )

            st.divider()

            # -------------------------------------------------
            # EDIT EXISTING RECORD
            # -------------------------------------------------

            st.subheader("Edit an existing transaction")

            st.caption(
                "Choose a transaction to correct it. "
                "Saving changes updates the original record "
                "instead of creating another one."
            )

            record_map = {
                record.id: record
                for record in filtered
            }

            selected_record_id = st.selectbox(
                "Choose transaction",
                options=list(record_map.keys()),
                format_func=lambda record_id: (
                    f"#{record_id} | "
                    f"{record_map[record_id].record_type} | "
                    f"{money(record_map[record_id].amount)} | "
                    f"{record_map[record_id].category} | "
                    f"{record_map[record_id].record_date}"
                ),
            )

            selected_record = record_map[
                selected_record_id
            ]

            with st.form("edit_money_record_form"):

                edited_type = st.selectbox(
                    "Transaction type",
                    [
                        "Income",
                        "Expense",
                    ],
                    index=(
                        0
                        if selected_record.record_type == "Income"
                        else 1
                    ),
                )

                edited_amount = st.number_input(
                    "Amount (Rp)",
                    min_value=0.0,
                    value=float(selected_record.amount),
                    step=1000.0,
                )

                edited_category = st.text_input(
                    "Category",
                    value=selected_record.category or "",
                )

                edited_date = st.date_input(
                    "Date",
                    value=selected_record.record_date,
                )

                edited_description = st.text_input(
                    "Description",
                    value=selected_record.description or "",
                )

                save_changes = st.form_submit_button(
                    "Save changes"
                )

                if save_changes:

                    if edited_amount <= 0:
                        show_error(
                            "Amount must be greater than zero."
                        )

                    elif not edited_category.strip():
                        show_error(
                            "Please enter a category."
                        )

                    else:
                        db = SessionLocal()

                        try:
                            existing_record = db.get(
                                MoneyRecord,
                                selected_record_id,
                            )

                            if existing_record is None:
                                show_error(
                                    "This transaction could not be found."
                                )

                            else:
                                existing_record.record_type = (
                                    edited_type
                                )

                                existing_record.amount = (
                                    edited_amount
                                )

                                existing_record.category = (
                                    edited_category.strip()
                                )

                                existing_record.record_date = (
                                    edited_date
                                )

                                existing_record.description = (
                                    edited_description.strip()
                                )

                                db.commit()

                                st.success(
                                    "Transaction updated successfully. "
                                    "No duplicate was created."
                                )

                                st.rerun()

                        except Exception as error:
                            db.rollback()
                            show_error(str(error))

                        finally:
                            db.close()

        else:
            st.info("No transactions match your filters.")

    else:
        st.info("No transactions recorded yet.")


# =========================================================
# DOWNLOAD REPORTS
# =========================================================

elif page == "Download reports":

    st.title("Download reports")
    st.caption("Export your business records as CSV files.")

    records = get_records()
    products = get_products()
    movements = get_movements()

    st.subheader("Income and expenses")

    if records:

        money_df = records_to_dataframe(records)

        csv_money = money_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="Download income and expenses",
            data=csv_money,
            file_name="income_expenses.csv",
            mime="text/csv",
        )

    else:
        st.info("No financial records to export.")

    st.divider()

    st.subheader("Product inventory")

    if products:

        inventory_df = products_to_dataframe(
            products,
            movements,
        )

        csv_inventory = inventory_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="Download product inventory",
            data=csv_inventory,
            file_name="product_inventory.csv",
            mime="text/csv",
        )

    else:
        st.info("No products to export.")

    st.divider()

    st.subheader("Stock movement history")

    if movements:

        movement_df = movement_to_dataframe(
            movements,
            products,
        )

        csv_movements = movement_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="Download stock movements",
            data=csv_movements,
            file_name="stock_movements.csv",
            mime="text/csv",
        )

    else:
        st.info("No stock movements to export.")

