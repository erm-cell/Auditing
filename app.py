import streamlit as st

st.markdown("""
<style>

/* Main background */
.stApp {
    background-color: #0E1117;
    color: #F8FAFC;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #161B22;
}

/* Cards and containers */
[data-testid="stMetric"] {
    background-color: #1E293B;
    padding: 20px;
    border-radius: 12px;
}

/* Text */
h1, h2, h3, p, label, span {
    color: #F8FAFC;
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] {
    background-color: #1E293B;
    color: white;
    border-radius: 8px;
}

/* Buttons */
.stButton button {
    background-color: #6366F1;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    background-color: #1E293B;
}

</style>
""", unsafe_allow_html=True)
import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime
from pathlib import Path
import hashlib
import hmac

# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Business Tracker",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path(__file__).parent / "business.db"

# Set this in Streamlit secrets.
ACCESS_CODE = st.secrets.get("APP_ACCESS_CODE", "")

# =========================================================
# DESIGN
# =========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #f7f8fa;
    }

    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1450px;
    }

    h1, h2, h3 {
        color: #172033;
        font-weight: 650;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricValue"] {
        color: #172033;
    }

    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        min-height: 42px;
    }

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 8px;
    }

    div[data-testid="stForm"] {
        background: white;
        padding: 20px;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
    }

    .subtext {
        color: #687386;
        font-size: 14px;
    }

    hr {
        border-color: #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT NOT NULL,
                amount INTEGER NOT NULL CHECK(amount > 0),
                payment_method TEXT NOT NULL DEFAULT 'Cash',
                notes TEXT DEFAULT ''
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                opening_quantity REAL NOT NULL DEFAULT 0,
                opening_cost REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                movement_date TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                quantity REAL NOT NULL CHECK(quantity > 0),
                unit_cost REAL DEFAULT 0,
                selling_price REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                FOREIGN KEY(product_id) REFERENCES products(id)
                    ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS movement_calculations (
                movement_id INTEGER PRIMARY KEY,
                quantity_after REAL NOT NULL,
                average_cost REAL NOT NULL,
                cost_used REAL NOT NULL,
                sales_value REAL NOT NULL,
                FOREIGN KEY(movement_id) REFERENCES stock_movements(id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()


# =========================================================
# STARTING RECORDS
# =========================================================

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


def seed_starting_data():
    with get_connection() as conn:

        existing = conn.execute(
            "SELECT value FROM settings WHERE key='initial_data_loaded'"
        ).fetchone()

        if existing:
            return

        # Starting cash is a balance, not business revenue.
        conn.execute("""
            INSERT INTO transactions
            (transaction_date, transaction_type, description,
             amount, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "2026-11-08",
            "Starting cash",
            "Cash on hand",
            238000,
            "Cash",
            "Initial cash balance"
        ))

        for transaction_date, amount in STARTING_INCOME:
            parsed_date = datetime.strptime(
                transaction_date, "%d/%m/%Y"
            ).date().isoformat()

            conn.execute("""
                INSERT INTO transactions
                (transaction_date, transaction_type, description,
                 amount, payment_method, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                parsed_date,
                "Income",
                "Existing income",
                amount,
                "Cash",
                ""
            ))

        conn.execute("""
            INSERT INTO settings (key, value)
            VALUES ('initial_data_loaded', 'yes')
        """)

        conn.commit()


# =========================================================
# GENERAL HELPERS
# =========================================================

def rupiah(value):
    return "Rp" + f"{int(round(value)):,}".replace(",", ".")


def display_date(value):
    return datetime.strptime(
        value, "%Y-%m-%d"
    ).strftime("%d/%m/%Y")


def get_transactions():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT * FROM transactions
            ORDER BY transaction_date DESC, id DESC
        """, conn)


def get_products():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT * FROM products
            ORDER BY name
        """, conn)


def get_movements():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT
                m.*,
                p.name AS product_name,
                c.quantity_after,
                c.average_cost,
                c.cost_used,
                c.sales_value
            FROM stock_movements m
            JOIN products p ON p.id = m.product_id
            LEFT JOIN movement_calculations c
                ON c.movement_id = m.id
            ORDER BY m.movement_date DESC, m.id DESC
        """, conn)


# =========================================================
# STOCK CALCULATIONS
# =========================================================

def recalculate_product(product_id):
    """
    Rebuilds stock balances chronologically.

    Uses weighted average cost.
    This also makes deleting a previous movement safe.
    """

    with get_connection() as conn:

        product = conn.execute("""
            SELECT * FROM products WHERE id=?
        """, (product_id,)).fetchone()

        if not product:
            return

        quantity = float(product["opening_quantity"])
        total_value = (
            quantity * float(product["opening_cost"])
        )

        movements = conn.execute("""
            SELECT * FROM stock_movements
            WHERE product_id=?
            ORDER BY movement_date ASC, id ASC
        """, (product_id,)).fetchall()

        for movement in movements:

            movement_type = movement["movement_type"]
            qty = float(movement["quantity"])

            average_cost = (
                total_value / quantity if quantity > 0 else 0
            )

            cost_used = 0
            sales_value = 0

            if movement_type == "Stock added":

                incoming_cost = float(movement["unit_cost"])

                quantity += qty
                total_value += qty * incoming_cost

                average_cost = (
                    total_value / quantity if quantity > 0 else 0
                )

            elif movement_type in ("Sold", "Used / Damaged"):

                if qty > quantity:
                    raise ValueError(
                        f"Insufficient stock for {product['name']}."
                    )

                cost_used = qty * average_cost

                quantity -= qty
                total_value -= cost_used

                if quantity < 0.000001:
                    quantity = 0
                    total_value = 0

                if movement_type == "Sold":
                    sales_value = (
                        qty * float(movement["selling_price"])
                    )

            conn.execute("""
                INSERT OR REPLACE INTO movement_calculations
                (movement_id, quantity_after, average_cost,
                 cost_used, sales_value)
                VALUES (?, ?, ?, ?, ?)
            """, (
                movement["id"],
                quantity,
                average_cost,
                cost_used,
                sales_value
            ))

        conn.commit()


def stock_summary():
    products = get_products()
    movements = get_movements()

    total_quantity = 0
    total_value = 0
    total_used_cost = 0
    total_sales_value = 0

    for _, product in products.iterrows():

        qty = float(product["opening_quantity"])
        value = qty * float(product["opening_cost"])

        product_movements = movements[
            movements["product_id"] == product["id"]
        ].copy()

        product_movements = product_movements.sort_values(
            ["movement_date", "id"]
        )

        for _, movement in product_movements.iterrows():

            movement_qty = float(movement["quantity"])

            if movement["movement_type"] == "Stock added":
                qty += movement_qty
                value += movement_qty * float(movement["unit_cost"])

            else:
                cost = float(movement["cost_used"] or 0)
                qty -= movement_qty
                value -= cost

                total_used_cost += cost

                total_sales_value += float(
                    movement["sales_value"] or 0
                )

        total_quantity += qty
        total_value += value

    return (
        total_quantity,
        total_value,
        total_used_cost,
        total_sales_value
    )


# =========================================================
# LOGIN
# =========================================================

if not ACCESS_CODE:
    st.error(
        "The app access code has not been configured. "
        "Set APP_ACCESS_CODE in Streamlit secrets."
    )
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    st.markdown("# Business Tracker")
    st.write("Enter your access code to continue.")

    with st.form("login_form"):

        entered_code = st.text_input(
            "Access code",
            type="password"
        )

        submitted = st.form_submit_button(
            "Continue",
            use_container_width=True
        )

        if submitted:
            if hmac.compare_digest(
                entered_code.encode("utf-8"),
                ACCESS_CODE.encode("utf-8")
            ):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect access code.")

    st.stop()


# =========================================================
# START DATABASE
# =========================================================

initialize_database()
seed_starting_data()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Business Tracker")

page = st.sidebar.radio(
    "MENU",
    [
        "Dashboard",
        "Income & Expenses",
        "Products & Stock",
        "Stock History",
        "Transaction History",
        "Data Backup"
    ]
)

st.sidebar.divider()

if st.sidebar.button("Log out", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.title("Dashboard")
    st.caption("Overview of your business finances and stock.")

    transactions = get_transactions()

    income = transactions[
        transactions["transaction_type"] == "Income"
    ]["amount"].sum()

    expenses = transactions[
        transactions["transaction_type"] == "Expense"
    ]["amount"].sum()

    starting_cash = transactions[
        transactions["transaction_type"] == "Starting cash"
    ]["amount"].sum()

    cash_balance = starting_cash + income - expenses

    qty, stock_value, used_cost, sales_value = stock_summary()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Income", rupiah(income))
    col2.metric("Total Expenses", rupiah(expenses))
    col3.metric("Cash Balance", rupiah(cash_balance))

    col4, col5, col6 = st.columns(3)

    col4.metric("Stock Value", rupiah(stock_value))
    col5.metric("Stock Cost Used", rupiah(used_cost))
    col6.metric("Recorded Stock Sales", rupiah(sales_value))

    st.divider()

    st.subheader("Financial Summary")

    st.write(
        "Cash balance = Starting cash + Income - Expenses"
    )

    st.write(
        f"**{rupiah(starting_cash)} + "
        f"{rupiah(income)} - {rupiah(expenses)} "
        f"= {rupiah(cash_balance)}**"
    )

    st.divider()

    st.subheader("Recent Transactions")

    if not transactions.empty:

        recent = transactions.head(10).copy()

        recent["Date"] = recent["transaction_date"].apply(
            display_date
        )

        recent["Amount"] = recent["amount"].apply(rupiah)

        recent = recent.rename(columns={
            "transaction_type": "Type",
            "description": "Description",
            "payment_method": "Payment"
        })

        st.dataframe(
            recent[
                ["Date", "Type", "Description", "Amount", "Payment"]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("No transactions recorded yet.")


# =========================================================
# INCOME AND EXPENSES
# =========================================================

elif page == "Income & Expenses":

    st.title("Income & Expenses")
    st.caption("Record money received and money spent.")

    tab1, tab2 = st.tabs([
        "Add Transaction",
        "Edit Transaction"
    ])

    with tab1:

        with st.form("add_transaction"):

            transaction_type = st.selectbox(
                "Transaction type",
                ["Income", "Expense"]
            )

            description = st.text_input(
                "Description",
                placeholder="Example: Product sales, electricity"
            )

            amount = st.number_input(
                "Amount (Rp)",
                min_value=1,
                step=1000
            )

            transaction_date = st.date_input(
                "Date",
                value=date.today(),
                format="DD/MM/YYYY"
            )

            payment = st.selectbox(
                "Payment method",
                ["Cash", "Bank transfer", "E-wallet", "Other"]
            )

            notes = st.text_input("Notes (optional)")

            submit = st.form_submit_button(
                "Save Transaction",
                use_container_width=True
            )

            if submit:

                if not description.strip():
                    st.error("Please enter a description.")

                else:

                    with get_connection() as conn:

                        conn.execute("""
                            INSERT INTO transactions
                            (transaction_date, transaction_type,
                             description, amount, payment_method, notes)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            transaction_date.isoformat(),
                            transaction_type,
                            description.strip(),
                            int(amount),
                            payment,
                            notes.strip()
                        ))

                        conn.commit()

                    st.success("Transaction saved.")
                    st.rerun()

    with tab2:

        transactions = get_transactions()

        if transactions.empty:
            st.info("There are no transactions to edit.")

        else:

            options = {
                f"#{row['id']} | {display_date(row['transaction_date'])} "
                f"| {row['transaction_type']} "
                f"| {row['description']} "
                f"| {rupiah(row['amount'])}": row["id"]
                for _, row in transactions.iterrows()
            }

            selected_label = st.selectbox(
                "Choose a transaction",
                list(options.keys())
            )

            selected_id = options[selected_label]

            selected = transactions[
                transactions["id"] == selected_id
            ].iloc[0]

            with st.form("edit_transaction"):

                new_type = st.selectbox(
                    "Transaction type",
                    ["Income", "Expense", "Starting cash"],
                    index=[
                        "Income", "Expense", "Starting cash"
                    ].index(selected["transaction_type"])
                )

                new_description = st.text_input(
                    "Description",
                    value=selected["description"]
                )

                new_amount = st.number_input(
                    "Amount (Rp)",
                    min_value=1,
                    value=int(selected["amount"]),
                    step=1000
                )

                new_date = st.date_input(
                    "Date",
                    value=datetime.strptime(
                        selected["transaction_date"],
                        "%Y-%m-%d"
                    ).date(),
                    format="DD/MM/YYYY"
                )

                new_payment = st.selectbox(
                    "Payment method",
                    ["Cash", "Bank transfer", "E-wallet", "Other"],
                    index=[
                        "Cash", "Bank transfer", "E-wallet", "Other"
                    ].index(selected["payment_method"])
                )

                new_notes = st.text_input(
                    "Notes",
                    value=selected["notes"] or ""
                )

                save_changes = st.form_submit_button(
                    "Save Changes",
                    use_container_width=True
                )

                if save_changes:

                    if not new_description.strip():
                        st.error("Please enter a description.")

                    else:

                        with get_connection() as conn:

                            conn.execute("""
                                UPDATE transactions
                                SET transaction_date=?,
                                    transaction_type=?,
                                    description=?,
                                    amount=?,
                                    payment_method=?,
                                    notes=?
                                WHERE id=?
                            """, (
                                new_date.isoformat(),
                                new_type,
                                new_description.strip(),
                                int(new_amount),
                                new_payment,
                                new_notes.strip(),
                                selected_id
                            ))

                            conn.commit()

                        st.success("Transaction updated.")
                        st.rerun()

            if st.button(
                "Delete this transaction",
                type="secondary"
            ):

                st.session_state.confirm_delete_transaction = selected_id

            if st.session_state.get(
                "confirm_delete_transaction"
            ) == selected_id:

                st.warning(
                    "Are you sure you want to permanently delete this transaction?"
                )

                yes, no = st.columns(2)

                if yes.button("Confirm Delete", type="primary"):
                    with get_connection() as conn:
                        conn.execute(
                            "DELETE FROM transactions WHERE id=?",
                            (selected_id,)
                        )
                        conn.commit()

                    del st.session_state[
                        "confirm_delete_transaction"
                    ]
                    st.rerun()

                if no.button("Cancel"):
                    del st.session_state[
                        "confirm_delete_transaction"
                    ]
                    st.rerun()


# =========================================================
# PRODUCTS AND STOCK
# =========================================================

elif page == "Products & Stock":

    st.title("Products & Stock")

    st.caption(
        "Track the products you own, how much stock remains, "
        "and how much stock has been used or sold."
    )

    tab1, tab2, tab3 = st.tabs([
        "Stock Overview",
        "Add Product",
        "Update Stock"
    ])

    products = get_products()
    movements = get_movements()

    with tab1:

        if products.empty:
            st.info("Add your first product to start tracking stock.")

        else:

            overview = []

            for _, product in products.iterrows():

                qty = float(product["opening_quantity"])
                value = qty * float(product["opening_cost"])

                product_movements = movements[
                    movements["product_id"] == product["id"]
                ].sort_values(["movement_date", "id"])

                used = 0
                sold_qty = 0
                sold_value = 0

                for _, movement in product_movements.iterrows():

                    mqty = float(movement["quantity"])

                    if movement["movement_type"] == "Stock added":
                        qty += mqty
                        value += mqty * float(movement["unit_cost"])

                    else:
                        qty -= mqty
                        value -= float(movement["cost_used"] or 0)
                        used += mqty

                        if movement["movement_type"] == "Sold":
                            sold_qty += mqty
                            sold_value += float(
                                movement["sales_value"] or 0
                            )

                average_cost = value / qty if qty > 0 else 0

                overview.append({
                    "Product": product["name"],
                    "Original Stock": product["opening_quantity"],
                    "Stock Used / Sold": used,
                    "Remaining Stock": round(qty, 3),
                    "Average Cost": rupiah(average_cost),
                    "Remaining Stock Value": rupiah(value),
                    "Sales Value": rupiah(sold_value)
                })

            st.dataframe(
                pd.DataFrame(overview),
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            st.subheader("Product Details")

            product_options = {
                f"{row['name']} (ID {row['id']})": row["id"]
                for _, row in products.iterrows()
            }

            chosen = st.selectbox(
                "Choose product",
                list(product_options.keys()),
                key="product_details"
            )

            product_id = product_options[chosen]

            product = products[
                products["id"] == product_id
            ].iloc[0]

            if st.button("Delete Product", type="secondary"):

                st.session_state.confirm_delete_product = product_id

            if st.session_state.get(
                "confirm_delete_product"
            ) == product_id:

                st.warning(
                    "Deleting this product will also delete all its stock history."
                )

                yes, no = st.columns(2)

                if yes.button("Confirm Product Deletion"):
                    with get_connection() as conn:
                        conn.execute(
                            "DELETE FROM products WHERE id=?",
                            (product_id,)
                        )
                        conn.commit()

                    del st.session_state["confirm_delete_product"]
                    st.rerun()

                if no.button("Cancel"):
                    del st.session_state["confirm_delete_product"]
                    st.rerun()

    with tab2:

        with st.form("add_product"):

            product_name = st.text_input(
                "Product name",
                placeholder="Example: Coffee"
            )

            opening_quantity = st.number_input(
                "Original stock quantity",
                min_value=0.0,
                step=1.0
            )

            opening_cost = st.number_input(
                "Cost per unit (Rp)",
                min_value=0.0,
                step=1000.0
            )

            add_product = st.form_submit_button(
                "Add Product",
                use_container_width=True
            )

            if add_product:

                if not product_name.strip():
                    st.error("Please enter a product name.")

                else:

                    with get_connection() as conn:

                        existing = conn.execute("""
                            SELECT id FROM products
                            WHERE LOWER(name)=LOWER(?)
                        """, (product_name.strip(),)).fetchone()

                        if existing:
                            st.error(
                                "This product already exists. "
                                "Update its stock instead."
                            )

                        else:

                            conn.execute("""
                                INSERT INTO products
                                (name, opening_quantity, opening_cost, created_at)
                                VALUES (?, ?, ?, ?)
                            """, (
                                product_name.strip(),
                                opening_quantity,
                                opening_cost,
                                datetime.now().isoformat()
                            ))

                            conn.commit()

                            st.success("Product added.")
                            st.rerun()

    with tab3:

        if products.empty:
            st.info("Add a product before updating stock.")

        else:

            product_options = {
                row["name"]: row["id"]
                for _, row in products.iterrows()
            }

            with st.form("stock_movement"):

                selected_product = st.selectbox(
                    "Product",
                    list(product_options.keys())
                )

                movement_type = st.selectbox(
                    "What happened to the stock?",
                    [
                        "Stock added",
                        "Sold",
                        "Used / Damaged"
                    ]
                )

                movement_quantity = st.number_input(
                    "Quantity",
                    min_value=0.001,
                    step=1.0
                )

                if movement_type == "Stock added":

                    unit_cost = st.number_input(
                        "Purchase cost per unit (Rp)",
                        min_value=0.0,
                        step=1000.0
                    )

                    selling_price = 0.0

                elif movement_type == "Sold":

                    unit_cost = 0.0

                    selling_price = st.number_input(
                        "Selling price per unit (Rp)",
                        min_value=0.0,
                        step=1000.0
                    )

                else:

                    unit_cost = 0.0
                    selling_price = 0.0

                movement_date = st.date_input(
                    "Date",
                    value=date.today(),
                    format="DD/MM/YYYY"
                )

                movement_notes = st.text_input(
                    "Notes (optional)"
                )

                save_movement = st.form_submit_button(
                    "Save Stock Update",
                    use_container_width=True
                )

                if save_movement:

                    product_id = product_options[selected_product]

                    with get_connection() as conn:

                        conn.execute("""
                            INSERT INTO stock_movements
                            (product_id, movement_date, movement_type,
                             quantity, unit_cost, selling_price, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            product_id,
                            movement_date.isoformat(),
                            movement_type,
                            movement_quantity,
                            unit_cost,
                            selling_price,
                            movement_notes.strip()
                        ))

                        movement_id = conn.execute(
                            "SELECT last_insert_rowid()"
                        ).fetchone()[0]

                        conn.commit()

                    try:

                        recalculate_product(product_id)

                        st.success("Stock updated successfully.")
                        st.rerun()

                    except ValueError as error:

                        with get_connection() as conn:
                            conn.execute(
                                "DELETE FROM stock_movements WHERE id=?",
                                (movement_id,)
                            )
                            conn.commit()

                        recalculate_product(product_id)
                        st.error(str(error))


# =========================================================
# STOCK HISTORY
# =========================================================

elif page == "Stock History":

    st.title("Stock History")
    st.caption("Review every stock increase, sale and usage.")

    movements = get_movements()

    if movements.empty:

        st.info("No stock movements recorded.")

    else:

        display = movements.copy()

        display["Date"] = display["movement_date"].apply(
            display_date
        )

        display["Cost Used"] = display["cost_used"].apply(
            lambda x: rupiah(x or 0)
        )

        display["Sales Value"] = display["sales_value"].apply(
            lambda x: rupiah(x or 0)
        )

        display["Purchase Cost"] = display.apply(
            lambda row: (
                rupiah(row["quantity"] * row["unit_cost"])
                if row["movement_type"] == "Stock added"
                else "-"
            ),
            axis=1
        )

        display = display.rename(columns={
            "product_name": "Product",
            "movement_type": "Movement",
            "quantity": "Quantity",
            "notes": "Notes"
        })

        st.dataframe(
            display[
                [
                    "Date", "Product", "Movement",
                    "Quantity", "Purchase Cost",
                    "Cost Used", "Sales Value", "Notes"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.subheader("Correct a Stock Update")

        movement_options = {
            f"#{row['id']} | {row['product_name']} | "
            f"{display_date(row['movement_date'])} | "
            f"{row['movement_type']} | {row['quantity']}": (
                row["id"], row["product_id"]
            )
            for _, row in movements.iterrows()
        }

        selected_movement = st.selectbox(
            "Choose the incorrect stock update",
            list(movement_options.keys())
        )

        movement_id, product_id = movement_options[
            selected_movement
        ]

        if st.button("Delete Stock Update", type="secondary"):

            st.session_state.confirm_delete_movement = (
                movement_id, product_id
            )

        if st.session_state.get(
            "confirm_delete_movement"
        ) == (movement_id, product_id):

            st.warning(
                "This will remove the stock update and recalculate "
                "the product's stock history."
            )

            yes, no = st.columns(2)

            if yes.button("Confirm Deletion"):

                with get_connection() as conn:
                    conn.execute(
                        "DELETE FROM stock_movements WHERE id=?",
                        (movement_id,)
                    )
                    conn.commit()

                recalculate_product(product_id)

                del st.session_state["confirm_delete_movement"]
                st.rerun()

            if no.button("Cancel"):
                del st.session_state["confirm_delete_movement"]
                st.rerun()


# =========================================================
# DATA BACKUP
# =========================================================

elif page == "Data Backup":

    st.title("Data Backup")

    st.caption(
        "Save a copy of your business records or restore them later."
    )

    transactions = get_transactions()
    products = get_products()
    movements = get_movements()

    st.subheader("Download your records")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.download_button(
            "Download Transactions",
            transactions.to_csv(index=False).encode("utf-8-sig"),
            file_name="transactions.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col2:

        st.download_button(
            "Download Products",
            products.to_csv(index=False).encode("utf-8-sig"),
            file_name="products.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col3:

        st.download_button(
            "Download Stock History",
            movements.to_csv(index=False).encode("utf-8-sig"),
            file_name="stock_history.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.divider()

    st.subheader("Database information")

    st.write(
        "Your records are stored in a SQLite database named "
        "`business.db`."
    )

    st.info(
        "Download your records regularly. If you host this app "
        "on a service with temporary storage, use a persistent "
        "database or keep backups outside the app."
    )

st.sidebar.caption("Business Tracker")
