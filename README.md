# Practical 10 — Sales Data Analysis Dashboard

A single Streamlit application for uploading, validating, cleaning, filtering, and visualizing sales data.

## Features

- Upload **CSV**, **Excel (.xlsx)**, and **JSON** files.
- Validate data dimensions, columns, data types, missing values, unique values, and duplicate records.
- Preprocess missing values, duplicate rows, whitespace inconsistencies, and date formats.
- Map your own column names to the sales fields used by the dashboard.
- Three or more interactive filters when matching fields exist, plus a date-range filter when a date column is mapped.
- Five dynamically updating KPIs: Total Sales, Total Profit, Total Orders, Total Quantity Sold, and Profit Margin.
- Four interactive Plotly charts, statistical summaries, and cleaned CSV export.

## Project structure

```text
Practical10-Sales-Dashboard/
├── app.py
├── requirements.txt
├── README.md
└── sample_sales.csv
```

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL printed by Streamlit (usually `http://localhost:8501`).

## Sample data

Use `sample_sales.csv` to try the dashboard immediately. You can also upload your own CSV, XLSX, or JSON records.

## Deploy with Streamlit Community Cloud

1. Sign in to Streamlit Community Cloud using GitHub.
2. Create an app and select this repository and the `main` branch.
3. Set the main file path to `app.py`.
4. Deploy and test the upload, filters, KPIs, charts, and CSV download.

## Notes

- Map the correct business columns if your dataset uses unusual column names.
- Profit Margin is calculated as `Total Profit / Total Sales × 100`.
- Date and category visualizations require corresponding fields in the uploaded data.
- Data is processed in the Streamlit session; the app does not store it in a separate database.
