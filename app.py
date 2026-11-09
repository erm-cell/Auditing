
from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from database import (
    Product,
    MoneyRecord,
    StockMovement,
    SeedMarker,
    app_today,
    create_session_factory,
    get_database_url,
)


# =========================================================
# APP SETUP
# =========================================================

st.set_page_config(
    page_title="Business Tracker",
    layout="wide",
    initial_sidebar_state="expanded",
)

TODAY = app_today()
CURRENCY = "Rp"


@st.cache_resource
def get_sessions(url):
    return create_session_factory(url)


SessionLocal = get_sessions(get_database_url())


# =========================================================
# INITIAL INCOME
# Imported only once into each database
# =========================================================

def seed_starting_income():

    entries = [
        (date(2026, 11, 8), 238000, "Cash", "Cash"),
        (date(2026, 11, 8), 28000, "Income", "Imported record"),

        (date(2026, 11, 1), 8000, "Income", "Imported record"),
        (date(2026, 11, 1), 8000, "Income", "Imported record"),
        (date(2026, 11, 1), 38000, "Income", "Imported record"),
        (date(2026, 11, 1), 5000, "Income", "Imported record"),
        (date(2026, 11, 1), 16000, "Income", "Imported record"),
        (date(2026, 11, 1), 7000, "Income", "Imported record"),
        (date(2026, 11, 1), 12000, "Income", "Imported record"),
        (date(2026, 11, 1), 16000, "Income", "Imported record"),
        (date(2026, 11, 1), 8000, "Income", "Imported record"),
        (date(2026, 11, 1), 8000, "Income", "Imported record"),
        (date(2026, 11, 1), 16000, "Income", "Imported record"),
        (date(2026, 11, 1), 10000, "Income", "Imported record"),
        (date(2026, 11, 1), 40000, "Income", "Imported record"),

        (date(2026, 10, 26), 15000, "Income", "Imported record"),
        (date(2026, 10, 26), 15000, "Income", "Imported record"),
        (date(2026, 10, 26), 16000, "Income", "Imported record"),

        (date(2026, 10, 24), 8000, "Income", "Imported record"),
        (date(2026, 10, 24), 14000, "Income", "Imported record"),

        (date(2026, 10, 21), 17000, "Income", "Imported record"),

        (date(2026, 10, 20), 18000, "Income", "Imported record"),
        (date(2026, 10, 20), 10000, "Income", "Imported record"),

        (date(2026, 10, 18), 38000, "Income", "Imported record"),
        (date(2026, 10, 18), 6000, "Income", "Imported record"),

        (date(2026, 10, 16), 38000, "Income", "Imported record"),
        (date(2026, 10, 14), 38000, "Income", "Imported record"),
        (date(2026, 10, 13), 16000, "Income", "Imported record"),

        (date(2026, 10, 12), 24000, "Income", "Imported record"),
        (date(2026, 10, 12), 24000, "Income", "Imported record"),

        (date(2026, 10, 9), 214000, "Income", "Imported record"),
        (date(2026, 10, 9), 24000, "Income", "Imported record"),
        (date(2026, 10, 9), 8000, "Income", "Imported record"),
        (date(2026, 10, 9), 8000, "Income", "Imported record"),

        (date(2026, 10, 8), 18000, "Income", "Imported record"),
        (date(2026, 10, 8), 46000, "Income", "Imported record"),
        (date(2026, 10, 8), 38000, "Income", "Imported record"),
        (date(2026, 10, 8), 42000, "Income", "Imported record"),
    ]

    marker_key = "initial_income_import_2026_11"

    with SessionLocal() as db:

        if db.get(SeedMarker, marker_key):
            return

        for record_date, amount, category, description in entries:

            db.add(
                MoneyRecord(
                    record_date=record_date,
                    record_type="Income",
                    category=category,
                    description=description,
                    amount=float(amount),
                )
            )

        db.add(SeedMarker(key=marker_key))
        db.commit()


seed_starting_income()


# =========================================================
# DARK INTERFACE
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: #090d14;
    color: #f3f4f6;
}

[data-testid="stHeader"] {
    background: #090d14;
}

[data-testid="stSidebar"] {
    background: #0d1420;
    border-right: 1px solid #263244;
}

[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}

h1, h2, h3, h4, h5 {
    color: #f8fafc !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #d1d5db;
}

.page-title {
    color: #f8fafc;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 5px;
}

.page-subtitle {
    color: #a7b2c2;
    margin-bottom: 25px;
}

.section-heading {
    color: #f1f5f9;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 15px 0 10px;
}

div[data-testid="stMetric"],
div[data-testid="stForm"],
[data-testid="stExpander"] {
    background: #111a28;
    border: 1px solid #29364a;
    border-radius: 14px;
}

div[data-testid="stMetric"] {
    padding: 16px;
}

div[data-testid="stMetricLabel"] {
    color: #a7b2c2 !important;
}

div[data-testid="stMetricValue"] {
    color: #f8fafc !important;
}

label, [data-testid="stWidgetLabel"] p {
    color: #e5e7eb !important;
}

input, textarea {
    background: #0b1220 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #3b4a60 !important;
}

input::placeholder,
textarea::placeholder {
    color: #8492a6 !important;
    -webkit-text-fill-color: #8492a6 !important;
}

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
    background: #0b1220 !important;
    color: #ffffff !important;
    border-color: #3b4a60 !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"] {
    background: #111a28 !important;
}

[role="option"] {
    color: #ffffff !important;
}

[role="option"]:hover {
    background: #26364c !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #29364a;
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stTabs"] button {
    color: #cbd5e1 !important;
}

[data-testid="stAlert"] {
    background: #111a28;
    color: #e5e7eb;
}

button[kind="primary"] {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid #3b82f6 !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
}

button[kind="secondary"],
.stDownloadButton button {
    background: #1b2738 !important;
    color: #ffffff !important;
    border: 1px solid #3b4a60 !important;
    border-radius: 9px !important;
}

hr {
    border-color: #29364a;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value):

    return (
        f"{CURRENCY} {float(value or 0):,.0f}"
        .replace(",", ".")
    )


def heading(title, subtitle):

    st.markdown(
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def show_error(error):

    if isinstance(error, ValueError):
        st.error(str(error))

    elif isinstance(error, SQLAlchemyError):
        st.error(
            "Could not save your data. "
            "Please check your database connection."
        )

    else:
        st.error(f"Something went wrong: {error}")


def load_data():

    with SessionLocal() as db:

        products = list(
            db.scalars(
                select(Product).order_by(Product.name)
            ).all()
        )

        movements = list(
            db.scalars(
                select(StockMovement).order_by(
                    StockMovement.movement_date.desc(),
                    StockMovement.id.desc()
                )
            ).all()
        )

        records = list(
            db.scalars(
                select(MoneyRecord).order_by(
                    MoneyRecord.record_date.desc(),
                    MoneyRecord.id.desc()
                )
            ).all()
        )

    return products, movements, records


def money_frame(records):

    return pd.DataFrame(
        [
            {
                "Date": r.record_date.strftime("%d/%m/%Y"),
                "Type": r.record_type,
                "Category": r.category,
                "Details": r.description,
                "Amount": r.amount,
            }
            for r in records
        ],
        columns=[
            "Date", "Type", "Category", "Details", "Amount"
        ],
    )


def movement_frame(movements, products):

    names = {p.id: p.name for p in products}

    return pd.DataFrame(
        [
            {
                "Date": m.movement_date.strftime("%d/%m/%Y"),
                "Product": names.get(m.product_id, "Unknown"),
                "Action": m.kind,
                "Quantity": m.quantity,
                "Cost per item": money(m.unit_cost),
                "Selling price": money(m.unit_price),
                "Total cost": money(m.total_cost),
                "Sales value": money(m.total_revenue),
                "Note": m.note,
            }
            for m in movements
        ]
    )


def inventory_frame(products, movements):

    rows = []

    for p in products:

        product_moves = [
            m for m in movements
            if m.product_id == p.id
        ]

        restocked = sum(
            m.quantity for m in product_moves
            if m.kind == "Restock"
        )

        used = sum(
            m.quantity for m in product_moves
            if m.kind in ("Used", "Damaged")
        )

        sold = max(
            0,
            p.opening_stock
            + restocked
            - p.current_stock
            - used
        )

        sales = [
            m for m in product_moves
            if m.kind == "Sale"
        ]

        sales_value = sum(
            m.total_revenue for m in sales
        )

        sold_cost = sum(
            m.total_cost for m in sales
        )

        used_cost = sum(
            m.total_cost for m in product_moves
            if m.kind in ("Used", "Damaged")
        )

        rows.append({

            "Product": p.name,
            "Category": p.category,

            "Starting quantity": p.opening_stock,
            "Stock added": restocked,
            "Items sold": sold,

            "Sales value": money(sales_value),
            "Cost of sold items": money(sold_cost),

            "Used / damaged": used,
            "Cost of used / damaged": money(used_cost),

            "Remaining stock": p.current_stock,

            "Value of remaining stock": money(
                p.current_stock * p.unit_cost
            ),

            "Cost per item": money(p.unit_cost),
            "Selling price": money(p.selling_price),

        })

    return pd.DataFrame(rows)


# =========================================================
# PRODUCT ACTIONS
# =========================================================

def add_product(
    name,
    category,
    quantity,
    cost,
    selling_price,
):

    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Please enter a product name.")

    if cost <= 0 or selling_price <= 0:
        raise ValueError("Both prices must be greater than zero.")

    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    with SessionLocal() as db:

        existing = db.scalar(
            select(Product).where(
                func.lower(Product.name) == clean_name.lower()
            )
        )

        if existing:
            raise ValueError(
                "This product already exists. "
                "Use the existing product instead."
            )

        product = Product(
            name=clean_name,
            category=category.strip() or "Other",
            opening_stock=int(quantity),
            current_stock=int(quantity),
            unit_cost=float(cost),
            selling_price=float(selling_price),
        )

        db.add(product)
        db.flush()

        if quantity > 0:

            db.add(
                StockMovement(
                    product_id=product.id,
                    movement_date=TODAY,
                    kind="Initial stock",
                    quantity=int(quantity),
                    unit_cost=float(cost),
                    total_cost=int(quantity) * float(cost),
                    note="Starting stock",
                )
            )

        db.commit()


def record_sale(
    product_id,
    quantity,
    price,
    sale_date,
    note,
):

    with SessionLocal() as db:

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if quantity < 1 or quantity > product.current_stock:
            raise ValueError(
                f"Only {product.current_stock} items are available."
            )

        if price <= 0:
            raise ValueError("Selling price must be greater than zero.")

        total_cost = float(product.unit_cost) * quantity
        total_revenue = float(price) * quantity

        product.current_stock -= quantity
        product.selling_price = float(price)

        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=sale_date,
                kind="Sale",
                quantity=quantity,
                unit_cost=float(product.unit_cost),
                unit_price=float(price),
                total_cost=total_cost,
                total_revenue=total_revenue,
                note=note.strip(),
            )
        )

        db.add(
            MoneyRecord(
                record_date=sale_date,
                record_type="Income",
                category="Sales",
                description=f"{product.name} x {quantity}",
                amount=total_revenue,
            )
        )

        db.commit()


def add_stock(
    product_id,
    quantity,
    cost,
    stock_date,
    note,
):

    with SessionLocal() as db:

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if quantity < 1 or cost <= 0:
            raise ValueError("Enter a valid quantity and cost.")

        old_quantity = product.current_stock
        old_value = old_quantity * float(product.unit_cost)

        added_value = quantity * float(cost)
        new_quantity = old_quantity + quantity

        average_cost = (
            old_value + added_value
        ) / new_quantity

        product.current_stock = new_quantity
        product.unit_cost = average_cost

        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=stock_date,
                kind="Restock",
                quantity=quantity,
                unit_cost=float(cost),
                total_cost=added_value,
                note=note.strip(),
            )
        )

        db.add(
            MoneyRecord(
                record_date=stock_date,
                record_type="Expense",
                category="Stock purchase",
                description=f"Stock purchase: {product.name} x {quantity}",
                amount=added_value,
            )
        )

        db.commit()


def remove_stock(
    product_id,
    quantity,
    reason,
    movement_date,
    note,
):

    with SessionLocal() as db:

        product = db.get(Product, product_id)

        if product is None:
            raise ValueError("Product not found.")

        if quantity < 1 or quantity > product.current_stock:
            raise ValueError(
                f"Only {product.current_stock} items are available."
            )

        total_cost = quantity * float(product.unit_cost)

        product.current_stock -= quantity

        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=movement_date,
                kind=reason,
                quantity=quantity,
                unit_cost=float(product.unit_cost),
                total_cost=total_cost,
                note=note.strip(),
            )
        )

        db.add(
            MoneyRecord(
                record_date=movement_date,
                record_type="Expense",
                category=(
                    "Stock used"
                    if reason == "Used"
                    else "Damaged stock"
                ),
                description=f"{product.name} x {quantity}",
                amount=total_cost,
            )
        )

        db.commit()


# =========================================================
# LOAD DATABASE
# =========================================================

try:

    products, movements, records = load_data()

except SQLAlchemyError:

    st.error(
        "Could not connect to the database. "
        "Please check your database settings."
    )

    st.stop()


product_by_id = {p.id: p for p in products}

stock_table = inventory_frame(products, movements)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown("# Business Tracker")

    st.divider()

    page = st.radio(
        "Menu",
        [
            "Overview",
            "Products & stock",
            "Sales",
            "Income & expenses",
            "Download reports",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    st.caption("Currency: Indonesian Rupiah (Rp)")


# =========================================================
# OVERVIEW
# =========================================================

if page == "Overview":

    heading(
        "Overview",
        "Your business income, expenses and stock."
    )

    first_day = TODAY.replace(day=1)

    month_records = [
        r for r in records
        if first_day <= r.record_date <= TODAY
    ]

    income = sum(
        r.amount for r in month_records
        if r.record_type == "Income"
    )

    expenses = sum(
        r.amount for r in month_records
        if r.record_type == "Expense"
    )

    stock_value = sum(
        p.current_stock * p.unit_cost
        for p in products
    )

    a, b, c, d = st.columns(4)

    a.metric("Income this month", money(income))
    b.metric("Expenses this month", money(expenses))
    c.metric("Difference", money(income - expenses))
    d.metric("Stock value left", money(stock_value))

    left, right = st.columns([1.3, 1])

    with left:

        st.markdown(
            '<div class="section-heading">Income and expenses</div>',
            unsafe_allow_html=True,
        )

        monthly_rows = []

        for r in records:

            monthly_rows.append({

                "Month": r.record_date.strftime("%b %Y"),

                "Income": (
                    r.amount
                    if r.record_type == "Income"
                    else 0
                ),

                "Expenses": (
                    r.amount
                    if r.record_type == "Expense"
                    else 0
                ),

                "Sort": r.record_date.replace(day=1),

            })

        if monthly_rows:

            chart = pd.DataFrame(monthly_rows)

            chart = (
                chart.groupby(["Month", "Sort"], as_index=False)
                [["Income", "Expenses"]]
                .sum()
                .sort_values("Sort")
                .tail(6)
                .set_index("Month")
            )

            st.bar_chart(chart)

        else:

            st.info("Your chart will appear after you add records.")

    with right:

        st.markdown(
            '<div class="section-heading">Stock summary</div>',
            unsafe_allow_html=True,
        )

        st.metric("Products listed", len(products))

        st.metric(
            "Items currently in stock",
            sum(p.current_stock for p in products),
        )

        st.metric("Total stock cost", money(stock_value))

    st.markdown(
        '<div class="section-heading">Latest money records</div>',
        unsafe_allow_html=True,
    )

    if records:

        latest = money_frame(records[:10])

        latest["Amount"] = latest["Amount"].map(money)

        st.dataframe(
            latest,
            hide_index=True,
            use_container_width=True,
        )

    else:

        st.info("No money records yet.")


# =========================================================
# PRODUCTS AND STOCK
# =========================================================

elif page == "Products & stock":

    heading(
        "Products & stock",
        "Manage products, prices and remaining stock."
    )

    tab_list, tab_add, tab_update = st.tabs([
        "Product list",
        "Add a product",
        "Update stock",
    ])

    # PRODUCT LIST

    with tab_list:

        if products:

            st.dataframe(
                stock_table,
                hide_index=True,
                use_container_width=True,
            )

        else:

            st.info("No products yet. Add your first product.")

        if products:

            with st.expander("Change selling price"):

                options = {
                    p.name: p.id
                    for p in products
                }

                selected_name = st.selectbox(
                    "Product",
                    list(options),
                    key="price_product",
                )

                selected = product_by_id[options[selected_name]]

                with st.form("price_form"):

                    new_price = st.number_input(
                        "New selling price per item (Rp)",
                        min_value=1,
                        value=max(1, int(selected.selling_price)),
                        step=1000,
                    )

                    save_price = st.form_submit_button(
                        "Save price",
                        type="primary",
                    )

                if save_price:

                    try:

                        with SessionLocal() as db:

                            product = db.get(Product, selected.id)

                            product.selling_price = float(new_price)

                            db.commit()

                        st.success("Selling price updated.")

                        st.rerun()

                    except Exception as error:

                        show_error(error)

    # ADD PRODUCT

    with tab_add:

        st.markdown(
            '<div class="section-heading">Add a new product</div>',
            unsafe_allow_html=True,
        )

        with st.form("add_product_form", clear_on_submit=True):

            name = st.text_input(
                "Product name",
                placeholder="Example: Classic T-shirt",
            )

            category = st.text_input(
                "Category",
                placeholder="Example: Clothing",
                value="Other",
            )

            quantity = st.number_input(
                "Starting quantity",
                min_value=0,
                value=1,
                step=1,
            )

            a, b = st.columns(2)

            cost = a.number_input(
                "Cost per item (Rp)",
                min_value=1,
                value=1000,
                step=1000,
            )

            selling_price = b.number_input(
                "Selling price per item (Rp)",
                min_value=1,
                value=2000,
                step=1000,
            )

            submitted = st.form_submit_button(
                "Add product",
                type="primary",
                use_container_width=True,
            )

        if submitted:

            try:

                add_product(
                    name,
                    category,
                    quantity,
                    cost,
                    selling_price,
                )

                st.success(f"{name.strip()} added successfully.")

                st.rerun()

            except Exception as error:

                show_error(error)

    # UPDATE STOCK

    with tab_update:

        if not products:

            st.info("Add a product before updating stock.")

        else:

            action = st.radio(
                "Choose an action",
                ["Add stock", "Remove stock"],
                horizontal=True,
            )

            options = {
                f"{p.name} — {p.current_stock} left": p.id
                for p in products
            }

            selected_label = st.selectbox(
                "Product",
                list(options),
                key="stock_product",
            )

            selected = product_by_id[options[selected_label]]

            if action == "Add stock":

                with st.form("restock_form"):

                    a, b = st.columns(2)

                    qty = a.number_input(
                        "Quantity added",
                        min_value=1,
                        value=1,
                        step=1,
                    )

                    cost = b.number_input(
                        "Cost per new item (Rp)",
                        min_value=1,
                        value=max(1, int(selected.unit_cost)),
                        step=1000,
                    )

                    stock_date = st.date_input(
                        "Date",
                        value=TODAY,
                        format="DD/MM/YYYY",
                    )

                    note = st.text_input("Note (optional)")

                    submit = st.form_submit_button(
                        "Save added stock",
                        type="primary",
                        use_container_width=True,
                    )

                if submit:

                    try:

                        add_stock(
                            selected.id,
                            int(qty),
                            float(cost),
                            stock_date,
                            note,
                        )

                        st.success(
                            f"Added {qty} items. "
                            f"Purchase cost: {money(qty * cost)}."
                        )

                        st.rerun()

                    except Exception as error:

                        show_error(error)

            else:

                if selected.current_stock < 1:

                    st.info("There is no stock to remove.")

                else:

                    with st.form("remove_stock_form"):

                        a, b = st.columns(2)

                        qty = a.number_input(
                            "Quantity removed",
                            min_value=1,
                            max_value=int(selected.current_stock),
                            value=1,
                            step=1,
                        )

                        reason = b.selectbox(
                            "Reason",
                            ["Used", "Damaged"],
                        )

                        stock_date = st.date_input(
                            "Date",
                            value=TODAY,
                            format="DD/MM/YYYY",
                            key="remove_date",
                        )

                        note = st.text_input(
                            "Note (optional)",
                            key="remove_note",
                        )

                        submit = st.form_submit_button(
                            "Save stock change",
                            type="primary",
                            use_container_width=True,
                        )

                    if submit:

                        try:

                            remove_stock(
                                selected.id,
                                int(qty),
                                reason,
                                stock_date,
                                note,
                            )

                            st.success(
                                "Stock updated. Cost recorded: "
                                + money(qty * selected.unit_cost)
                            )

                            st.rerun()

                        except Exception as error:

                            show_error(error)

    st.markdown(
        '<div class="section-heading">Recent stock changes</div>',
        unsafe_allow_html=True,
    )

    if movements:

        st.dataframe(
            movement_frame(movements[:15], products),
            hide_index=True,
            use_container_width=True,
        )

    else:

        st.info("Stock changes will appear here.")


# =========================================================
# SALES
# =========================================================

elif page == "Sales":

    heading(
        "Sales",
        "Record sold products. Stock and income update automatically."
    )

    available = [
        p for p in products
        if p.current_stock > 0
    ]

    if not available:

        st.info("No products available. Add products or more stock first.")

    else:

        options = {
            f"{p.name} — {p.current_stock} left": p.id
            for p in available
        }

        selected_label = st.selectbox(
            "Product",
            list(options),
        )

        selected = product_by_id[options[selected_label]]

        st.caption(
            f"Current price: {money(selected.selling_price)} each "
            f"| Available: {selected.current_stock}"
        )

        with st.form("sale_form"):

            a, b = st.columns(2)

            quantity = a.number_input(
                "Quantity sold",
                min_value=1,
                max_value=int(selected.current_stock),
                value=1,
                step=1,
            )

            price = b.number_input(
                "Selling price per item (Rp)",
                min_value=1,
                value=max(1, int(selected.selling_price)),
                step=1000,
            )

            sale_date = st.date_input(
                "Sale date",
                value=TODAY,
                format="DD/MM/YYYY",
            )

            note = st.text_input("Note (optional)")

            submit = st.form_submit_button(
                "Save sale",
                type="primary",
                use_container_width=True,
            )

        if submit:

            try:

                record_sale(
                    selected.id,
                    int(quantity),
                    float(price),
                    sale_date,
                    note,
                )

                st.success(
                    f"Sale saved. Total received: "
                    f"{money(quantity * price)}."
                )

                st.rerun()

            except Exception as error:

                show_error(error)

    st.markdown(
        '<div class="section-heading">Recent sales</div>',
        unsafe_allow_html=True,
    )

    sales = [
        m for m in movements
        if m.kind == "Sale"
    ][:15]

    if sales:

        st.dataframe(
            movement_frame(sales, products),
            hide_index=True,
            use_container_width=True,
        )

    else:

        st.info("Your sales will appear here.")


# =========================================================
# INCOME AND EXPENSES
# =========================================================

elif page == "Income & expenses":

    heading(
        "Income & expenses",
        "Record money received and money paid out."
    )

    with st.form("money_form", clear_on_submit=True):

        a, b = st.columns(2)

        record_type = a.selectbox(
            "Type",
            ["Income", "Expense"],
        )

        amount = b.number_input(
            "Amount (Rp)",
            min_value=1,
            value=10000,
            step=1000,
        )

        c, d = st.columns(2)

        category = c.text_input(
            "Category",
            placeholder="Example: Rent, delivery, other sales",
        )

        record_date = d.date_input(
            "Date",
            value=TODAY,
            format="DD/MM/YYYY",
        )

        description = st.text_input(
            "Details",
            placeholder="What was the money for?",
        )

        submit = st.form_submit_button(
            "Save record",
            type="primary",
            use_container_width=True,
        )

    if submit:

        if not description.strip():

            st.error("Please enter some details.")

        else:

            try:

                with SessionLocal() as db:

                    db.add(
                        MoneyRecord(
                            record_date=record_date,
                            record_type=record_type,
                            category=category.strip() or "Other",
                            description=description.strip(),
                            amount=float(amount),
                        )
                    )

                    db.commit()

                st.success(f"{record_type} saved.")

                st.rerun()

            except Exception as error:

                show_error(error)

    st.markdown(
        '<div class="section-heading">Money records</div>',
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)

    date_from = a.date_input(
        "From",
        value=TODAY.replace(day=1),
        format="DD/MM/YYYY",
        key="money_from",
    )

    date_to = b.date_input(
        "To",
        value=TODAY,
        format="DD/MM/YYYY",
        key="money_to",
    )

    record_filter = c.selectbox(
        "Show",
        ["All", "Income", "Expense"],
    )

    filtered = [
        r for r in records
        if date_from <= r.record_date <= date_to
    ]

    if record_filter != "All":

        filtered = [
            r for r in filtered
            if r.record_type == record_filter
        ]

    if date_from > date_to:

        st.warning("The starting date must be before the ending date.")

    elif filtered:

        df = money_frame(filtered)

        df["Amount"] = df["Amount"].map(money)

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
        )

        total_income = sum(
            r.amount for r in filtered
            if r.record_type == "Income"
        )

        total_expenses = sum(
            r.amount for r in filtered
            if r.record_type == "Expense"
        )

        a, b, c = st.columns(3)

        a.metric("Income", money(total_income))
        b.metric("Expenses", money(total_expenses))
        c.metric(
            "Difference",
            money(total_income - total_expenses),
        )

    else:

        st.info("No records found for these dates.")


# =========================================================
# DOWNLOAD REPORTS
# =========================================================

elif page == "Download reports":

    heading(
        "Download reports",
        "Download your business records as CSV files."
    )

    stock_export = stock_table.copy()

    money_export = money_frame(records)

    movement_export = movement_frame(
        movements,
        products,
    )

    a, b, c = st.columns(3)

    with a:

        st.markdown("**Product and stock list**")

        st.caption(
            "Products, quantity sold, remaining stock and stock cost."
        )

        st.download_button(
            "Download stock CSV",
            data=stock_export.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="product_stock_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with b:

        st.markdown("**Income and expenses**")

        st.caption("All saved money records.")

        st.download_button(
            "Download money CSV",
            data=money_export.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="income_expense_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c:

        st.markdown("**Stock changes**")

        st.caption(
            "Sales, new stock and removed stock."
        )

        st.download_button(
            "Download stock changes CSV",
            data=movement_export.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="stock_changes_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()

    st.markdown("**How stock is calculated**")

    st.write("""
    - Items sold = starting quantity + stock added - remaining stock - used or damaged items.
    - Sales value = actual money received from recorded sales.
    - Cost of sold items = original cost of the sold products.
    - Value of remaining stock = remaining quantity multiplied by average cost.
    """)

    st.warning(
        "This version does not have separate user accounts. "
        "Everyone using the same app shares the same records. "
        "Keep access restricted and download backups regularly."
    )
