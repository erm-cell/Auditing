
from __future__ import annotations

import hmac
import os
from datetime import date, datetime
from io import BytesIO

import pandas as pd
import streamlit as st

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from database import (
    Product,
    MoneyRecord,
    StockMovement,
    SeedMarker,
    get_database_url,
    create_session_factory,
    app_today,
)


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Business Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Business Tracker"

SEED_KEY = "initial_income_2026_v1"

# ============================================================
# DATABASE CONNECTION
# ============================================================

@st.cache_resource
def get_session_factory_cached():
    return create_session_factory(get_database_url())


SessionFactory = get_session_factory_cached()


def get_session():
    return SessionFactory()


# ============================================================
# ACCESS CODE
# ============================================================

def get_access_code():
    try:
        return str(st.secrets.get("APP_ACCESS_CODE", "")).strip()
    except Exception:
        return os.getenv("APP_ACCESS_CODE", "").strip()


ACCESS_CODE = get_access_code()

if not ACCESS_CODE:
    st.error(
        "Access code is not configured. "
        "Add APP_ACCESS_CODE to Streamlit Secrets."
    )
    st.stop()


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


if not st.session_state.authenticated:

    st.title(APP_NAME)
    st.write("Enter your access code to continue.")

    with st.form("login_form"):

        entered_code = st.text_input(
            "Access code",
            type="password",
        )

        login = st.form_submit_button(
            "Continue",
            use_container_width=True,
        )

        if login:

            if hmac.compare_digest(
                entered_code.encode("utf-8"),
                ACCESS_CODE.encode("utf-8"),
            ):
                st.session_state.authenticated = True
                st.rerun()

            else:
                st.error("Incorrect access code.")

    st.stop()


# ============================================================
# GENERAL HELPERS
# ============================================================

def money(value):
    return "Rp" + f"{round(float(value or 0)):,.0f}".replace(",", ".")


def format_date(value):
    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")

    return str(value)


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    return datetime.strptime(str(value), "%Y-%m-%d").date()


def safe_float(value):
    return float(value or 0)


def get_all_transactions(session):
    return (
        session.query(MoneyRecord)
        .order_by(
            MoneyRecord.record_date.desc(),
            MoneyRecord.id.desc(),
        )
        .all()
    )


def get_all_products(session):
    return (
        session.query(Product)
        .order_by(Product.name.asc())
        .all()
    )


def get_all_movements(session):
    return (
        session.query(StockMovement)
        .order_by(
            StockMovement.movement_date.desc(),
            StockMovement.id.desc(),
        )
        .all()
    )


# ============================================================
# INITIAL INCOME
# ============================================================

STARTING_INCOME = [
    ("08/11/2026", 28000),
    ("01/11/2026", 8000),
    ("01/11/2026", 8000),
    ("01/11/2026", 38000),
    ("01/11/2026", 5000),
    ("01/11/2026", 16000),
    ("01/11/2026", 7000),
    ("01/11/2026", 12000),
    ("01/11/2026", 16000),
    ("01/11/2026", 8000),
    ("01/11/2026", 8000),
    ("01/11/2026", 16000),
    ("01/11/2026", 10000),
    ("01/11/2026", 40000),
    ("26/10/2026", 15000),
    ("26/10/2026", 15000),
    ("26/10/2026", 16000),
    ("24/10/2026", 8000),
    ("24/10/2026", 14000),
    ("21/10/2026", 17000),
    ("20/10/2026", 18000),
    ("20/10/2026", 10000),
    ("18/10/2026", 38000),
    ("18/10/2026", 6000),
    ("16/10/2026", 38000),
    ("14/10/2026", 38000),
    ("13/10/2026", 16000),
    ("12/10/2026", 24000),
    ("12/10/2026", 24000),
    ("09/10/2026", 214000),
    ("09/10/2026", 24000),
    ("09/10/2026", 8000),
    ("09/10/2026", 8000),
    ("08/10/2026", 18000),
    ("08/10/2026", 46000),
    ("08/10/2026", 38000),
    ("08/10/2026", 42000),
]


def seed_initial_income():

    session = get_session()

    try:

        marker = session.get(SeedMarker, SEED_KEY)

        if marker:
            return

        # Never insert the supplied starting records into
        # a database that already contains money records.
        existing_count = (
            session.query(func.count(MoneyRecord.id)).scalar() or 0
        )

        if existing_count == 0:

            # The Rp238,000 is recorded as cash income,
            # as requested.
            session.add(
                MoneyRecord(
                    record_date=date(2026, 11, 8),
                    record_type="Income",
                    category="Cash",
                    description="Starting cash",
                    amount=238000,
                )
            )

            for date_text, amount in STARTING_INCOME:

                transaction_date = datetime.strptime(
                    date_text,
                    "%d/%m/%Y",
                ).date()

                session.add(
                    MoneyRecord(
                        record_date=transaction_date,
                        record_type="Income",
                        category="Cash",
                        description="Existing income",
                        amount=amount,
                    )
                )

        session.add(
            SeedMarker(key=SEED_KEY)
        )

        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


# ============================================================
# STOCK MOVEMENT TYPES
# ============================================================

def movement_group(kind):

    normalized = str(kind).strip().lower()

    purchase_names = {
        "purchase",
        "stock added",
        "stock in",
        "add stock",
        "addition",
        "restock",
    }

    sale_names = {
        "sale",
        "sold",
        "stock sold",
    }

    usage_names = {
        "use",
        "used",
        "used / damaged",
        "damaged",
        "damage",
        "stock used",
        "stock out",
    }

    if normalized in purchase_names:
        return "purchase"

    if normalized in sale_names:
        return "sale"

    if normalized in usage_names:
        return "usage"

    raise ValueError(
        f"Unknown stock movement type: {kind}"
    )


# ============================================================
# STOCK CALCULATIONS
# ============================================================

def get_opening_unit_cost(session, product):

    """
    Reconstruct the opening stock value from the saved
    current balance and the recorded stock movements.

    This allows previous movements to be edited or deleted
    without simply subtracting their quantities from today.
    """

    current_value = (
        safe_float(product.current_stock)
        * safe_float(product.unit_cost)
    )

    purchase_cost = 0
    outgoing_cost = 0

    movements = (
        session.query(StockMovement)
        .filter(
            StockMovement.product_id == product.id
        )
        .all()
    )

    for movement in movements:

        group = movement_group(movement.kind)

        if group == "purchase":
            purchase_cost += safe_float(movement.total_cost)

        else:
            outgoing_cost += safe_float(movement.total_cost)

    opening_value = (
        current_value
        - purchase_cost
        + outgoing_cost
    )

    opening_value = max(0, opening_value)

    if product.opening_stock <= 0:
        return 0

    return opening_value / product.opening_stock


def recalculate_product(
    session,
    product,
    opening_unit_cost,
):

    """
    Recalculate all movements in date order.

    Purchase:
        Adds stock and updates weighted average cost.

    Sale:
        Removes stock, records cost used and sales revenue.

    Usage:
        Removes stock and records the cost of the stock used.
    """

    quantity = int(product.opening_stock)

    total_stock_value = (
        quantity * float(opening_unit_cost)
    )

    movements = (
        session.query(StockMovement)
        .filter(
            StockMovement.product_id == product.id
        )
        .order_by(
            StockMovement.movement_date.asc(),
            StockMovement.id.asc(),
        )
        .all()
    )

    last_average_cost = float(opening_unit_cost)

    for movement in movements:

        group = movement_group(movement.kind)
        qty = int(movement.quantity)

        if qty <= 0:
            raise ValueError(
                "Stock quantity must be greater than zero."
            )

        average_cost = (
            total_stock_value / quantity
            if quantity > 0
            else last_average_cost
        )

        if group == "purchase":

            incoming_cost = safe_float(movement.unit_cost)

            quantity += qty

            total_stock_value += (
                qty * incoming_cost
            )

            movement.total_cost = qty * incoming_cost
            movement.total_revenue = 0

            last_average_cost = (
                total_stock_value / quantity
                if quantity > 0
                else incoming_cost
            )

        elif group in ("sale", "usage"):

            if qty > quantity:

                raise ValueError(
                    f"Not enough stock for {product.name}. "
                    f"Available: {quantity}. "
                    f"Required: {qty}."
                )

            cost_used = qty * average_cost

            quantity -= qty
            total_stock_value -= cost_used

            if quantity == 0:
                total_stock_value = 0

            movement.total_cost = cost_used

            if group == "sale":

                movement.total_revenue = (
                    qty * safe_float(movement.unit_price)
                )

            else:
                movement.total_revenue = 0

            last_average_cost = average_cost

    product.current_stock = quantity

    product.unit_cost = last_average_cost

    session.flush()


def save_stock_movement(
    session,
    product,
    movement_date,
    kind,
    quantity,
    unit_cost=0,
    unit_price=0,
    note="",
    movement=None,
):

    """
    Add or edit a movement safely.

    The previous opening cost is calculated before changing
    the movement, then the entire stock history is replayed.
    """

    opening_cost = get_opening_unit_cost(
        session,
        product,
    )

    if movement is None:

        movement = StockMovement(
            product_id=product.id,
            movement_date=movement_date,
            kind=kind,
            quantity=quantity,
            unit_cost=unit_cost,
            unit_price=unit_price,
            total_cost=0,
            total_revenue=0,
            note=note,
        )

        session.add(movement)

    else:

        movement.movement_date = movement_date
        movement.kind = kind
        movement.quantity = quantity
        movement.unit_cost = unit_cost
        movement.unit_price = unit_price
        movement.note = note

    session.flush()

    recalculate_product(
        session,
        product,
        opening_cost,
    )

    return movement


# ============================================================
# STARTUP
# ============================================================

try:
    seed_initial_income()

except SQLAlchemyError as error:
    st.error(
        "The database could not be initialized. "
        "Check your database connection and settings."
    )
    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(APP_NAME)

page = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "Income & Expenses",
        "Products & Stock",
        "Stock History",
        "Data Backup",
    ],
)

st.sidebar.divider()

if st.sidebar.button(
    "Log out",
    use_container_width=True,
):
    st.session_state.authenticated = False
    st.rerun()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title("Dashboard")

    session = get_session()

    try:

        records = get_all_transactions(session)
        products = get_all_products(session)
        movements = get_all_movements(session)

        income = sum(
            safe_float(r.amount)
            for r in records
            if r.record_type.lower() == "income"
        )

        expenses = sum(
            safe_float(r.amount)
            for r in records
            if r.record_type.lower() == "expense"
        )

        cash_balance = income - expenses

        remaining_stock_value = sum(
            safe_float(p.current_stock)
            * safe_float(p.unit_cost)
            for p in products
        )

        total_stock_used_cost = sum(
            safe_float(m.total_cost)
            for m in movements
            if movement_group(m.kind) in ("sale", "usage")
        )

        total_sales = sum(
            safe_float(m.total_revenue)
            for m in movements
            if movement_group(m.kind) == "sale"
        )

        total_cost_of_sold_stock = sum(
            safe_float(m.total_cost)
            for m in movements
            if movement_group(m.kind) == "sale"
        )

        gross_profit = (
            total_sales - total_cost_of_sold_stock
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Income",
            money(income),
        )

        col2.metric(
            "Total Expenses",
            money(expenses),
        )

        col3.metric(
            "Cash Balance",
            money(cash_balance),
        )

        col4, col5, col6 = st.columns(3)

        col4.metric(
            "Remaining Stock Value",
            money(remaining_stock_value),
        )

        col5.metric(
            "Stock Cost Used",
            money(total_stock_used_cost),
        )

        col6.metric(
            "Recorded Sales Value",
            money(total_sales),
        )

        st.divider()

        st.subheader("Sales Summary")

        st.metric(
            "Gross Profit from Recorded Stock Sales",
            money(gross_profit),
        )

        st.caption(
            "Gross profit is sales value minus the cost of stock sold. "
            "It does not include other business expenses."
        )

        st.divider()

        st.subheader("Recent Transactions")

        if records:

            recent = []

            for record in records[:10]:

                recent.append({
                    "Date": format_date(record.record_date),
                    "Type": record.record_type,
                    "Description": record.description,
                    "Category": record.category,
                    "Amount": money(record.amount),
                })

            st.dataframe(
                pd.DataFrame(recent),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info("No transactions recorded.")

    finally:
        session.close()


# ============================================================
# INCOME AND EXPENSES
# ============================================================

elif page == "Income & Expenses":

    st.title("Income & Expenses")

    tab1, tab2, tab3 = st.tabs([
        "Add Transaction",
        "Edit Transaction",
        "Transaction List",
    ])

    # --------------------------------------------------------
    # ADD TRANSACTION
    # --------------------------------------------------------

    with tab1:

        with st.form("add_money_form"):

            record_type = st.selectbox(
                "Type",
                ["Income", "Expense"],
            )

            description = st.text_input(
                "Description",
            )

            amount = st.number_input(
                "Amount (Rp)",
                min_value=1,
                step=1000,
            )

            record_date = st.date_input(
                "Date",
                value=app_today(),
                format="DD/MM/YYYY",
            )

            category = st.selectbox(
                "Payment method / Category",
                [
                    "Cash",
                    "Bank transfer",
                    "E-wallet",
                    "Other",
                ],
            )

            submitted = st.form_submit_button(
                "Save Transaction",
                use_container_width=True,
            )

            if submitted:

                if not description.strip():
                    st.error("Please enter a description.")

                else:

                    session = get_session()

                    try:

                        session.add(
                            MoneyRecord(
                                record_date=record_date,
                                record_type=record_type,
                                category=category,
                                description=description.strip(),
                                amount=float(amount),
                            )
                        )

                        session.commit()

                        st.success("Transaction saved.")
                        st.rerun()

                    except Exception as error:

                        session.rollback()
                        st.error(f"Could not save transaction: {error}")

                    finally:
                        session.close()

    # --------------------------------------------------------
    # EDIT TRANSACTION
    # --------------------------------------------------------

    with tab2:

        session = get_session()

        try:

            records = get_all_transactions(session)

            if not records:

                st.info("No transactions available.")

            else:

                options = {
                    (
                        f"#{r.id} | "
                        f"{format_date(r.record_date)} | "
                        f"{r.record_type} | "
                        f"{r.description} | "
                        f"{money(r.amount)}"
                    ): r.id
                    for r in records
                }

                selected_label = st.selectbox(
                    "Choose a transaction to edit",
                    list(options.keys()),
                )

                selected_id = options[selected_label]
                selected = session.get(MoneyRecord, selected_id)

                with st.form("edit_money_form"):

                    new_type = st.selectbox(
                        "Type",
                        ["Income", "Expense"],
                        index=(
                            0 if selected.record_type.lower() == "income"
                            else 1
                        ),
                    )

                    new_description = st.text_input(
                        "Description",
                        value=selected.description,
                    )

                    new_amount = st.number_input(
                        "Amount (Rp)",
                        min_value=1,
                        value=max(1, int(round(selected.amount))),
                        step=1000,
                    )

                    new_date = st.date_input(
                        "Date",
                        value=selected.record_date,
                        format="DD/MM/YYYY",
                    )

                    category_options = [
                        "Cash",
                        "Bank transfer",
                        "E-wallet",
                        "Other",
                    ]

                    old_category = (
                        selected.category
                        if selected.category in category_options
                        else "Other"
                    )

                    new_category = st.selectbox(
                        "Payment method / Category",
                        category_options,
                        index=category_options.index(old_category),
                    )

                    save_edit = st.form_submit_button(
                        "Save Changes",
                        use_container_width=True,
                    )

                    if save_edit:

                        if not new_description.strip():

                            st.error("Please enter a description.")

                        else:

                            selected.record_type = new_type
                            selected.description = new_description.strip()
                            selected.amount = float(new_amount)
                            selected.record_date = new_date
                            selected.category = new_category

                            session.commit()

                            st.success(
                                "Transaction updated. "
                                "It was not duplicated."
                            )

                            st.rerun()

                st.divider()

                st.subheader("Delete Transaction")

                confirm_delete = st.checkbox(
                    "I want to permanently delete this transaction.",
                    key=f"delete_money_{selected_id}",
                )

                if st.button(
                    "Delete Transaction",
                    disabled=not confirm_delete,
                ):

                    session.delete(selected)
                    session.commit()

                    st.success("Transaction deleted.")
                    st.rerun()

        except Exception as error:

            session.rollback()
            st.error(f"Could not load transaction: {error}")

        finally:
            session.close()

    # --------------------------------------------------------
    # TRANSACTION LIST
    # --------------------------------------------------------

    with tab3:

        session = get_session()

        try:

            records = get_all_transactions(session)

            if records:

                data = []

                for record in records:

                    data.append({
                        "ID": record.id,
                        "Date": format_date(record.record_date),
                        "Type": record.record_type,
                        "Description": record.description,
                        "Category": record.category,
                        "Amount": money(record.amount),
                    })

                st.dataframe(
                    pd.DataFrame(data),
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info("No transactions recorded.")

        finally:
            session.close()


# ============================================================
# PRODUCTS AND STOCK
# ============================================================

elif page == "Products & Stock":

    st.title("Products & Stock")

    tab1, tab2, tab3 = st.tabs([
        "Stock Overview",
        "Add Product",
        "Update Stock",
    ])

    # --------------------------------------------------------
    # STOCK OVERVIEW
    # --------------------------------------------------------

    with tab1:

        session = get_session()

        try:

            products = get_all_products(session)

            if not products:

                st.info("No products have been added.")

            else:

                rows = []

                for product in products:

                    movements = (
                        session.query(StockMovement)
                        .filter(
                            StockMovement.product_id == product.id
                        )
                        .all()
                    )

                    sold_quantity = sum(
                        m.quantity
                        for m in movements
                        if movement_group(m.kind) == "sale"
                    )

                    used_quantity = sum(
                        m.quantity
                        for m in movements
                        if movement_group(m.kind) == "usage"
                    )

                    stock_value = (
                        product.current_stock * product.unit_cost
                    )

                    rows.append({

                        "Product": product.name,

                        "Category": product.category,

                        "Original Stock": product.opening_stock,

                        "Sold": sold_quantity,

                        "Used / Damaged": used_quantity,

                        "Remaining Stock": product.current_stock,

                        "Cost per Unit": money(product.unit_cost),

                        "Selling Price": money(product.selling_price),

                        "Remaining Stock Value": money(stock_value),

                    })

                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )

                st.divider()

                st.subheader("Edit Product Details")

                product_options = {
                    f"{p.name} (ID {p.id})": p.id
                    for p in products
                }

                selected_label = st.selectbox(
                    "Choose a product",
                    list(product_options.keys()),
                )

                product_id = product_options[selected_label]

                product = session.get(Product, product_id)

                with st.form("edit_product_form"):

                    new_name = st.text_input(
                        "Product name",
                        value=product.name,
                    )

                    new_category = st.text_input(
                        "Category",
                        value=product.category,
                    )

                    new_selling_price = st.number_input(
                        "Selling price per unit (Rp)",
                        min_value=0.0,
                        value=float(product.selling_price),
                        step=1000.0,
                    )

                    save_product = st.form_submit_button(
                        "Save Product Details",
                        use_container_width=True,
                    )

                    if save_product:

                        if not new_name.strip():

                            st.error("Please enter a product name.")

                        else:

                            duplicate = (
                                session.query(Product)
                                .filter(
                                    func.lower(Product.name)
                                    == new_name.strip().lower(),
                                    Product.id != product_id,
                                )
                                .first()
                            )

                            if duplicate:

                                st.error(
                                    "Another product already uses this name."
                                )

                            else:

                                product.name = new_name.strip()
                                product.category = (
                                    new_category.strip() or "Other"
                                )
                                product.selling_price = float(
                                    new_selling_price
                                )

                                session.commit()

                                st.success("Product details updated.")
                                st.rerun()

        except Exception as error:

            session.rollback()
            st.error(f"Could not load products: {error}")

        finally:
            session.close()

    # --------------------------------------------------------
    # ADD PRODUCT
    # --------------------------------------------------------

    with tab2:

        with st.form("add_product_form"):

            name = st.text_input("Product name")

            category = st.text_input(
                "Category",
                value="Other",
            )

            opening_stock = st.number_input(
                "Original stock",
                min_value=0,
                step=1,
            )

            unit_cost = st.number_input(
                "Purchase cost per unit (Rp)",
                min_value=0.0,
                step=1000.0,
            )

            selling_price = st.number_input(
                "Selling price per unit (Rp)",
                min_value=0.0,
                step=1000.0,
            )

            add_product = st.form_submit_button(
                "Add Product",
                use_container_width=True,
            )

            if add_product:

                if not name.strip():

                    st.error("Please enter a product name.")

                else:

                    session = get_session()

                    try:

                        existing = (
                            session.query(Product)
                            .filter(
                                func.lower(Product.name)
                                == name.strip().lower()
                            )
                            .first()
                        )

                        if existing:

                            st.error(
                                "This product already exists. "
                                "Use Update Stock instead."
                            )

                        else:

                            product = Product(
                                name=name.strip(),
                                category=category.strip() or "Other",
                                opening_stock=int(opening_stock),
                                current_stock=int(opening_stock),
                                unit_cost=float(unit_cost),
                                selling_price=float(selling_price),
                            )

                            session.add(product)
                            session.commit()

                            st.success("Product added.")
                            st.rerun()

                    except Exception as error:

                        session.rollback()
                        st.error(f"Could not add product: {error}")

                    finally:
                        session.close()

    # --------------------------------------------------------
    # UPDATE STOCK
    # --------------------------------------------------------

    with tab3:

        session = get_session()

        try:

            products = get_all_products(session)

            if not products:

                st.info("Add a product first.")

            else:

                product_options = {
                    p.name: p.id
                    for p in products
                }

                with st.form("stock_update_form"):

                    selected_name = st.selectbox(
                        "Product",
                        list(product_options.keys()),
                    )

                    product_id = product_options[selected_name]

                    movement_type = st.selectbox(
                        "What happened?",
                        [
                            "Purchase",
                            "Sale",
                            "Used / Damaged",
                        ],
                    )

                    quantity = st.number_input(
                        "Quantity",
                        min_value=1,
                        step=1,
                    )

                    selected_product = session.get(
                        Product,
                        product_id,
                    )

                    if movement_type == "Purchase":

                        purchase_cost = st.number_input(
                            "Purchase cost per unit (Rp)",
                            min_value=0.0,
                            value=float(selected_product.unit_cost),
                            step=1000.0,
                        )

                        sale_price = 0.0

                    elif movement_type == "Sale":

                        purchase_cost = 0.0

                        sale_price = st.number_input(
                            "Selling price per unit (Rp)",
                            min_value=0.0,
                            value=float(selected_product.selling_price),
                            step=1000.0,
                        )

                    else:

                        purchase_cost = 0.0
                        sale_price = 0.0

                    movement_date = st.date_input(
                        "Date",
                        value=app_today(),
                        format="DD/MM/YYYY",
                    )

                    note = st.text_input("Notes (optional)")

                    save_stock = st.form_submit_button(
                        "Save Stock Update",
                        use_container_width=True,
                    )

                    if save_stock:

                        try:

                            save_stock_movement(
                                session=session,
                                product=selected_product,
                                movement_date=movement_date,
                                kind=movement_type,
                                quantity=int(quantity),
                                unit_cost=float(purchase_cost),
                                unit_price=float(sale_price),
                                note=note.strip(),
                            )

                            session.commit()

                            st.success(
                                "Stock updated successfully."
                            )

                            st.rerun()

                        except Exception as error:

                            session.rollback()

                            st.error(
                                f"Stock was not changed: {error}"
                            )

        finally:
            session.close()


# ============================================================
# STOCK HISTORY
# ============================================================

elif page == "Stock History":

    st.title("Stock History")

    session = get_session()

    try:

        movements = get_all_movements(session)

        if not movements:

            st.info("No stock movements recorded.")

        else:

            data = []

            for movement in movements:

                product = session.get(
                    Product,
                    movement.product_id,
                )

                data.append({

                    "ID": movement.id,

                    "Date": format_date(movement.movement_date),

                    "Product": (
                        product.name if product else "Deleted product"
                    ),

                    "Type": movement.kind,

                    "Quantity": movement.quantity,

                    "Purchase / Used Cost": money(
                        movement.total_cost
                    ),

                    "Sales Value": money(
                        movement.total_revenue
                    ),

                    "Notes": movement.note,

                })

            st.dataframe(
                pd.DataFrame(data),
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            st.subheader("Edit or Delete Stock Update")

            movement_options = {

                (
                    f"#{m.id} | "
                    f"{format_date(m.movement_date)} | "
                    f"{m.kind} | "
                    f"{m.quantity}"
                ): m.id

                for m in movements

            }

            selected_label = st.selectbox(
                "Choose a stock update",
                list(movement_options.keys()),
            )

            movement_id = movement_options[selected_label]

            movement = session.get(
                StockMovement,
                movement_id,
            )

            product = session.get(
                Product,
                movement.product_id,
            )

            with st.form("edit_stock_movement_form"):

                new_kind = st.selectbox(
                    "Movement type",
                    [
                        "Purchase",
                        "Sale",
                        "Used / Damaged",
                    ],
                    index={
                        "purchase": 0,
                        "sale": 1,
                        "usage": 2,
                    }[movement_group(movement.kind)],
                )

                new_quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=max(1, int(movement.quantity)),
                    step=1,
                )

                if new_kind == "Purchase":

                    new_unit_cost = st.number_input(
                        "Purchase cost per unit (Rp)",
                        min_value=0.0,
                        value=float(movement.unit_cost),
                        step=1000.0,
                    )

                    new_unit_price = 0.0

                elif new_kind == "Sale":

                    new_unit_cost = 0.0

                    new_unit_price = st.number_input(
                        "Selling price per unit (Rp)",
                        min_value=0.0,
                        value=float(movement.unit_price),
                        step=1000.0,
                    )

                else:

                    new_unit_cost = 0.0
                    new_unit_price = 0.0

                new_date = st.date_input(
                    "Date",
                    value=movement.movement_date,
                    format="DD/MM/YYYY",
                )

                new_note = st.text_input(
                    "Notes",
                    value=movement.note or "",
                )

                save_movement = st.form_submit_button(
                    "Save Changes",
                    use_container_width=True,
                )

                if save_movement:

                    try:

                        save_stock_movement(
                            session=session,
                            product=product,
                            movement_date=new_date,
                            kind=new_kind,
                            quantity=int(new_quantity),
                            unit_cost=float(new_unit_cost),
                            unit_price=float(new_unit_price),
                            note=new_note.strip(),
                            movement=movement,
                        )

                        session.commit()

                        st.success(
                            "Stock movement updated and stock recalculated."
                        )

                        st.rerun()

                    except Exception as error:

                        session.rollback()

                        st.error(
                            f"Changes were not saved: {error}"
                        )

            st.divider()

            st.subheader("Delete Stock Update")

            confirm_delete = st.checkbox(
                "I understand that deleting this record changes the stock history.",
                key=f"delete_movement_{movement_id}",
            )

            if st.button(
                "Delete Stock Update",
                disabled=not confirm_delete,
            ):

                try:

                    opening_cost = get_opening_unit_cost(
                        session,
                        product,
                    )

                    session.delete(movement)
                    session.flush()

                    recalculate_product(
                        session,
                        product,
                        opening_cost,
                    )

                    session.commit()

                    st.success(
                        "Stock update deleted and remaining stock recalculated."
                    )

                    st.rerun()

                except Exception as error:

                    session.rollback()

                    st.error(
                        f"Could not delete stock update: {error}"
                    )

    finally:
        session.close()


# ============================================================
# DATA BACKUP
# ============================================================

elif page == "Data Backup":

    st.title("Data Backup")

    st.write(
        "Download copies of your records for safekeeping."
    )

    session = get_session()

    try:

        records = get_all_transactions(session)
        products = get_all_products(session)
        movements = get_all_movements(session)

        transaction_data = [

            {
                "ID": r.id,
                "Date": r.record_date.isoformat(),
                "Type": r.record_type,
                "Category": r.category,
                "Description": r.description,
                "Amount": r.amount,
            }

            for r in records

        ]

        product_data = [

            {
                "ID": p.id,
                "Name": p.name,
                "Category": p.category,
                "Original Stock": p.opening_stock,
                "Current Stock": p.current_stock,
                "Unit Cost": p.unit_cost,
                "Selling Price": p.selling_price,
            }

            for p in products

        ]

        movement_data = [

            {
                "ID": m.id,
                "Product ID": m.product_id,
                "Date": m.movement_date.isoformat(),
                "Type": m.kind,
                "Quantity": m.quantity,
                "Unit Cost": m.unit_cost,
                "Unit Price": m.unit_price,
                "Total Cost": m.total_cost,
                "Total Revenue": m.total_revenue,
                "Notes": m.note,
            }

            for m in movements

        ]

        col1, col2, col3 = st.columns(3)

        with col1:

            st.download_button(
                "Download Transactions",
                pd.DataFrame(transaction_data).to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="transactions.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col2:

            st.download_button(
                "Download Products",
                pd.DataFrame(product_data).to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="products.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col3:

            st.download_button(
                "Download Stock History",
                pd.DataFrame(movement_data).to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="stock_history.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.divider()

        st.subheader("Database")

        st.write(
            "The app uses the database configured in database.py. "
            "Your existing records are not intentionally replaced "
            "or reset by this version."
        )

        st.warning(
            "CSV downloads are not a complete database backup. "
            "Keep a separate backup of your SQLite database file "
            "or PostgreSQL database."
        )

    finally:
        session.close()


# ============================================================
# FOOTER
# ============================================================

st.sidebar.caption("Business Tracker")
