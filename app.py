from __future__ import annotations

from datetime import date, timedelta
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


# -----------------------------------------------------------------------------
# App setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Business Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CURRENCY_SYMBOL = "Rp"
TODAY = app_today()


@st.cache_resource
def get_sessions(database_url: str):
    return create_session_factory(database_url)


SessionLocal = get_sessions(get_database_url())

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
        .stApp { background: #f5f7fb; }
        [data-testid="stHeader"] { background: rgba(245,247,251,0.9); }
        [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e6eaf1; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #64748b; }
        .page-eyebrow { color: #64748b; font-size: 0.78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; margin-bottom: .2rem; }
        .page-title { color: #152238; font-size: 2rem; line-height: 1.2; font-weight: 700; margin: 0 0 .35rem 0; }
        .page-subtitle { color: #64748b; margin: 0 0 1.35rem 0; font-size: .98rem; }
        div[data-testid="stMetric"] { background: #fff; border: 1px solid #e6eaf1; padding: 16px 18px; border-radius: 14px; }
        div[data-testid="stMetricLabel"] { color: #64748b; }
        div[data-testid="stMetricValue"] { color: #152238; }
        div[data-testid="stForm"] { background: #fff; border: 1px solid #e6eaf1; padding: 18px; border-radius: 14px; }
        div[data-testid="stDataFrame"] { border: 1px solid #e6eaf1; border-radius: 12px; overflow: hidden; }
        .small-note { color: #64748b; font-size: .86rem; }
        .section-heading { color: #152238; font-size: 1.12rem; font-weight: 700; margin: .2rem 0 .7rem 0; }
        button[kind="primary"] { border-radius: 9px; font-weight: 600; }
        .stDownloadButton button { border-radius: 9px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float | int | None) -> str:
    amount = float(value or 0)
    return f"{CURRENCY_SYMBOL} {amount:,.0f}".replace(",", ".")


def page_heading(title: str, subtitle: str, eyebrow: str = "BUSINESS TRACKER") -> None:
    st.markdown(
        f'<div class="page-eyebrow">{eyebrow}</div>'
        f'<div class="page-title">{title}</div>'
        f'<div class="page-subtitle">{subtitle}</div>',
        unsafe_allow_html=True,
    )


def load_data() -> tuple[list[Product], list[StockMovement], list[MoneyRecord]]:
    with SessionLocal() as db:
        products = list(db.scalars(select(Product).order_by(Product.name)).all())
        movements = list(
            db.scalars(select(StockMovement).order_by(StockMovement.movement_date.desc(), StockMovement.id.desc())).all()
        )
        records = list(
            db.scalars(select(MoneyRecord).order_by(MoneyRecord.record_date.desc(), MoneyRecord.id.desc())).all()
        )
    return products, movements, records


def inventory_rows(products: list[Product], movements: list[StockMovement]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for product in products:
        product_moves = [m for m in movements if m.product_id == product.id]
        restocked = sum(m.quantity for m in product_moves if m.kind == "Restock")
        sold_revenue = sum(m.total_revenue for m in product_moves if m.kind == "Sale")
        cost_sold = sum(m.total_cost for m in product_moves if m.kind == "Sale")
        used_moves = [m for m in product_moves if m.kind in ("Used", "Damaged")]
        used_qty = sum(m.quantity for m in used_moves)
        used_cost = sum(m.total_cost for m in used_moves)

        # This is the requested stock-difference calculation. Other stock removals
        # are subtracted so only items sold are counted as sales.
        sold_by_difference = max(
            0,
            product.opening_stock + restocked - product.current_stock - used_qty,
        )

        rows.append(
            {
                "Product": product.name,
                "Group": product.category,
                "Original stock": product.opening_stock,
                "Added later": restocked,
                "Sold": sold_by_difference,
                "Sales value": sold_revenue,
                "Cost of sold items": cost_sold,
                "Used / damaged": used_qty,
                "Cost of used / damaged": used_cost,
                "Left in stock": product.current_stock,
                "Value left": product.current_stock * product.unit_cost,
                "Cost per item": product.unit_cost,
                "Selling price": product.selling_price,
                "Low stock alert": product.low_stock_at,
            }
        )

    columns = [
        "Product", "Group", "Original stock", "Added later", "Sold", "Sales value",
        "Cost of sold items", "Used / damaged", "Cost of used / damaged", "Left in stock",
        "Value left", "Cost per item", "Selling price", "Low stock alert",
    ]
    return pd.DataFrame(rows, columns=columns)


def money_frame(records: list[MoneyRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date": r.record_date.isoformat(),
                "Type": r.record_type,
                "Group": r.category,
                "Details": r.description,
                "Amount (Rp)": r.amount,
            }
            for r in records
        ],
        columns=["Date", "Type", "Group", "Details", "Amount (Rp)"],
    )


def movement_frame(movements: list[StockMovement], products: list[Product]) -> pd.DataFrame:
    names = {p.id: p.name for p in products}
    return pd.DataFrame(
        [
            {
                "Date": m.movement_date.isoformat(),
                "Product": names.get(m.product_id, "Unknown product"),
                "Action": m.kind,
                "Quantity": m.quantity,
                "Cost per item (Rp)": m.unit_cost,
                "Sale price per item (Rp)": m.unit_price,
                "Total stock cost (Rp)": m.total_cost,
                "Sales value (Rp)": m.total_revenue,
                "Note": m.note,
            }
            for m in movements
        ],
        columns=[
            "Date", "Product", "Action", "Quantity", "Cost per item (Rp)",
            "Sale price per item (Rp)", "Total stock cost (Rp)", "Sales value (Rp)", "Note",
        ],
    )


def record_sale(product_id: int, quantity: int, selling_price: float, sale_date: date, note: str) -> None:
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if product is None:
            raise ValueError("That product could not be found.")
        if quantity < 1:
            raise ValueError("Enter a quantity of at least 1.")
        if quantity > product.current_stock:
            raise ValueError(f"Only {product.current_stock} item(s) are left in stock.")

        item_cost = float(product.unit_cost)
        total_cost = item_cost * quantity
        total_revenue = float(selling_price) * quantity

        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=sale_date,
                kind="Sale",
                quantity=quantity,
                unit_cost=item_cost,
                unit_price=float(selling_price),
                total_cost=total_cost,
                total_revenue=total_revenue,
                note=note.strip(),
            )
        )
        product.current_stock -= quantity
        product.selling_price = float(selling_price)
        db.add(
            MoneyRecord(
                record_date=sale_date,
                record_type="Income",
                category="Sales",
                description=f"{product.name} × {quantity}" + (f" — {note.strip()}" if note.strip() else ""),
                amount=total_revenue,
            )
        )
        db.commit()


def add_stock(product_id: int, quantity: int, purchase_cost: float, stock_date: date, note: str) -> None:
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if product is None:
            raise ValueError("That product could not be found.")
        if quantity < 1:
            raise ValueError("Enter a quantity of at least 1.")

        old_quantity = product.current_stock
        new_quantity = old_quantity + quantity
        old_stock_value = old_quantity * float(product.unit_cost)
        new_stock_value = old_stock_value + (quantity * float(purchase_cost))
        new_average_cost = new_stock_value / new_quantity if new_quantity else 0

        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=stock_date,
                kind="Restock",
                quantity=quantity,
                unit_cost=float(purchase_cost),
                total_cost=quantity * float(purchase_cost),
                note=note.strip(),
            )
        )
        product.current_stock = new_quantity
        product.unit_cost = new_average_cost
        db.add(
            MoneyRecord(
                record_date=stock_date,
                record_type="Expense",
                category="Stock purchase",
                description=f"Restock: {product.name} × {quantity}" + (f" — {note.strip()}" if note.strip() else ""),
                amount=quantity * float(purchase_cost),
            )
        )
        db.commit()


def remove_stock(product_id: int, quantity: int, reason: str, movement_date: date, note: str) -> None:
    with SessionLocal() as db:
        product = db.get(Product, product_id)
        if product is None:
            raise ValueError("That product could not be found.")
        if quantity < 1:
            raise ValueError("Enter a quantity of at least 1.")
        if quantity > product.current_stock:
            raise ValueError(f"Only {product.current_stock} item(s) are left in stock.")

        item_cost = float(product.unit_cost)
        total_cost = item_cost * quantity
        product.current_stock -= quantity
        db.add(
            StockMovement(
                product_id=product.id,
                movement_date=movement_date,
                kind=reason,
                quantity=quantity,
                unit_cost=item_cost,
                total_cost=total_cost,
                note=note.strip(),
            )
        )
        db.add(
            MoneyRecord(
                record_date=movement_date,
                record_type="Expense",
                category="Stock used" if reason == "Used" else "Damaged stock",
                description=f"{product.name} × {quantity}" + (f" — {note.strip()}" if note.strip() else ""),
                amount=total_cost,
            )
        )
        db.commit()


def current_month_records(records: list[MoneyRecord]) -> list[MoneyRecord]:
    first_day = TODAY.replace(day=1)
    return [r for r in records if first_day <= r.record_date <= TODAY]


def six_month_chart(records: list[MoneyRecord]) -> pd.DataFrame:
    month_starts: list[date] = []
    year, month = TODAY.year, TODAY.month
    for _ in range(6):
        month_starts.append(date(year, month, 1))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    month_starts.reverse()

    rows = []
    for start in month_starts:
        if start.month == 12:
            next_start = date(start.year + 1, 1, 1)
        else:
            next_start = date(start.year, start.month + 1, 1)
        month_records = [r for r in records if start <= r.record_date < next_start]
        rows.append(
            {
                "Month": start.strftime("%b %Y"),
                "Income": sum(r.amount for r in month_records if r.record_type == "Income"),
                "Expenses": sum(r.amount for r in month_records if r.record_type == "Expense"),
            }
        )
    return pd.DataFrame(rows).set_index("Month")


def show_error(error: Exception) -> None:
    if isinstance(error, ValueError):
        st.error(str(error))
    elif isinstance(error, SQLAlchemyError):
        st.error("The data could not be saved. Please try again. If it keeps happening, check your database connection.")
    else:
        st.error(f"Something went wrong: {error}")


# -----------------------------------------------------------------------------
# Sidebar and shared data
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# 📊 Business Tracker")
    st.caption("Money and stock, in one place")
    st.divider()
    page = st.radio(
        "Menu",
        ["Overview", "Sales", "Products & stock", "Income & expenses", "Download reports"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Money is shown in Indonesian Rupiah (Rp).")

try:
    products, movements, records = load_data()
    stock_table = inventory_rows(products, movements)
except SQLAlchemyError:
    st.error("Could not connect to the database. Check your database settings and try again.")
    st.stop()

product_by_id = {p.id: p for p in products}


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------
if page == "Overview":
    page_heading("Overview", "A clear look at your money and the stock you have.")
    month_records = current_month_records(records)
    month_income = sum(r.amount for r in month_records if r.record_type == "Income")
    month_expenses = sum(r.amount for r in month_records if r.record_type == "Expense")
    stock_value = sum(p.current_stock * p.unit_cost for p in products)
    month_difference = month_income - month_expenses

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income this month", money(month_income))
    c2.metric("Expenses this month", money(month_expenses))
    c3.metric("Income minus expenses", money(month_difference))
    c4.metric("Value of stock left", money(stock_value))

    st.write("")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown('<div class="section-heading">Money over the last 6 months</div>', unsafe_allow_html=True)
        chart = six_month_chart(records)
        if chart.empty or float(chart.to_numpy().sum()) == 0:
            st.info("Your income and expenses will appear here after you add records.")
        else:
            st.bar_chart(chart)
    with right:
        st.markdown('<div class="section-heading">Stock that needs attention</div>', unsafe_allow_html=True)
        low_stock = [p for p in products if p.current_stock <= p.low_stock_at]
        if low_stock:
            low_df = pd.DataFrame(
                [{"Product": p.name, "Left": p.current_stock, "Alert at": p.low_stock_at} for p in low_stock]
            )
            st.dataframe(low_df, hide_index=True, use_container_width=True)
        else:
            st.success("All products are above their stock alert levels.")

    st.markdown('<div class="section-heading">Latest money records</div>', unsafe_allow_html=True)
    recent_records = records[:8]
    if recent_records:
        recent_df = money_frame(recent_records)
        recent_df["Amount"] = recent_df["Amount (Rp)"].map(money)
        st.dataframe(recent_df[["Date", "Type", "Group", "Details", "Amount"]], hide_index=True, use_container_width=True)
    else:
        st.info("No money records yet. Add a sale, income, or expense to get started.")

    st.caption("The figures above use records dated in the current month. Stock value is based on the current average cost per item.")


# -----------------------------------------------------------------------------
# Sales
# -----------------------------------------------------------------------------
elif page == "Sales":
    page_heading("Record a sale", "Choose a product and enter how many items you sold.")
    available_products = [p for p in products if p.current_stock > 0]

    if not available_products:
        st.info("There are no products in stock yet. Add a product or add more stock first.")
    else:
        product_options = {f"{p.name} — {p.current_stock} left": p.id for p in available_products}
        selected_label = st.selectbox("Product", list(product_options.keys()))
        selected_product = product_by_id[product_options[selected_label]]

        st.caption(f"Current selling price: **{money(selected_product.selling_price)}** per item · In stock: **{selected_product.current_stock}**")
        with st.form("sale_form"):
            a, b = st.columns(2)
            quantity = a.number_input(
                "Quantity sold", min_value=1, max_value=int(selected_product.current_stock), value=1, step=1
            )
            sale_price = b.number_input(
                "Selling price per item (Rp)", min_value=0, value=int(round(selected_product.selling_price)), step=1000
            )
            sale_date = st.date_input("Sale date", value=TODAY)
            note = st.text_input("Note (optional)", placeholder="Example: Customer name or order number")
            submitted = st.form_submit_button("Save sale", type="primary", use_container_width=True)

        if submitted:
            try:
                record_sale(selected_product.id, int(quantity), float(sale_price), sale_date, note)
                st.success(
                    f"Sale saved. {quantity} item(s) sold for {money(quantity * sale_price)}. "
                    f"Stock cost: {money(quantity * selected_product.unit_cost)}."
                )
                st.rerun()
            except Exception as error:
                show_error(error)

    st.divider()
    st.markdown('<div class="section-heading">Recent sales</div>', unsafe_allow_html=True)
    sales = [m for m in movements if m.kind == "Sale"][:12]
    if sales:
        sales_df = pd.DataFrame(
            [
                {
                    "Date": m.movement_date.isoformat(),
                    "Product": product_by_id[m.product_id].name if m.product_id in product_by_id else "Unknown",
                    "Quantity": m.quantity,
                    "Sales value": money(m.total_revenue),
                    "Stock cost": money(m.total_cost),
                    "Note": m.note,
                }
                for m in sales
            ]
        )
        st.dataframe(sales_df, hide_index=True, use_container_width=True)
    else:
        st.info("Your sales will appear here.")


# -----------------------------------------------------------------------------
# Products and stock
# -----------------------------------------------------------------------------
elif page == "Products & stock":
    page_heading("Products & stock", "See what you have, what you sold, and what your remaining stock is worth.")

    tab_products, tab_add, tab_stock = st.tabs(["Product list", "Add a product", "Update stock"])

    with tab_products:
        if stock_table.empty:
            st.info("No products yet. Add your first product to start tracking stock.")
        else:
            display = stock_table.copy()
            for col in ["Sales value", "Cost of sold items", "Cost of used / damaged", "Value left", "Cost per item", "Selling price"]:
                display[col] = display[col].map(money)
            st.dataframe(display, hide_index=True, use_container_width=True)
            st.caption(
                "Sold = original stock + stock added later − stock left − items used or damaged. "
                "Sales value uses the selling price entered when each sale was saved."
            )

        if products:
            with st.expander("Change a product's selling price"):
                price_options = {p.name: p.id for p in products}
                chosen_name = st.selectbox("Product to update", list(price_options.keys()), key="price_product")
                chosen_product = product_by_id[price_options[chosen_name]]
                with st.form("update_price_form"):
                    new_price = st.number_input(
                        "New selling price per item (Rp)",
                        min_value=0,
                        value=int(round(chosen_product.selling_price)),
                        step=1000,
                    )
                    update_price = st.form_submit_button("Save price", type="primary")
                if update_price:
                    try:
                        with SessionLocal() as db:
                            product = db.get(Product, chosen_product.id)
                            product.selling_price = float(new_price)
                            db.commit()
                        st.success("Selling price updated.")
                        st.rerun()
                    except Exception as error:
                        show_error(error)

    with tab_add:
        st.markdown("Add a product and enter the stock you already have.")
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("Product name", placeholder="Example: Classic T-shirt")
            category = st.text_input("Group (optional)", placeholder="Example: Clothing", value="Other")
            c1, c2 = st.columns(2)
            opening_stock = c1.number_input("Starting stock", min_value=0, value=0, step=1)
            low_stock_at = c2.number_input("Show a warning when stock reaches", min_value=0, value=5, step=1)
            c3, c4 = st.columns(2)
            unit_cost = c3.number_input("Cost per item (Rp)", min_value=0, value=0, step=1000)
            selling_price = c4.number_input("Selling price per item (Rp)", min_value=0, value=0, step=1000)
            add_product_submit = st.form_submit_button("Add product", type="primary", use_container_width=True)

        if add_product_submit:
            clean_name = name.strip()
            if not clean_name:
                st.error("Enter a product name.")
            else:
                try:
                    with SessionLocal() as db:
                        existing = db.scalar(select(Product).where(func.lower(Product.name) == clean_name.lower()))
                        if existing:
                            st.error("A product with that name already exists. Choose a different name.")
                        else:
                            product = Product(
                                name=clean_name,
                                category=category.strip() or "Other",
                                opening_stock=int(opening_stock),
                                current_stock=int(opening_stock),
                                unit_cost=float(unit_cost),
                                selling_price=float(selling_price),
                                low_stock_at=int(low_stock_at),
                            )
                            db.add(product)
                            db.flush()
                            if opening_stock > 0:
                                db.add(
                                    StockMovement(
                                        product_id=product.id,
                                        movement_date=TODAY,
                                        kind="Initial stock",
                                        quantity=int(opening_stock),
                                        unit_cost=float(unit_cost),
                                        total_cost=int(opening_stock) * float(unit_cost),
                                        note="Starting stock",
                                    )
                                )
                            db.commit()
                            st.success(f"{clean_name} added.")
                            st.rerun()
                except Exception as error:
                    show_error(error)

    with tab_stock:
        if not products:
            st.info("Add a product before updating stock.")
        else:
            stock_tab_add, stock_tab_remove = st.tabs(["Add stock", "Remove stock"])
            product_options = {f"{p.name} — {p.current_stock} left": p.id for p in products}

            with stock_tab_add:
                chosen_label = st.selectbox("Product", list(product_options.keys()), key="restock_product")
                chosen_product = product_by_id[product_options[chosen_label]]
                with st.form("restock_form"):
                    c1, c2 = st.columns(2)
                    add_quantity = c1.number_input("Quantity added", min_value=1, value=1, step=1)
                    purchase_cost = c2.number_input("Cost per new item (Rp)", min_value=0, value=int(round(chosen_product.unit_cost)), step=1000)
                    restock_date = st.date_input("Date stock was added", value=TODAY)
                    restock_note = st.text_input("Note (optional)", placeholder="Example: Supplier or invoice number")
                    restock_submit = st.form_submit_button("Save added stock", type="primary", use_container_width=True)
                if restock_submit:
                    try:
                        add_stock(chosen_product.id, int(add_quantity), float(purchase_cost), restock_date, restock_note)
                        st.success(
                            f"Stock updated. Added {add_quantity} item(s). "
                            f"Purchase cost recorded: {money(add_quantity * purchase_cost)}."
                        )
                        st.rerun()
                    except Exception as error:
                        show_error(error)

            with stock_tab_remove:
                products_in_stock = [p for p in products if p.current_stock > 0]
                if not products_in_stock:
                    st.info("There is no stock to remove.")
                else:
                    remove_options = {f"{p.name} — {p.current_stock} left": p.id for p in products_in_stock}
                    remove_label = st.selectbox("Product", list(remove_options.keys()), key="remove_product")
                    remove_product_selected = product_by_id[remove_options[remove_label]]
                    with st.form("remove_stock_form"):
                        c1, c2 = st.columns(2)
                        remove_quantity = c1.number_input(
                            "Quantity removed", min_value=1, max_value=int(remove_product_selected.current_stock), value=1, step=1
                        )
                        reason_label = c2.selectbox("Why was it removed?", ["Used", "Damaged"])
                        remove_date = st.date_input("Date", value=TODAY, key="remove_date")
                        remove_note = st.text_input("Note (optional)", placeholder="Example: Used for an order")
                        remove_submit = st.form_submit_button("Save stock change", type="primary", use_container_width=True)
                    if remove_submit:
                        try:
                            remove_stock(remove_product_selected.id, int(remove_quantity), reason_label, remove_date, remove_note)
                            st.success(
                                f"Stock updated. Cost recorded as an expense: "
                                f"{money(remove_quantity * remove_product_selected.unit_cost)}."
                            )
                            st.rerun()
                        except Exception as error:
                            show_error(error)

    st.divider()
    st.markdown('<div class="section-heading">Stock changes</div>', unsafe_allow_html=True)
    if movements:
        recent_movements = movements[:15]
        recent_move_df = movement_frame(recent_movements, products)
        recent_move_df["Total stock cost (Rp)"] = recent_move_df["Total stock cost (Rp)"].map(money)
        recent_move_df["Sales value (Rp)"] = recent_move_df["Sales value (Rp)"].map(money)
        st.dataframe(recent_move_df, hide_index=True, use_container_width=True)
    else:
        st.info("Stock changes will appear here.")


# -----------------------------------------------------------------------------
# Income and expenses
# -----------------------------------------------------------------------------
elif page == "Income & expenses":
    page_heading("Income & expenses", "Keep track of money coming in and money going out.")

    with st.form("money_record_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        record_type = c1.selectbox("Type", ["Income", "Expense"])
        amount = c2.number_input("Amount (Rp)", min_value=1, value=10000, step=1000)
        c3, c4 = st.columns(2)
        category = c3.text_input("Group", placeholder="Example: Delivery, Rent, Other sales")
        record_date = c4.date_input("Date", value=TODAY)
        description = st.text_input("Details", placeholder="Example: Electricity bill or cash sale")
        money_submit = st.form_submit_button("Save record", type="primary", use_container_width=True)

    if money_submit:
        if not description.strip():
            st.error("Enter a short description.")
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
                st.success(f"{record_type} record saved.")
                st.rerun()
            except Exception as error:
                show_error(error)

    st.divider()
    st.markdown('<div class="section-heading">Money records</div>', unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1])
    start_filter = filter_col1.date_input("From", value=TODAY.replace(day=1), key="money_from")
    end_filter = filter_col2.date_input("To", value=TODAY, key="money_to")
    type_filter = filter_col3.selectbox("Show", ["All", "Income", "Expense"], key="money_type_filter")

    filtered_records = [r for r in records if start_filter <= r.record_date <= end_filter]
    if type_filter != "All":
        filtered_records = [r for r in filtered_records if r.record_type == type_filter]

    if start_filter > end_filter:
        st.warning("The start date must be on or before the end date.")
    elif filtered_records:
        result_df = money_frame(filtered_records)
        result_df["Amount"] = result_df["Amount (Rp)"].map(money)
        st.dataframe(result_df[["Date", "Type", "Group", "Details", "Amount"]], hide_index=True, use_container_width=True)
        income_total = sum(r.amount for r in filtered_records if r.record_type == "Income")
        expense_total = sum(r.amount for r in filtered_records if r.record_type == "Expense")
        c1, c2, c3 = st.columns(3)
        c1.metric("Income in this period", money(income_total))
        c2.metric("Expenses in this period", money(expense_total))
        c3.metric("Difference", money(income_total - expense_total))
    else:
        st.info("No records match these dates and filters.")


# -----------------------------------------------------------------------------
# Downloads
# -----------------------------------------------------------------------------
elif page == "Download reports":
    page_heading("Download reports", "Save copies of your records as CSV files. You can open them in Excel or Google Sheets.")

    inventory_export = inventory_table = stock_table.copy()
    money_export = money_frame(records)
    movements_export = movement_frame(movements, products)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Product and stock list**")
        st.caption("Current stock, sold items, sales value, and remaining stock value.")
        st.download_button(
            "Download stock CSV",
            data=inventory_export.to_csv(index=False).encode("utf-8-sig"),
            file_name="product_stock_report.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.markdown("**Income and expenses**")
        st.caption("All saved money records, including sales and stock purchases.")
        st.download_button(
            "Download money CSV",
            data=money_export.to_csv(index=False).encode("utf-8-sig"),
            file_name="income_expense_report.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col3:
        st.markdown("**Stock changes**")
        st.caption("Every sale, stock purchase, and stock removal.")
        st.download_button(
            "Download stock changes CSV",
            data=movements_export.to_csv(index=False).encode("utf-8-sig"),
            file_name="stock_changes_report.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.divider()
    st.markdown("**What the stock values mean**")
    st.write(
        "• **Sold:** starting stock + stock added later − stock left − items used or damaged.\n"
        "• **Sales value:** the actual selling price saved for each sale.\n"
        "• **Cost of sold items:** what those sold items cost you, based on the average stock cost at the time of sale.\n"
        "• **Value left:** items still in stock × their current average cost."
    )

    st.warning(
        "This starter app does not include user accounts. Restrict access to the app before entering private business records. "
        "Download these CSV reports regularly as backups."
    )
