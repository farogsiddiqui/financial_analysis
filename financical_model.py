import math
import numpy as np
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

months = 24
start_month = datetime(2025, 8, 1)      # start from Aug 2025
base_recurring_revenue = 50_000.0   # baseline recurring revenue per month
client_annual_value = 10_000.0
client_monthly_recognition = client_annual_value / 12.0  # revenue recognized each month per new client for 12 months
cost_to_win = 800.0                 # cash required to win 1 client
starting_cash = 0.0
initial_total_clients = 0           # baseline clients count
cash_floor = -100_000.0             # cash must not fall below this

cols = [(start_month + relativedelta(months=i)).strftime("%b-%Y") for i in range(months)]

revenue = np.zeros(months)
cost_of_sales = np.zeros(months)
operations_cost = np.zeros(months)
planned_s_and_m = np.zeros(months)      # budgeted by rule (accrual)
actual_s_and_m_spent = np.zeros(months) # actual acquisition cash spending (multiple of 800)
net_profit_accrual = np.zeros(months)   # accrual net profit after planned S&M
new_clients = np.zeros(months, dtype=int)
total_clients = np.zeros(months, dtype=int)
cash_in = np.zeros(months)
cash_out = np.zeros(months)
cash_balance = np.zeros(months)

acquired_clients_by_month = np.zeros(months, dtype=int)

current_cash = starting_cash
running_total_clients = initial_total_clients

for i in range(months):
    # 1) Determine revenue for month i
    # baseline recurring revenue (assumed cash + revenue same month)
    rev = base_recurring_revenue
    
    # plus recognition from clients acquired in last 12 months (including current month)
    for j in range(max(0, i-11), i+1):
        rev += acquired_clients_by_month[j] * client_monthly_recognition
    
    revenue[i] = rev

    # 2) Accrual expense calculations
    cos = 0.30 * rev
    ops = 0.50 * (rev - cos)  # equals 0.35 * rev
    planned_s = 0.5 * (rev - cos - ops)  # planned S&M = half of remaining
    net_accrual = rev - cos - ops - planned_s

    cost_of_sales[i] = cos
    operations_cost[i] = ops
    planned_s_and_m[i] = planned_s
    net_profit_accrual[i] = net_accrual

    # 3) Cash receipts this month
    # - baseline recurring cash arriving same month (base_recurring_revenue)
    cash_receipt = base_recurring_revenue

    # - plus lump-sum payments (10,000) from clients acquired 4 months ago
    idx_for_payment = i - 4
    if idx_for_payment >= 0:
        cash_receipt += acquired_clients_by_month[idx_for_payment] * client_annual_value

    cash_in[i] = cash_receipt

    # 4) Cash out before S&M acquisitions
    cash_out_before_sandm = cos + ops

    # 5) Determine maximum possible cash available to spend on acquisitions without breaching cash floor
    # After paying cos & ops (and before S&M), available to spend:
    # max_spend such that: current_cash + cash_in - cash_out_before_sandm - actual_spend >= cash_floor
    max_spend_allowed = (current_cash + cash_receipt - cash_out_before_sandm) - cash_floor
    if max_spend_allowed < 0:
        # No room to spend on acquisitions this month (already below or at floor)
        max_spend_allowed = 0.0

    # We cannot spend more than planned budget nor more than allowed by cash floor.
    spend_cap = min(planned_s, max_spend_allowed)

    # But actual spend must be a multiple of cost_to_win (800)
    affordable_clients = int(math.floor(spend_cap / cost_to_win))
    actual_spend = affordable_clients * cost_to_win

    actual_s_and_m_spent[i] = actual_spend
    new_clients[i] = affordable_clients

    # 6) Update acquired clients (they start contributing monthly revenue from this month)
    acquired_clients_by_month[i] = affordable_clients

    # 7) Compute cash out for this month and update balance
    total_cash_out = cash_out_before_sandm + actual_spend
    cash_out[i] = total_cash_out

    current_cash = current_cash + cash_receipt - total_cash_out
    cash_balance[i] = current_cash

    # 8) Update running total clients
    running_total_clients += affordable_clients
    total_clients[i] = running_total_clients

# Build DataFrame with months as columns
rows = {
    "Monthly Revenue": revenue,
    "Cost of Sales": cost_of_sales,
    "Operations Cost": operations_cost,
    "Planned Sales & Marketing (Budget)": planned_s_and_m,
    "Actual Sales & Marketing (Spent)": actual_s_and_m_spent,
    "Net Profit (Accrual)": net_profit_accrual,
    "New Clients Acquired": new_clients,
    "Total Clients": total_clients,
    "Cash In (Receipts)": cash_in,
    "Cash Out (Payments)": cash_out,
    "Cash Balance": cash_balance
}

df = pd.DataFrame(rows, index=cols).T  # transpose so rows are index, columns are months

# Format numeric values for readability (round money)
money_rows = [
    "Monthly Revenue", "Cost of Sales", "Operations Cost",
    "Planned Sales & Marketing (Budget)", "Actual Sales & Marketing (Spent)",
    "Net Profit (Accrual)", "Cash In (Receipts)", "Cash Out (Payments)", "Cash Balance"
]
df.loc[money_rows] = df.loc[money_rows].astype(float).round(2)
df.loc["New Clients Acquired"] = df.loc["New Clients Acquired"].astype(int)
df.loc["Total Clients"] = df.loc["Total Clients"].astype(int)

# Print
pd.set_option('display.max_columns', None)
print("2-year month-by-month model (columns = months Aug-2025 .. Jul-2027)\n")
print(df)

df.to_csv("Financial_model.csv")
print("\nSaved model to: Financial_model.csv")
