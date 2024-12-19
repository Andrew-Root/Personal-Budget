import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import requests
import os
import json
from datetime import datetime

# Function to get the AUD-EUR exchange rate
def get_exchange_rate():
    try:
        response = requests.get("https://api.exchangerate-api.com/v4/latest/AUD")
        data = response.json()
        return data["rates"]["EUR"]
    except Exception as e:
        print(f"Error fetching exchange rate: {e}")
        return 0.6  # Fallback value

# Initial exchange rate
aud_to_eur = get_exchange_rate()

# Directory for saving weekly data
DATA_DIR = "financial_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Function to load previous data
def load_previous_data():
    try:
        files = sorted(os.listdir(DATA_DIR))
        if files:
            latest_file = os.path.join(DATA_DIR, files[-1])
            with open(latest_file, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading previous data: {e}")
    return {}

# Function to save weekly data
def save_weekly_data(data):
    try:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(DATA_DIR, f"weekly_data_{date_str}.json")
        with open(file_path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving weekly data: {e}")

# Function to calculate summaries
def calculate_summaries():
    try:
        files = sorted(os.listdir(DATA_DIR))
        monthly_data = {}
        for file in files:
            file_path = os.path.join(DATA_DIR, file)
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    date = datetime.strptime(data["date"], "%Y-%m-%d")
                    month_key = date.strftime("%Y-%m")
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {"income": 0, "expenses": {}, "savings": 0}

                    monthly_data[month_key]["income"] += data["income"]
                    monthly_data[month_key]["savings"] += data["savings"]

                    for expense_type, amount in data.get("expense_details", {}).items():
                        if expense_type not in monthly_data[month_key]["expenses"]:
                            monthly_data[month_key]["expenses"][expense_type] = 0
                        monthly_data[month_key]["expenses"][expense_type] += amount
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping invalid file {file_path}: {e}")

        return {"monthly_data": monthly_data}
    except Exception as e:
        print(f"Error calculating summaries: {e}")
    return {}

# Load previous data
previous_data = load_previous_data()

# Create Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("Financial Management in Australia", style={"textAlign": "center", "fontFamily": "Arial, sans-serif", "color": "#FFD700"}),

    html.Div([
        html.Label("Date (YYYY-MM-DD):", style={"fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
        dcc.Input(id="date-input", type="text", value="0-0-0"),
    ], style={"marginBottom": "10px"}),

    html.Div([
        html.Label("Weekly Income (Salary, Extra):", style={"fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
        dcc.Input(id="income-salary", type="number", placeholder="Salary", value=0),
        dcc.Input(id="income-extra", type="number", placeholder="Extra", value=0),
    ], style={"marginBottom": "10px"}),

    html.Div([
        html.Label("Weekly Expenses (Rent, Food, Transport, Leisure, Extra):", style={"fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
        dcc.Input(id="expense-rent", type="number", placeholder="Rent", value=0),
        dcc.Input(id="expense-food", type="number", placeholder="Food", value=0),
        dcc.Input(id="expense-transport", type="number", placeholder="Transport", value=0),
        dcc.Input(id="expense-leisure", type="number", placeholder="Leisure", value=0),
        dcc.Input(id="expense-extra", type="number", placeholder="Extra", value=0),
    ], style={"marginBottom": "20px"}),

    html.Button("Update", id="update-button", n_clicks=0, style={"marginBottom": "10px", "backgroundColor": "#FFD700", "color": "black", "border": "none", "padding": "10px", "cursor": "pointer"}),
    html.Button("Reset All Data", id="reset-button", n_clicks=0, style={"marginBottom": "10px", "backgroundColor": "red", "color": "white", "border": "none", "padding": "10px", "cursor": "pointer"}),

    dcc.Graph(id="finance-graph"),

    html.Div(id="summary", style={"marginTop": "20px", "fontFamily": "Arial, sans-serif", "color": "#FFD700"}),

    html.H2("Monthly Overview", style={"marginTop": "40px", "fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
    dcc.Graph(id="monthly-graph"),

    html.H2("Annual Overview", style={"marginTop": "40px", "fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
    dcc.Graph(id="annual-graph"),

    html.H2("Summary Table", style={"marginTop": "40px", "fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
    html.Div(id="summary-table", style={"fontFamily": "Arial, sans-serif", "color": "#FFD700"}),
], style={"backgroundColor": "#000000", "padding": "20px"})
# Callback to update graphs, summaries, and handle reset
@app.callback(
    [Output("finance-graph", "figure"),
     Output("monthly-graph", "figure"),
     Output("annual-graph", "figure"),
     Output("summary", "children"),
     Output("summary-table", "children")],
    [Input("update-button", "n_clicks"),
     Input("reset-button", "n_clicks")],
    [dash.dependencies.State("date-input", "value"),
     dash.dependencies.State("income-salary", "value"),
     dash.dependencies.State("income-extra", "value"),
     dash.dependencies.State("expense-rent", "value"),
     dash.dependencies.State("expense-food", "value"),
     dash.dependencies.State("expense-transport", "value"),
     dash.dependencies.State("expense-leisure", "value"),
     dash.dependencies.State("expense-extra", "value")]
)
def update_or_reset_finances(update_clicks, reset_clicks, date_input, salary, extra, rent, food, transport, leisure, extra_expense):
    ctx = dash.callback_context
    if not ctx.triggered:
        return go.Figure(), go.Figure(), go.Figure(), "", None

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if triggered_id == "reset-button" and reset_clicks > 0:
        try:
            reset_all_data()
            return go.Figure(), go.Figure(), go.Figure(), "All data has been reset successfully.", None
        except Exception as e:
            print(f"Error resetting data: {e}")
            return go.Figure(), go.Figure(), go.Figure(), "Error resetting data.", None

    if triggered_id == "update-button" and update_clicks > 0:
        try:
            # Financial calculations
            weekly_income = (salary or 0) + (extra or 0)
            weekly_expenses = {
                "Rent": rent or 0,
                "Food": food or 0,
                "Transport": transport or 0,
                "Leisure": leisure or 0,
                "Extra": extra_expense or 0
            }
            total_weekly_expenses = sum(weekly_expenses.values())
            weekly_savings = weekly_income - total_weekly_expenses

            # Convert to EUR
            weekly_savings_eur = weekly_savings * aud_to_eur

            # Save data
            weekly_data = {
                "date": date_input,
                "income": weekly_income,
                "expenses": total_weekly_expenses,
                "savings": weekly_savings,
                "expense_details": weekly_expenses
            }
            save_weekly_data(weekly_data)

            # Data for weekly pie chart
            weekly_labels = list(weekly_expenses.keys()) + ["Savings"]
            weekly_values = list(weekly_expenses.values()) + [weekly_savings]
            weekly_colors = ["#FFB6C1", "#FFD700", "#87CEEB", "#32CD32", "#FFA07A", "#8A2BE2"]

            weekly_fig = go.Figure(data=[
                go.Pie(labels=weekly_labels, values=weekly_values, hole=0.4, marker=dict(colors=weekly_colors))
            ])

            weekly_fig.update_layout(
                title="Weekly Financial Breakdown",
                template="plotly_dark",
            )

            # Monthly summary
            annual_summary_data = calculate_summaries()
            monthly_data = annual_summary_data.get("monthly_data", {})
            monthly_fig = go.Figure()

            for month, data in monthly_data.items():
                monthly_fig.add_trace(go.Pie(
                    labels=list(data["expenses"].keys()) + ["Savings"],
                    values=list(data["expenses"].values()) + [data["savings"]],
                    hole=0.4,
                    name=f"{month} Overview",
                ))

            monthly_fig.update_layout(
                title="Monthly Financial Breakdown",
                template="plotly_dark",
            )

            # Annual summary
            annual_fig = go.Figure()

            for month, data in monthly_data.items():
                annual_fig.add_trace(go.Pie(
                    labels=list(data["expenses"].keys()) + ["Savings"],
                    values=list(data["expenses"].values()) + [data["savings"]],
                    hole=0.4,
                    name=f"Expenses ({month})",
                ))

            annual_fig.update_layout(
                title="Annual Financial Breakdown",
                template="plotly_dark",
            )

            # Summary table
            summary_table = html.Table([
                html.Thead(html.Tr([html.Th("Type"), html.Th("Amount (AUD)"), html.Th("Amount (EUR)")])),
                html.Tbody([
                    html.Tr([html.Td("Income"), html.Td(weekly_income), html.Td(f"{weekly_income * aud_to_eur:.2f}")], style={"borderBottom": "1px solid #FFD700"}),
                    html.Tr([html.Td("Expenses"), html.Td(total_weekly_expenses), html.Td(f"{total_weekly_expenses * aud_to_eur:.2f}")], style={"borderBottom": "1px solid #FFD700"}),
                    html.Tr([html.Td("Savings"), html.Td(weekly_savings), html.Td(f"{weekly_savings_eur:.2f}")]),
                ])
            ], style={"width": "50%", "margin": "auto", "color": "#FFD700", "borderCollapse": "collapse"})

            # Summary details
            summary_text = ""

            return weekly_fig, monthly_fig, annual_fig, summary_text, summary_table

        except Exception as e:
            print(f"Error updating finances: {e}")
            return go.Figure(), go.Figure(), go.Figure(), "Error calculating finances.", None

    return go.Figure(), go.Figure(), go.Figure(), "", None

if __name__ == "__main__":
    app.layout.children.append(
        html.Div("© 2024 by Andrew_Root", style={"textAlign": "center", "color": "#FFD700", "fontSize": "10px", "marginTop": "20px"})
    )
    app.run_server(debug=True, host="0.0.0.0", port=8050)
