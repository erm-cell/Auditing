
from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from database import (
    MoneyRecord,
    Product,
    StockMovement,
    app_today,
    create_session_factory,
    get_database_url,
)

# --------------------------------------------------
# APP SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Business Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

TODAY = app_today()
CURRENCY = "Rp"


@st.cache_resource
def get_session_factory(database_url):
    return create_session_factory(database_url)


SessionLocal = get_session_factory(get_database_url())


# --------------------------------------------------
# DARK MODE DESIGN
# --------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

:root {
    color-scheme: dark;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp,
[data-testid="stAppViewContainer"] {
    background: #090d16 !important;
    color: #f4f7fb !important;
}

[data-testid="stHeader"] {
    background: #090d16 !important;
}

[data-testid="stSidebar"] {
    background: #0e1421 !important;
    border-right: 1px solid #263247;
}

[data-testid="stSidebar"] * {
    color: #e8edf5 !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
label,
.stCaption {
    color: #c3ccda !important;
}

h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
}

.page-title {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 5px;
}

.page-subtitle {
    color: #aab6c8;
    margin-bottom: 25px;
}

.section-title {
    color: #ffffff;
    font-size: 1.1rem;
    font-weight: 700;
    margin: 10px 0;
}

/* INPUT FIELDS */

div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
div[data-baseweb="select"] > div,
[data-testid="stDateInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {

    background: #151e2d !important;
    color: #ffffff !important;
    border: 1px solid #344258 !important;
    border-radius: 9px !important;
    -webkit-text-fill-color: #ffffff !important;
}

input, textarea {
    color: #ffffff !important;
    caret-color: white !important;
}

input::placeholder,
textarea::placeholder {
    color: #8795aa !important;
    -webkit-text-fill-color: #8795aa !important;
}

[data-baseweb="select"] *,
[data-baseweb="popover"] *,
[role="listbox"] *,
[role="option"] {
    color: #ffffff !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"] {
    background: #151e2d !important;
}

[role="option"]:hover {
    background: #24334a !important;
}

/* CARDS */

div[data-testid="stForm"],
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stMetric"] {

    background: #111a28 !important;
    border: 1px solid #253247 !important;
    border-radius: 14px !important;
}

div[data-testid="stMetric"] {
    padding: 16px;
}

div[data-testid="stMetricLabel"] {
    color: #aab6c8 !important;
}

div[data-testid="stMetricValue"] {
    color: #ffffff !important;
}

/* TABLES */

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #111a28 !important;
    border: 1px solid #253247 !important;
    border-radius: 12px;
    overflow: hidden;
}

/* BUTTONS */

button[kind="primary"] {
    background: #3478f6 !important;
    color: white !important;
    border: 1px solid #3478f6 !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
}

button[kind="secondary"],
.stDownloadButton button {
    background: #1a2638 !important;
    color: white !important;
    border: 1px solid #3a4b64 !important;
    border-radius: 9px !important;
}

hr {
    border-color: #253247 !important;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def money(value):
    return f"Rp {float(value or 0):,.0f}".replace(",", ".")


def heading(title, subtitle):
    st.markdown(
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def get_all_data():
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


def stock_report(products, movements):

    rows = []

    for p in products:

        pm = [
            m for m in movements
            if m.product_id == p.id
        ]

        restocked = sum(
            m.quantity for m in pm
            if m.kind == "Restock"
        )

        removed = sum(
            m.quantity for m in pm
            if m.kind in ("Used", "Damaged")
        )

        sold = max(
            0,
            p.opening_stock
            + restocked
            - p.current_stock
            - removed
        )

        sales = [
            m for m in pm
            if m.kind == "Sale"
        ]

        sales_value = sum(
            m.total_revenue for m in sales
        )

        cost_sold = sum(
            m.total_cost for m in sales
        )

        rows.append({

            "Product": p.name,
            "Category": p.category,

            "Starting stock": p.opening_stock,
            "Stock added": restocked,
            "Items sold": sold,

            "Sales value": sales_value,
            "Cost of sold items": cost_sold,

            "Remaining stock": p.current_stock,

            "Value of remaining stock":
                p.current_stock * p.unit_cost,

            "Cost per item": p.unit_cost,
            "Selling price": p.selling_price,

            "Low stock warning": p.low_stock_at,
        })

    return pd.DataFrame(rows)


def money_report(records):

    return pd.DataFrame([{

        "Date": r.record_date.isoformat(),
        "Type": r.record_type,
        "Category": r.category,
        "Details": r.description,
        "Amount": r.amount,

    } for r in records])


def movement_report(movements, products):

    names = {
        p.id: p.name
        for p in products
    }

    return pd.DataFrame([{

        "Date": m.movement_date.isoformat(),
        "Product": names.get(m.product_id, "Unknown"),
        "Action": m.kind,
        "Quantity": m.quantity,
        "Cost per item": m.unit_cost,
        "Selling price": m.unit_price,
        "Total stock cost": m.total_cost,
        "Sales value": m.total_revenue,
        "Note": m.note,

    } for m in movements])


# --------------------------------------------------
# ADD PRODUCT
# --------------------------------------------------

def save_product(
    name,
    category,
    starting_stock,
    unit_cost,
    selling_price,
    low_stock_at,
):

    clean_name = name.strip()

    if not clean_name:
        raise ValueError("Please enter a product name.")

    if unit_cost <= 0:
        raise ValueError("Please enter the cost per item.")

    if selling_price <= 0:
        raise ValueError("Please enter the selling price.")

    if starting_stock < 0 or low_stock_at < 0:
        raise ValueError("Stock cannot be negative.")

    with SessionLocal() as db:

        existing = db.scalar(
            select(Product).where(
                func.lower(Product.name) == clean_name.lower()
            )
        )

        if existing:
            raise ValueError(
                "This product already exists. Please use a different name."
            )

        product = Product(

            name=clean_name,
            category=category.strip() or "Other",

            opening_stock=int(starting_stock),
            current_stock=int(starting_stock),

            unit_cost=float(unit_cost),
            selling_price=float(selling_price),

            low_stock_at=int(low_stock_at),
        )

        db.add(product)
        db.flush()

        if int(starting_stock) > 0:

            db.add(StockMovement(

                product_id=product.id,
                movement_date=TODAY,

                kind="Initial stock",
                quantity=int(starting_stock),

                unit_cost=float(unit_cost),

                total_cost=(
                    int(starting_stock)
                    * float(unit_cost)
                ),

                note="Starting stock",
            ))

        db.commit()


# --------------------------------------------------
# RECORD A SALE
# --------------------------------------------------

def save_sale(
    product_id,
    quantity,
    sale_price,
    sale_date,
    note,
):

    with SessionLocal() as db:

        p = db.get(Product, int(product_id))

        if p is None:
            raise ValueError("Product not found.")

        if int(quantity) < 1 or int(quantity) > p.current_stock:
            raise ValueError(
                f"Only {p.current_stock} items are available."
            )

        total_cost = (
            float(p.unit_cost) * int(quantity)
        )

        total_revenue = (
            float(sale_price) * int(quantity)
        )

        db.add(StockMovement(

            product_id=p.id,
            movement_date=sale_date,

            kind="Sale",
            quantity=int(quantity),

            unit_cost=float(p.unit_cost),
            unit_price=float(sale_price),

            total_cost=total_cost,
            total_revenue=total_revenue,

            note=note.strip(),
        ))

        p.current_stock -= int(quantity)
        p.selling_price = float(sale_price)

        db.add(MoneyRecord(

            record_date=sale_date,
            record_type="Income",

            category="Sales",

            description=(
                f"{p.name} x {int(quantity)}"
            ),

            amount=total_revenue,
        ))

        db.commit()


# --------------------------------------------------
# ADD MORE STOCK
# --------------------------------------------------

def save_restock(
    product_id,
    quantity,
    cost_each,
    stock_date,
    note,
):

    with SessionLocal() as db:

        p = db.get(Product, int(product_id))

        if p is None:
            raise ValueError("Product not found.")

        quantity = int(quantity)

        if quantity < 1 or cost_each <= 0:
            raise ValueError(
                "Enter a quantity and cost greater than zero."
            )

        old_quantity = p.current_stock

        old_value = (
            old_quantity * float(p.unit_cost)
        )

        added_value = (
            quantity * float(cost_each)
        )

        new_quantity = old_quantity + quantity

        new_average_cost = (
            (old_value + added_value) / new_quantity
        )

        db.add(StockMovement(

            product_id=p.id,
            movement_date=stock_date,

            kind="Restock",
            quantity=quantity,

            unit_cost=float(cost_each),
            total_cost=added_value,

            note=note.strip(),
        ))

        p.current_stock = new_quantity
        p.unit_cost = new_average_cost

        db.add(MoneyRecord(

            record_date=stock_date,
            record_type="Expense",

            category="Stock purchase",

            description=f"Restock: {p.name} x {quantity}",

            amount=added_value,
        ))

        db.commit()


# --------------------------------------------------
# REMOVE STOCK
# --------------------------------------------------

def remove_stock(
    product_id,
    quantity,
    reason,
    movement_date,
    note,
):

    with SessionLocal() as db:

        p = db.get(Product, int(product_id))

        if p is None:
            raise ValueError("Product not found.")

        quantity = int(quantity)

        if quantity < 1 or quantity > p.current_stock:
            raise ValueError(
                f"Only {p.current_stock} items are available."
            )

        total_cost = (
            quantity * float(p.unit_cost)
        )

        p.current_stock -= quantity

        db.add(StockMovement(

            product_id=p.id,
            movement_date=movement_date,

            kind=reason,
            quantity=quantity,

            unit_cost=float(p.unit_cost),
            total_cost=total_cost,

            note=note.strip(),
        ))

        db.add(MoneyRecord(

            record_date=movement_date,
            record_type="Expense",

            category=(
                "Stock used"
                if reason == "Used"
                else "Damaged stock"
            ),

            description=f"{p.name} x {quantity}",

            amount=total_cost,
        ))

        db.commit()


def show_error(error):

    if isinstance(error, ValueError):
        st.error(str(error))

    elif isinstance(error, SQLAlchemyError):
        st.error(
            "Could not save the data. "
            "Please check your database connection."
        )

    else:
        st.error(f"Something went wrong: {error}")


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:

    st.markdown("## 📊 Business Tracker")

    st.caption("Money and stock, made simple")

    st.divider()

    page = st.radio(
        "Menu",
        [
            "Overview",
            "Products & stock",
            "Sales",
            "Income & expenses",
            "Reports",
        ]
    )

    st.divider()

    st.caption("Currency: Indonesian Rupiah (Rp)")


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

try:

    products, movements, records = get_all_data()

except SQLAlchemyError:

    st.error(
        "The database could not be opened. "
        "Please check your database settings."
    )

    st.stop()


product_by_id = {
    p.id: p
    for p in products
}

stock_df = stock_report(products, movements)


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

if page == "Overview":

    heading(
        "Overview",
        "Your business money and stock at a glance."
    )

    first_day = TODAY.replace(day=1)

    this_month = [
        r for r in records
        if first_day <= r.record_date <= TODAY
    ]

    income = sum(
        r.amount for r in this_month
        if r.record_type == "Income"
    )

    expenses = sum(
        r.amount for r in this_month
        if r.record_type == "Expense"
    )

    stock_value = sum(
        p.current_stock * p.unit_cost
        for p in products
    )

    a, b, c, d = st.columns(4)

    a.metric("Income this month", money(income))

    b.metric("Expenses this month", money(expenses))

    c.metric(
        "Money left after expenses",
        money(income - expenses)
    )

    d.metric(
        "Cost of stock left",
        money(stock_value)
    )

    left, right = st.columns([1.3, 1])

    with left:

        st.markdown(
            '<div class="section-title">Income and expenses</div>',
            unsafe_allow_html=True
        )

        if records:

            monthly = pd.DataFrame([{

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

            } for r in records])

            monthly = monthly.groupby(
                ["Month", "Sort"],
                as_index=False
            )[["Income", "Expenses"]].sum()

            monthly = monthly.sort_values(
                "Sort"
            ).tail(6).set_index("Month")

            st.bar_chart(
                monthly[["Income", "Expenses"]]
            )

        else:

            st.info(
                "Your chart will appear after you add records."
            )

    with right:

        st.markdown(
            '<div class="section-title">Products running low</div>',
            unsafe_allow_html=True
        )

        low = [
            p for p in products
            if p.current_stock <= p.low_stock_at
        ]

        if low:

            st.dataframe(
                pd.DataFrame([{
                    "Product": p.name,
                    "Left": p.current_stock,
                    "Warning at": p.low_stock_at,
                } for p in low]),
                hide_index=True,
                use_container_width=True
            )

        else:

            st.success("No products are running low.")

    st.markdown(
        '<div class="section-title">Latest money records</div>',
        unsafe_allow_html=True
    )

    if records:

        latest = money_report(records[:10])

        latest["Amount"] = latest["Amount"].map(money)

        st.dataframe(
            latest,
            hide_index=True,
            use_container_width=True
        )

    else:

        st.info("No money records yet.")


# --------------------------------------------------
# PRODUCTS & STOCK
# --------------------------------------------------

elif page == "Products & stock":

    heading(
        "Products & stock",
        "Add products, enter their prices, and see how many are left."
    )

    tab_add, tab_list, tab_update = st.tabs([
        "➕ Add a product",
        "Product list",
        "Update stock"
    ])

    # ADD PRODUCT

    with tab_add:

        st.markdown(
            '<div class="section-title">Product details</div>',
            unsafe_allow_html=True
        )

        with st.form(
            "add_product_form",
            clear_on_submit=True
        ):

            product_name = st.text_input(
                "Product name",
                placeholder="Example: Classic T-shirt"
            )

            category = st.text_input(
                "Category",
                value="Other",
                placeholder="Example: Clothing"
            )

            col1, col2 = st.columns(2)

            starting_stock = col1.number_input(
                "Starting stock (items)",
                min_value=0,
                value=0,
                step=1
            )

            low_stock_at = col2.number_input(
                "Show warning when stock reaches",
                min_value=0,
                value=5,
                step=1
            )

            col3, col4 = st.columns(2)

            unit_cost = col3.number_input(
                "Your cost per item (Rp)",
                min_value=0,
                value=1000,
                step=1000
            )

            selling_price = col4.number_input(
                "Selling price per item (Rp)",
                min_value=0,
                value=2000,
                step=1000
            )

            st.caption(
                "Enter what you paid for one item "
                "and the price you plan to sell it for."
            )

            submitted = st.form_submit_button(
                "Save product",
                type="primary",
                use_container_width=True
            )

        if submitted:

            try:

                save_product(
                    product_name,
                    category,
                    starting_stock,
                    unit_cost,
                    selling_price,
                    low_stock_at
                )

                st.success(
                    f"{product_name.strip()} has been added."
                )

                st.rerun()

            except Exception as error:

                show_error(error)

    # PRODUCT LIST

    with tab_list:

        if products:

            view = stock_df.copy()

            money_columns = [
                "Sales value",
                "Cost of sold items",
                "Value of remaining stock",
                "Cost per item",
                "Selling price",
            ]

            for col in money_columns:
                view[col] = view[col].map(money)

            st.dataframe(
                view,
                hide_index=True,
                use_container_width=True
            )

            st.caption(
                "Items sold = starting stock + stock added "
                "- remaining stock - items used or damaged."
            )

            st.caption(
                "Sales value uses the selling price saved "
                "when each sale was recorded."
            )

        else:

            st.info(
                "No products yet. Open the Add a product tab "
                "to add your first product."
            )

        if products:

            with st.expander(
                "Change a product's selling price"
            ):

                price_options = {
                    p.name: p.id
                    for p in products
                }

                chosen_name = st.selectbox(
                    "Choose product",
                    list(price_options),
                    key="change_price_product"
                )

                chosen = product_by_id[
                    price_options[chosen_name]
                ]

                with st.form("change_price_form"):

                    new_price = st.number_input(
                        "New selling price per item (Rp)",
                        min_value=1,
                        value=max(1, int(chosen.selling_price)),
                        step=1000
                    )

                    save_price = st.form_submit_button(
                        "Save new price",
                        type="primary"
                    )

                if save_price:

                    try:

                        with SessionLocal() as db:

                            p = db.get(Product, chosen.id)

                            p.selling_price = float(new_price)

                            db.commit()

                        st.success("Selling price updated.")

                        st.rerun()

                    except Exception as error:

                        show_error(error)

    # UPDATE STOCK

    with tab_update:

        if not products:

            st.info("Add a product first.")

        else:

            update_type = st.radio(
                "What would you like to do?",
                ["Add more stock", "Remove stock"],
                horizontal=True
            )

            stock_options = {
                f"{p.name} ({p.current_stock} left)": p.id
                for p in products
            }

            chosen_label = st.selectbox(
                "Product",
                list(stock_options),
                key="update_stock_product"
            )

            chosen = product_by_id[
                stock_options[chosen_label]
            ]

            if update_type == "Add more stock":

                with st.form("restock_form"):

                    col1, col2 = st.columns(2)

                    qty = col1.number_input(
                        "How many items did you add?",
                        min_value=1,
                        value=1,
                        step=1
                    )

                    cost = col2.number_input(
                        "Cost per new item (Rp)",
                        min_value=1,
                        value=max(1, int(chosen.unit_cost)),
                        step=1000
                    )

                    movement_date = st.date_input(
                        "Date",
                        value=TODAY
                    )

                    note = st.text_input(
                        "Note (optional)"
                    )

                    ok = st.form_submit_button(
                        "Save added stock",
                        type="primary",
                        use_container_width=True
                    )

                if ok:

                    try:

                        save_restock(
                            chosen.id,
                            qty,
                            cost,
                            movement_date,
                            note
                        )

                        st.success(
                            f"Added {qty} items. "
                            f"Purchase cost: {money(qty * cost)}."
                        )

                        st.rerun()

                    except Exception as error:

                        show_error(error)

            else:

                if chosen.current_stock < 1:

                    st.info("There is no stock left to remove.")

                else:

                    with st.form("remove_form"):

                        col1, col2 = st.columns(2)

                        qty = col1.number_input(
                            "How many items?",
                            min_value=1,
                            max_value=int(chosen.current_stock),
                            value=1,
                            step=1
                        )

                        reason = col2.selectbox(
                            "Reason",
                            ["Used", "Damaged"]
                        )

                        movement_date = st.date_input(
                            "Date",
                            value=TODAY,
                            key="remove_date"
                        )

                        note = st.text_input(
                            "Note (optional)",
                            key="remove_note"
                        )

                        ok = st.form_submit_button(
                            "Save stock change",
                            type="primary",
                            use_container_width=True
                        )

                    if ok:

                        try:

                            remove_stock(
                                chosen.id,
                                qty,
                                reason,
                                movement_date,
                                note
                            )

                            st.success(
                                "Stock updated. Cost recorded: "
                                + money(qty * chosen.unit_cost)
                            )

                            st.rerun()

                        except Exception as error:

                            show_error(error)

    # STOCK HISTORY

    st.markdown(
        '<div class="section-title">Latest stock changes</div>',
        unsafe_allow_html=True
    )

    if movements:

        recent = movement_report(
            movements[:15],
            products
        )

        money_cols = [
            "Cost per item",
            "Selling price",
            "Total stock cost",
            "Sales value",
        ]

        for col in money_cols:
            recent[col] = recent[col].map(money)

        st.dataframe(
            recent,
            hide_index=True,
            use_container_width=True
        )

    else:

        st.info("Stock changes will appear here.")


# --------------------------------------------------
# SALES
# --------------------------------------------------

elif page == "Sales":

    heading(
        "Sales",
        "Record items sold. Stock and income update automatically."
    )

    available = [
        p for p in products
        if p.current_stock > 0
    ]

    if not available:

        st.info(
            "No products available. Add a product "
            "or add more stock first."
        )

    else:

        sale_options = {
            f"{p.name} — {p.current_stock} left": p.id
            for p in available
        }

        chosen_label = st.selectbox(
            "Product",
            list(sale_options)
        )

        chosen = product_by_id[
            sale_options[chosen_label]
        ]

        st.caption(
            f"Current selling price: {money(chosen.selling_price)} each "
            f"· Available: {chosen.current_stock}"
        )

        with st.form("sale_form"):

            col1, col2 = st.columns(2)

            quantity = col1.number_input(
                "Quantity sold",
                min_value=1,
                max_value=int(chosen.current_stock),
                value=1,
                step=1
            )

            sale_price = col2.number_input(
                "Selling price per item (Rp)",
                min_value=1,
                value=max(1, int(chosen.selling_price)),
                step=1000
            )

            sale_date = st.date_input(
                "Sale date",
                value=TODAY
            )

            note = st.text_input(
                "Note (optional)",
                placeholder="Customer or order number"
            )

            ok = st.form_submit_button(
                "Save sale",
                type="primary",
                use_container_width=True
            )

        if ok:

            try:

                save_sale(
                    chosen.id,
                    quantity,
                    sale_price,
                    sale_date,
                    note
                )

                st.success(
                    f"Sale saved: {quantity} items, "
                    f"total {money(quantity * sale_price)}."
                )

                st.rerun()

            except Exception as error:

                show_error(error)

    st.markdown(
        '<div class="section-title">Recent sales</div>',
        unsafe_allow_html=True
    )

    sales = [
        m for m in movements
        if m.kind == "Sale"
    ][:15]

    if sales:

        sales_df = pd.DataFrame([{

            "Date": m.movement_date.isoformat(),

            "Product": (
                product_by_id[m.product_id].name
                if m.product_id in product_by_id
                else "Unknown"
            ),

            "Quantity": m.quantity,
            "Sales value": money(m.total_revenue),
            "Item cost": money(m.total_cost),
            "Note": m.note,

        } for m in sales])

        st.dataframe(
            sales_df,
            hide_index=True,
            use_container_width=True
        )

    else:

        st.info("Your sales will appear here.")


# --------------------------------------------------
# INCOME & EXPENSES
# --------------------------------------------------

elif page == "Income & expenses":

    heading(
        "Income & expenses",
        "Add money received or money paid out. "
        "Product sales are added automatically."
    )

    with st.form(
        "money_form",
        clear_on_submit=True
    ):

        col1, col2 = st.columns(2)

        record_type = col1.selectbox(
            "Money received or paid?",
            ["Income", "Expense"]
        )

        amount = col2.number_input(
            "Amount (Rp)",
            min_value=1,
            value=10000,
            step=1000
        )

        col3, col4 = st.columns(2)

        category = col3.text_input(
            "Category",
            placeholder="Rent, delivery, other sales..."
        )

        record_date = col4.date_input(
            "Date",
            value=TODAY
        )

        description = st.text_input(
            "Details",
            placeholder="What was this payment for?"
        )

        ok = st.form_submit_button(
            "Save record",
            type="primary",
            use_container_width=True
        )

    if ok:

        if not description.strip():

            st.error("Please enter a short description.")

        else:

            try:

                with SessionLocal() as db:

                    db.add(MoneyRecord(

                        record_date=record_date,
                        record_type=record_type,

                        category=category.strip() or "Other",
                        description=description.strip(),

                        amount=float(amount),
                    ))

                    db.commit()

                st.success(f"{record_type} saved.")

                st.rerun()

            except Exception as error:

                show_error(error)

    st.markdown(
        '<div class="section-title">Money records</div>',
        unsafe_allow_html=True
    )

    f1, f2, f3 = st.columns(3)

    date_from = f1.date_input(
        "From",
        value=TODAY.replace(day=1),
        key="filter_from"
    )

    date_to = f2.date_input(
        "To",
        value=TODAY,
        key="filter_to"
    )

    kind = f3.selectbox(
        "Show",
        ["All", "Income", "Expense"],
        key="filter_kind"
    )

    filtered = [
        r for r in records
        if date_from <= r.record_date <= date_to
    ]

    if kind != "All":

        filtered = [
            r for r in filtered
            if r.record_type == kind
        ]

    if date_from > date_to:

        st.warning(
            "The start date must be before the end date."
        )

    elif filtered:

        df = money_report(filtered)

        df["Amount"] = df["Amount"].map(money)

        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True
        )

        total_in = sum(
            r.amount for r in filtered
            if r.record_type == "Income"
        )

        total_out = sum(
            r.amount for r in filtered
            if r.record_type == "Expense"
        )

        a, b, c = st.columns(3)

        a.metric("Income", money(total_in))
        b.metric("Expenses", money(total_out))

        c.metric(
            "Difference",
            money(total_in - total_out)
        )

    else:

        st.info("No records found for those dates.")


# --------------------------------------------------
# REPORTS
# --------------------------------------------------

elif page == "Reports":

    heading(
        "Reports",
        "Download your business records for Excel "
        "or Google Sheets."
    )

    stock_export = stock_df.copy()

    money_export = money_report(records)

    movement_export = movement_report(
        movements,
        products
    )

    a, b, c = st.columns(3)

    with a:

        st.markdown("**Product and stock list**")

        st.caption(
            "Starting stock, sold items, sales value "
            "and remaining stock."
        )

        st.download_button(
            "Download stock CSV",
            stock_export.to_csv(index=False).encode("utf-8-sig"),
            "product_stock_report.csv",
            "text/csv",
            use_container_width=True
        )

    with b:

        st.markdown("**Income and expenses**")

        st.caption("All saved money records.")

        st.download_button(
            "Download money CSV",
            money_export.to_csv(index=False).encode("utf-8-sig"),
            "income_expense_report.csv",
            "text/csv",
            use_container_width=True
        )

    with c:

        st.markdown("**Stock changes**")

        st.caption(
            "Every sale, stock purchase, and stock removal."
        )

        st.download_button(
            "Download stock changes CSV",
            movement_export.to_csv(index=False).encode("utf-8-sig"),
            "stock_changes_report.csv",
            "text/csv",
            use_container_width=True
        )

    st.divider()

    st.markdown("**How the stock numbers work**")

    st.write("""
    - Items sold = starting stock + stock added - stock left - items used or damaged.
    - Sales value = actual selling prices saved for sales.
    - Cost of sold items = what those sold items cost you.
    - Value left = current stock multiplied by average cost per item.
    """)

    st.warning(
        "This app does not have user accounts. "
        "Keep access restricted if you enter private business records. "
        "Download reports regularly as backups."
    )
