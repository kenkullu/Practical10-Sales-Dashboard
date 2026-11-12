import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Sales Data Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Helpers ---------------------------------
ALIASES = {
    "sales": ["sales", "total sales", "revenue", "amount", "sales amount"],
    "profit": ["profit", "net profit", "earnings"],
    "order_id": ["order id", "order_id", "orderid", "invoice", "invoice id"],
    "quantity": ["quantity", "qty", "units", "units sold"],
    "date": ["order date", "date", "transaction date", "sales date"],
    "category": ["category", "product category", "type"],
    "region": ["region", "area", "territory", "state", "city"],
}


def clean_column_name(name):
    """Return a consistent, readable column label."""
    return str(name).strip().replace("\n", " ")


def read_uploaded_file(uploaded_file):
    """Read CSV, Excel, or JSON input and return a DataFrame."""
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(uploaded_file)
    if suffix == ".xlsx":
        return pd.read_excel(uploaded_file, engine="openpyxl")
    if suffix == ".json":
        raw = json.load(uploaded_file)
        if isinstance(raw, list):
            return pd.json_normalize(raw)
        if isinstance(raw, dict):
            # Support common JSON record containers.
            for key in ("data", "records", "rows", "items"):
                if key in raw and isinstance(raw[key], list):
                    return pd.json_normalize(raw[key])
            return pd.json_normalize(raw)
        raise ValueError("JSON must contain an object or a list of records.")
    raise ValueError("Unsupported file type. Upload CSV, XLSX, or JSON.")


def find_column(columns, role):
    """Guess a column for a business role using common aliases."""
    normalized = {str(c).strip().lower(): c for c in columns}
    for alias in ALIASES[role]:
        if alias in normalized:
            return normalized[alias]
    for key, original in normalized.items():
        if any(alias in key for alias in ALIASES[role]):
            return original
    return "(Not available)"


def numeric_series(frame, column):
    if column == "(Not available)" or column not in frame.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def safe_sum(series):
    return float(series.fillna(0).sum()) if not series.empty else 0.0


def calculate_kpis(frame, mapping):
    sales = numeric_series(frame, mapping["sales"])
    profit = numeric_series(frame, mapping["profit"])
    quantity = numeric_series(frame, mapping["quantity"])
    order_col = mapping["order_id"]

    total_sales = safe_sum(sales)
    total_profit = safe_sum(profit)
    total_orders = (
        frame[order_col].nunique(dropna=True)
        if order_col != "(Not available)" and order_col in frame.columns
        else 0
    )
    total_quantity = safe_sum(quantity)
    margin = (total_profit / total_sales * 100) if total_sales else 0.0
    return total_sales, total_profit, total_orders, total_quantity, margin


def statistical_summary(frame):
    """Reusable descriptive-statistics function for numeric columns."""
    numeric = frame.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame()
    return numeric.describe().T.round(2)


def preprocess_data(
    source,
    date_col=None,
    dayfirst=False,
    missing_strategy="Fill numeric with median and text with mode",
    normalize_text=True,
    remove_duplicates=True,
):
    """Clean labels, values, dates, duplicates, and missing data."""
    df = source.copy()
    df.columns = [clean_column_name(c) for c in df.columns]

    # Convert whitespace-only cells to missing values.
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # Normalize text values to reduce inconsistent labels.
    if normalize_text:
        for col in df.select_dtypes(include=["object", "string"]).columns:
            df[col] = df[col].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )

    # Parse the selected date field safely.
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(
            df[date_col], errors="coerce", dayfirst=dayfirst
        )

    duplicates_removed = int(df.duplicated().sum()) if remove_duplicates else 0
    if remove_duplicates:
        df = df.drop_duplicates()

    if missing_strategy == "Drop rows with missing values":
        df = df.dropna()
    elif missing_strategy == "Fill numeric with median and text with mode":
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                median = df[col].median()
                if pd.notna(median):
                    df[col] = df[col].fillna(median)
            else:
                mode = df[col].mode(dropna=True)
                if not mode.empty:
                    df[col] = df[col].fillna(mode.iloc[0])
    # "Keep missing values" intentionally leaves nulls unchanged.

    return df, duplicates_removed


def money(value):
    return f"₹{value:,.2f}"


def get_filter_columns(frame, mapping):
    preferred = []
    for role in ("region", "category"):
        col = mapping.get(role)
        if col and col != "(Not available)" and col in frame.columns and col not in preferred:
            preferred.append(col)
    for col in frame.columns:
        if (
            col not in preferred
            and (pd.api.types.is_object_dtype(frame[col]) or
                 isinstance(frame[col].dtype, pd.CategoricalDtype))
            and frame[col].nunique(dropna=True) <= 100
        ):
            preferred.append(col)
    return preferred


# ----------------------------- Interface --------------------------------
st.title("📊 Sales Data Analysis Dashboard")
st.caption("Upload sales data, clean it, explore performance, and export the processed dataset.")

with st.sidebar:
    st.header("1. Upload data")
    uploaded = st.file_uploader(
        "Choose a sales data file",
        type=["csv", "xlsx", "json"],
        help="Supported formats: CSV, Excel (.xlsx), and JSON.",
    )
    st.divider()
    st.header("2. Preprocessing options")
    missing_strategy = st.selectbox(
        "Missing-value treatment",
        [
            "Fill numeric with median and text with mode",
            "Keep missing values",
            "Drop rows with missing values",
        ],
    )
    remove_duplicates = st.checkbox("Remove duplicate records", value=True)
    normalize_text = st.checkbox("Trim extra spaces in text values", value=True)
    dayfirst = st.checkbox("Interpret dates as DD/MM/YYYY", value=False)

if uploaded is None:
    st.info("Upload a CSV, XLSX, or JSON file from the sidebar to begin.")
    st.subheader("What this dashboard includes")
    st.markdown(
        "- File validation and data-quality inspection\n"
        "- Missing-value, duplicate, text, and date preprocessing\n"
        "- Five live KPIs and interactive filters\n"
        "- Interactive Plotly charts and downloadable cleaned data"
    )
    st.stop()

try:
    raw_df = read_uploaded_file(uploaded)
    if raw_df.empty:
        st.error("The uploaded file contains no rows.")
        st.stop()
    if len(raw_df.columns) == 0:
        st.error("No columns were found in the uploaded file.")
        st.stop()
    raw_df.columns = [clean_column_name(c) for c in raw_df.columns]
except Exception as exc:
    st.error(f"Could not read this file: {exc}")
    st.stop()

st.success(f"Loaded **{uploaded.name}** successfully.")
st.subheader("Data validation — before preprocessing")
a, b, c, d = st.columns(4)
a.metric("Rows", f"{raw_df.shape[0]:,}")
b.metric("Columns", f"{raw_df.shape[1]:,}")
c.metric("Missing cells", f"{int(raw_df.isna().sum().sum()):,}")
d.metric("Duplicate rows", f"{int(raw_df.duplicated().sum()):,}")

with st.expander("Preview uploaded data", expanded=True):
    st.dataframe(raw_df.head(20), use_container_width=True)

quality = pd.DataFrame({
    "Column": raw_df.columns,
    "Data type": [str(dtype) for dtype in raw_df.dtypes],
    "Missing values": [int(raw_df[col].isna().sum()) for col in raw_df.columns],
    "Missing (%)": [
        round(raw_df[col].isna().mean() * 100, 2) for col in raw_df.columns
    ],
    "Unique values": [int(raw_df[col].nunique(dropna=True)) for col in raw_df.columns],
})
st.markdown("**Column-level validation**")
st.dataframe(quality, use_container_width=True, hide_index=True)

# Detect the likely date column before preprocessing.
guessed_date = find_column(raw_df.columns, "date")
date_options = ["(Not available)"] + list(raw_df.columns)
default_date_index = date_options.index(guessed_date) if guessed_date in date_options else 0
date_choice = st.selectbox(
    "Date column to parse",
    date_options,
    index=default_date_index,
    help="Choose the date field so date filters and time-series charts can work.",
)

clean_df, duplicates_removed = preprocess_data(
    raw_df,
    date_col=None if date_choice == "(Not available)" else date_choice,
    dayfirst=dayfirst,
    missing_strategy=missing_strategy,
    normalize_text=normalize_text,
    remove_duplicates=remove_duplicates,
)

st.subheader("Preprocessing results")
p1, p2, p3 = st.columns(3)
p1.metric("Rows after cleaning", f"{len(clean_df):,}")
p2.metric("Duplicate rows removed", f"{duplicates_removed:,}")
p3.metric("Missing cells remaining", f"{int(clean_df.isna().sum().sum()):,}")

with st.expander("Cleaned data preview"):
    st.dataframe(clean_df.head(20), use_container_width=True)

st.download_button(
    "⬇️ Download cleaned data (CSV)",
    data=clean_df.to_csv(index=False).encode("utf-8"),
    file_name="cleaned_sales_data.csv",
    mime="text/csv",
)

st.subheader("3. Map your sales columns")
st.caption("The dashboard guesses common column names. Change any mapping if your file uses different names.")
columns = ["(Not available)"] + list(clean_df.columns)
roles = [
    ("sales", "Sales / Revenue"),
    ("profit", "Profit"),
    ("order_id", "Order ID"),
    ("quantity", "Quantity"),
    ("date", "Date"),
    ("category", "Category"),
    ("region", "Region / Area"),
]
mapping = {}
map_cols = st.columns(3)
for index, (role, label) in enumerate(roles):
    guess = find_column(clean_df.columns, role)
    options = columns
    default_index = options.index(guess) if guess in options else 0
    with map_cols[index % 3]:
        mapping[role] = st.selectbox(
            label,
            options,
            index=default_index,
            key=f"mapping_{role}",
        )

required_missing = [
    label for role, label in roles[:4]
    if mapping[role] == "(Not available)"
]
if required_missing:
    st.warning(
        "Map these required fields to calculate all five KPIs: "
        + ", ".join(required_missing)
        + ". You can still inspect the data and use available charts."
    )

# ----------------------------- Filters ----------------------------------
st.subheader("4. Interactive filters")
filtered = clean_df.copy()
filter_cols = get_filter_columns(clean_df, mapping)

filter_area = st.columns(3)
for index, col in enumerate(filter_cols[:3]):
    values = sorted(clean_df[col].dropna().astype(str).unique().tolist())
    if not values:
        continue
    with filter_area[index]:
        selected = st.multiselect(
            f"Filter {col}",
            options=values,
            default=[],
            key=f"filter_{col}",
            help="Leave empty to include every value.",
        )
    if selected:
        filtered = filtered[filtered[col].astype(str).isin(selected)]

date_col = mapping["date"]
if date_col != "(Not available)" and date_col in filtered.columns:
    parsed_dates = pd.to_datetime(filtered[date_col], errors="coerce").dropna()
    if not parsed_dates.empty:
        min_date = parsed_dates.min().date()
        max_date = parsed_dates.max().date()
        date_range = st.date_input(
            "Filter date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            date_values = pd.to_datetime(filtered[date_col], errors="coerce")
            filtered = filtered[
                date_values.dt.date.between(start_date, end_date)
            ]

st.caption(f"Showing **{len(filtered):,}** of **{len(clean_df):,}** cleaned rows.")

# ----------------------------- KPIs -------------------------------------
st.subheader("5. Sales performance KPIs")
total_sales, total_profit, total_orders, total_quantity, margin = calculate_kpis(
    filtered, mapping
)
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sales", money(total_sales))
k2.metric("Total Profit", money(total_profit))
k3.metric("Total Orders", f"{total_orders:,}")
k4.metric("Total Quantity Sold", f"{total_quantity:,.0f}")
k5.metric("Profit Margin", f"{margin:.2f}%")

# ----------------------------- Charts -----------------------------------
st.subheader("6. Interactive visualizations")
chart1, chart2 = st.columns(2)

category_col = mapping["category"]
if category_col == "(Not available)" or category_col not in filtered.columns:
    category_col = next(
        (col for col in filter_cols if col in filtered.columns), None
    )

sales_values = numeric_series(filtered, mapping["sales"])
profit_values = numeric_series(filtered, mapping["profit"])

with chart1:
    if category_col and mapping["sales"] != "(Not available)":
        plot_df = filtered[[category_col]].copy()
        plot_df["__sales"] = sales_values
        grouped = plot_df.groupby(category_col, dropna=False)["__sales"].sum().reset_index()
        grouped = grouped.sort_values("__sales", ascending=False)
        fig = px.bar(
            grouped,
            x=category_col,
            y="__sales",
            color=category_col,
            title=f"Sales by {category_col}",
            labels={"__sales": "Sales"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Map a Sales field and a Category/Region field to show sales by category.")

with chart2:
    if date_col != "(Not available)" and date_col in filtered.columns and mapping["sales"] != "(Not available)":
        trend = filtered[[date_col]].copy()
        trend["__sales"] = sales_values
        trend[date_col] = pd.to_datetime(trend[date_col], errors="coerce")
        trend = trend.dropna(subset=[date_col]).groupby(date_col)["__sales"].sum().reset_index()
        trend = trend.sort_values(date_col)
        if not trend.empty:
            fig = px.line(
                trend, x=date_col, y="__sales", markers=True,
                title="Sales over time", labels={"__sales": "Sales"}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid dates are available for the time-series chart.")
    else:
        st.info("Map a Date and Sales field to show sales over time.")

chart3, chart4 = st.columns(2)
with chart3:
    if category_col and mapping["profit"] != "(Not available)":
        plot_df = filtered[[category_col]].copy()
        plot_df["__profit"] = profit_values
        grouped = plot_df.groupby(category_col, dropna=False)["__profit"].sum().reset_index()
        fig = px.pie(
            grouped, names=category_col, values="__profit",
            title=f"Profit contribution by {category_col}", hole=0.35
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Map Profit and Category to show profit contribution.")

with chart4:
    if mapping["sales"] != "(Not available)" and mapping["profit"] != "(Not available)":
        scatter = pd.DataFrame({"Sales": sales_values, "Profit": profit_values}).dropna()
        if not scatter.empty:
            fig = px.scatter(
                scatter, x="Sales", y="Profit",
                title="Sales vs Profit", opacity=0.7,
                hover_data=None,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric Sales and Profit values are available.")
    else:
        st.info("Map Sales and Profit to show the relationship chart.")

# ----------------------------- Statistics -------------------------------
st.subheader("7. Statistical summary")
summary = statistical_summary(filtered)
if summary.empty:
    st.info("No numeric columns are available for statistical summaries.")
else:
    st.dataframe(summary, use_container_width=True)

with st.expander("Data-quality report after preprocessing"):
    remaining = pd.DataFrame({
        "Column": clean_df.columns,
        "Data type": [str(dtype) for dtype in clean_df.dtypes],
        "Missing values": [int(clean_df[col].isna().sum()) for col in clean_df.columns],
        "Duplicate rows": [int(clean_df.duplicated().sum())] * len(clean_df.columns),
    })
    st.dataframe(remaining, use_container_width=True, hide_index=True)

st.caption("Built with Streamlit, Pandas, and Plotly.")