import json
import streamlit as st
import pandas as pd
import os
import pickle

# Set up the title and description
st.title(":money_with_wings: Finance Management")
st.write("The purpose of this app is to analyze finances and make informed budget decisions. In case of emergency, click the sidebar.")
with st.sidebar.expander(':exclamation: Emergency Images'):
    tab1, tab2, tab3 = st.tabs(["Cat", "Dog", "Owl"])

    with tab1:
        st.header("A cat")
        st.image("https://static.streamlit.io/examples/cat.jpg", width=200)
    with tab2:
        st.header("A dog")
        st.image("https://static.streamlit.io/examples/dog.jpg", width=200)
    with tab3:
        st.header("An owl")
        st.image("https://static.streamlit.io/examples/owl.jpg", width=200)

data_file_path = "uploaded_files.pkl"

# Load existing data if available
if os.path.exists(data_file_path):
    with open(data_file_path, "rb") as f:
        st.session_state['data_files'] = pickle.load(f)
else:
    st.session_state['data_files'] = []

# Function to upload CSV files
def upload_csv():
    uploaded_files = st.file_uploader("Upload CSV files", type=[
                                      "csv"], accept_multiple_files=True)

    if uploaded_files is not None:
        for file in uploaded_files:
            # Check if the file already exists in session state
            if any(f['file_name'] == file.name for f in st.session_state['data_files']):
                st.write(f"File {file.name} is already uploaded.")
                continue  # Skip uploading this file

            # Read the CSV file and process it
            df = pd.read_csv(file)

            # Append the new data to session state along with the file name
            st.session_state['data_files'].append(
                {"file_name": file.name, "data": df})

            # Save the updated session state to a file for persistence
            with open(data_file_path, "wb") as f:
                pickle.dump(st.session_state['data_files'], f)

            # Display a message about successful upload
            st.write(f"File {file.name} uploaded successfully.")


# Call the upload function
upload_csv()

# Combine all uploaded dataframes if they exist
if 'data_files' in st.session_state and st.session_state['data_files']:
    # Combine all DataFrames
    union_df = pd.concat([file_info['data'] for file_info in st.session_state['data_files']]).sort_values(
        by='Date', ascending=True).reset_index(drop=True)

    # Transformations
    union_df['Date'] = pd.to_datetime(union_df['Date'])
    union_df['Day of Month'] = union_df['Date'].dt.day
    union_df['Month'] = union_df['Date'].dt.month
    union_df['Year'] = union_df['Date'].dt.year

    with st.expander("Combined Data:"):
        st.write(union_df)


# Sort transactions in ascending order (so paycheck assignment works correctly)
union_df = union_df.sort_values(by='Date', ascending=True)

# Identify paycheck deposit dates
paycheck_mask = union_df['Description'] == "Defense Finance and Accounting Service"
paycheck_dates = union_df.loc[paycheck_mask, 'Date']

# Initialize "Paycheck Cycle" with default value "Paycheck 1"
union_df['Paycheck Cycle'] = None

# Initialize "Paycheck Month" with NaN
union_df['Paycheck Year Month'] = None

# Process each paycheck in order
paycheck_number = 1  # Start with Paycheck 1
paycheck_month = None  # Store the current Paycheck Month

for i, date in enumerate(paycheck_dates):
    # Only update the paycheck month when it's the first paycheck of the month
    if paycheck_number == 1:
        paycheck_month = date.strftime('%Y-%m')

    # Assign transactions from this paycheck onward
    union_df.loc[union_df['Date'] >= date, ['Paycheck Cycle', 'Paycheck Year Month']] = [
        f'Paycheck {paycheck_number}', paycheck_month]

    # Alternate paycheck number for the next deposit
    paycheck_number = 1 if paycheck_number == 2 else 2

# Forward-fill the Paycheck Month for transactions before the first paycheck
union_df['Paycheck Year Month'] = union_df['Paycheck Year Month'].ffill()

# Add one month to each Paycheck Year Month
union_df['Paycheck Year Month'] = pd.to_datetime(
    union_df['Paycheck Year Month']) + pd.DateOffset(months=1)
union_df['Paycheck Year Month'] = union_df['Paycheck Year Month'].dt.strftime(
    '%Y-%m')

# Reverse order back to descending
union_df = union_df.sort_values(
    by='Date', ascending=False).reset_index(drop=True)

# expenses
expense_data = union_df.loc[union_df.Amount < 0].reset_index(drop=True)
expense_data.Amount = expense_data.Amount * -1

# defense income
defense_income_data = union_df.loc[union_df.Description.str.contains(
    'Defense')].reset_index(drop=True)

# all income
income_data = union_df.loc[union_df.Amount > 0].reset_index(drop=True)

# expense pivot table by paycheck month
expense_pivot = expense_data.pivot_table(
    index=['Paycheck Cycle', 'Paycheck Year Month'], values='Amount', aggfunc='sum')
expense_pivot.reset_index(inplace=True)
expense_paycheck1 = expense_pivot.loc[expense_pivot['Paycheck Cycle']
                                      == 'Paycheck 1'].reset_index(drop=True)
expense_paycheck2 = expense_pivot.loc[expense_pivot['Paycheck Cycle']
                                      == 'Paycheck 2'].reset_index(drop=True)

# defense income pivot table
defense_income_pivot = pd.DataFrame(defense_income_data.pivot_table(
    index=['Paycheck Cycle', 'Paycheck Year Month'], values='Amount', aggfunc='sum'))
defense_income_pivot.reset_index(inplace=True)
defense_income_paycheck1 = defense_income_pivot.loc[defense_income_pivot['Paycheck Cycle'] == 'Paycheck 1'].reset_index(
    drop=True)
defense_income_paycheck2 = defense_income_pivot.loc[defense_income_pivot['Paycheck Cycle'] == 'Paycheck 2'].reset_index(
    drop=True)

# Q1 ANSWER: average expense for paycheck cycle in txn data
averge_paycheck_cycle_expenses = pd.pivot_table(
    expense_pivot, values='Amount', index=['Paycheck Cycle'], aggfunc='mean')
averge_paycheck_cycle_expenses.reset_index(inplace=True)

# Q1 ANSWER: average expense count for paycheck cycle in txn data
cycle_expense_counts = pd.pivot_table(expense_data, values='Amount', index=[
                                      'Paycheck Cycle', 'Paycheck Year Month'], aggfunc='count')
cycle_expense_counts.reset_index(inplace=True)
cycle_expense_avg_counts = pd.pivot_table(
    cycle_expense_counts, values='Amount', index=['Paycheck Cycle'], aggfunc='mean')
cycle_expense_avg_counts.reset_index(inplace=True)

# Q2 ANSWER: recurring and common expenses
# obtain all expense descriptions
expense_description = expense_data['Description'].unique()

# initial a list of reucrring expense descriptions
recurring_expense_description = []

# filter the `expense_data` by each value in `expense_description`
for description_i in expense_description:
    # store the description to `recurring_expense_description` if it occurs in multiple transactions (rows)
    if len(expense_data.loc[expense_data['Description'] == description_i]) >= 2:
        recurring_expense_description.append(description_i)

# filter the expense data with recurring transactions
recurring_expenses = expense_data.loc[expense_data['Description'].isin(
    recurring_expense_description)]

# make a pivot table of the average recurring expense for each paycheck cycle (date included)
recurring_expenses_date_included_pivot = pd.pivot_table(recurring_expenses, values=[
                                                        'Amount'], index=['Paycheck Cycle', 'Description', 'Date'], aggfunc='mean')
recurring_expenses_date_included_pivot.reset_index(inplace=True)
recurring_expenses_date_included_pivot["Amount"] = round(
    recurring_expenses_date_included_pivot["Amount"], 2)


# make a pivot table of the average recurring expense for each day
recurring_expenses_day_included_pivot = pd.pivot_table(recurring_expenses, values=[
                                                       'Amount'], index=['Description', 'Day of Month', 'Month', 'Year'], aggfunc='mean')
recurring_expenses_day_included_pivot.reset_index(inplace=True)
recurring_expenses_day_included_pivot["Amount"] = round(
    recurring_expenses_day_included_pivot["Amount"], 2)

# make a pivot table of the average recurring expense for each paycheck cycle
recurring_expenses_pivot = pd.pivot_table(recurring_expenses, values=[
                                          'Amount'], index=['Paycheck Cycle', 'Description'], aggfunc='mean')
recurring_expenses_pivot.reset_index(inplace=True)
recurring_expenses_pivot["Amount"] = round(
    recurring_expenses_pivot["Amount"], 2)

# Group by 'Description' and aggregate to find range and amount mean
recurring_expenses_charge_range = recurring_expenses.groupby('Description', as_index=False).agg({
    'Day of Month': ['min', 'max'], 'Amount': 'mean'
})

# Rename columns for clarity
recurring_expenses_charge_range.columns = [
    'Description', 'Min Charge Day', 'Max Charge Day', 'Mean Amount']
recurring_expenses_charge_range['Mean Amount'] = round(
    recurring_expenses_charge_range['Mean Amount'], 2)

# Display result
recurring_expenses_charge_range['Delta'] = recurring_expenses_charge_range['Max Charge Day'] - \
    recurring_expenses_charge_range['Min Charge Day']
recurring_expenses_charge_range = recurring_expenses_charge_range.sort_values(
    by=['Min Charge Day', 'Max Charge Day'], ascending=[True, True]).reset_index(drop=True)

# Q3 ANSWER: sorted by expense in descending order, and description (gives insight into the frequency and magnitude of expenses in order)
sorted_expense_data = expense_data.sort_values(by=['Paycheck Cycle', 'Amount', 'Description', 'Date'], ascending=[
                                               True, False, True, True]).reset_index(drop=True)

# Q8 ANSWER: running total amount
union_df = union_df.sort_values(
    by='Date', ascending=True).reset_index(drop=True)
runner = 3400.02
full_length = len(union_df)
I = range(full_length)
for i in I:
    runner += union_df.loc[i, 'Amount']
    union_df.loc[i, 'Running Total'] = runner
union_df = union_df.sort_values(
    by='Date', ascending=False).reset_index(drop=True)

most_recent_income_amount = defense_income_data.loc[defense_income_data['Paycheck Year Month']
                                                    == defense_income_data['Paycheck Year Month'].max()]
most_recent_income = most_recent_income_amount['Amount'][:-1].values[0]

info = {
    'all_transactions': union_df,  # all transactions
    'expenses': expense_data,  # expenses
    'defense_income': defense_income_data,  # AF paychecks
    'income': income_data,  # nonnegative transactions
    'most_recent_income': most_recent_income,  # most recent paycheck
    'expense_pivot': expense_pivot,  # sum of expenses for each paycheck, for each month
    # Paycheck 1 avg, Paycheck 2 avg
    'averge_paycheck_cycle_expenses': averge_paycheck_cycle_expenses,
    # count of expenses for each paycheck
    'cycle_expense_avg_counts': cycle_expense_avg_counts,
    # df of transactions whose descriptions are recurring
    'recurring_expenses': recurring_expenses,
    # index=paycheck, description, date | amount aggfunc=mean
    'recurring_expenses_date_included_pivot': recurring_expenses_date_included_pivot,
    # index=paycheck, description | amount aggfunc=mean
    'recurring_expenses_pivot': recurring_expenses_pivot,
    # check recurring transaction descriptions and then the DAY they are made, aggregated by avergae price
    'recurring_expense_description_day': recurring_expenses_day_included_pivot,
    # check recurring transaction descriptions and then the range of days it has been historically charged, aggregated by avergae price
    'recurring_expenses_charge_range': recurring_expenses_charge_range,
    # check where bulk our expenses are going and their frequency
    'sorted_expense_data': sorted_expense_data
}


# Display income vs expenses overtime
income_mean = defense_income_data.groupby(
    'Paycheck Cycle').agg({'Amount': 'mean'})
income_mean['Amount'] = round(income_mean['Amount'], 2)
income_mean = income_mean.rename(columns={"Amount": "Income"})

expense_mean = averge_paycheck_cycle_expenses.groupby(
    'Paycheck Cycle').agg({'Amount': 'mean'})
expense_mean["Amount"] = round(expense_mean["Amount"], 2)
expense_mean = expense_mean.rename(columns={"Amount": "Expense"})

income_expense_mean = pd.merge(
    income_mean, expense_mean, on=["Paycheck Cycle"])
income_expense_mean['Delta'] = income_expense_mean['Income'] - \
    income_expense_mean["Expense"]
with st.expander('Income and expense average to date'):
    income_expense_mean

# Display income vs expenses for each Paycheck Year Month
income_data_ym = defense_income_data.groupby(
    ['Paycheck Year Month', 'Paycheck Cycle']).agg({'Amount': 'sum'})
income_data_ym['Amount'] = round(income_data_ym['Amount'], 2)
income_data_ym = income_data_ym.rename(columns={'Amount': 'Income'})

expense_sum_ym = expense_data.groupby(
    ['Paycheck Year Month', 'Paycheck Cycle']).agg({'Amount': 'sum'})
expense_sum_ym['Amount'] = round(expense_sum_ym['Amount'], 2)
expense_sum_ym = expense_sum_ym.rename(columns={'Amount': 'Expense'})

income_expense_ym = pd.merge(expense_sum_ym, income_data_ym, on=[
                             "Paycheck Year Month", 'Paycheck Cycle'])
income_expense_ym['Delta'] = income_expense_ym['Income'] - \
    income_expense_ym['Expense']
income_expense_ym = income_expense_ym.sort_values(
    ['Paycheck Year Month', 'Paycheck Cycle'], ascending=[False, True])

with st.expander('Total expenses and income for each paycheck interval to date'):
    income_expense_ym

# Display recurring and common expenses
with st.expander('Common and recurring expenses with their charge date range'):
    st.dataframe(recurring_expenses_charge_range)

with st.expander('All expenses'):
    col_order = ['Day of Month', 'Paycheck Year Month', 'Paycheck Cycle', 'Description', 'Amount']
    st.dataframe(expense_data[col_order])

# Display irregular recurring expenses
with st.expander('Irregularly Recurring Details'):
    irreg_exp = {
        'Cycle': ['Quarterly', 'Quarterly', 'Bimonthly', 'Annual', 'Annual', 'Annual'],
        'Merchant': ['Mint (C)', 'Mint (R)', 'Anti-Pest', 'Google Cloud 200 GB (R)', 'Chat GPT', 'Walmart+'], 
        'Cost': [120.00, 120.00, 80.00, 30.89, 39.99, 98.00],
        'Month': ['Jan, Apr, Jul, Oct', 'Jan, Apr, Jul, Oct', 'Jan, Mar, May, Jul, Sep, Nov', 'Jul', 'Jul', 'May']
    }
    irreg_exp_df = pd.DataFrame(irreg_exp)
    col_order_ir_exp = ['Cycle', 'Merchant','Month']
    st.dataframe(irreg_exp_df[col_order_ir_exp])

# Display irregular recurring expenses navigation
with st.expander('Irregularly Recurring Navigation'):
    irreg_exp_nav = {
        'Merchant': ['Mint (C)', 'Mint (R)', 'Anti-Pest', 'Google Cloud 200 GB (R)', 'Chat GPT', 'Walmart+'],
        'Nav': ['Mint Mobil App or https://my.mintmobile.com/account/summary/primary', 'Mint Mobil App or https://my.mintmobile.com/account/summary/primary', 'Call 318-668-2682', 'https://play.google.com/store/account/subscriptions', 'https://play.google.com/store/account/subscriptions', 'https://www.walmart.com/account/plus/manage']
            }
    irreg_exp_nav_df = pd.DataFrame(irreg_exp_nav)
    col_order_ir_exp_nav = ['Merchant','Nav']
    st.dataframe(irreg_exp_nav_df[col_order_ir_exp_nav])
'''
Expense-Income Overlap Visual
'''

'''
Paycheck 1 Interval
'''

# break up paycheck cycles
income_expense_ym = income_expense_ym.reset_index(drop=False)
cond = (income_expense_ym['Paycheck Cycle'] == 'Paycheck 1')
income_expense_ym1 = income_expense_ym[cond]

cond = (income_expense_ym['Paycheck Cycle'] == 'Paycheck 2')
income_expense_ym2 = income_expense_ym[cond]

st.bar_chart(data=income_expense_ym1, x="Paycheck Year Month", y=[
             "Expense", "Income"], stack='layered', color=['#ff0000', '#0000ff'])

'''
Paycheck 2 Interval
'''
st.bar_chart(data=income_expense_ym2, x="Paycheck Year Month", y=[
             "Expense", "Income"], stack='layered', color=['#ff0000', '#0000ff'])


PAYCHECK1_EXPENSES = "paycheck1_expenses.csv"
PAYCHECK2_EXPENSES = "second_paycheck_expenses.csv"
PAYCHECK1_INCOME = 'paycheck1_income.json'
PAYCHECK2_INCOME = 'paycheck2_income.json'
GROCERY_BUDGET = 'grocery_budget.csv'
GROCERY_EXPENSES = 'grocery_expenses.csv'

# Load data from CSV
def load_data():
    return pd.read_csv(PAYCHECK1_EXPENSES) if os.path.exists(PAYCHECK1_EXPENSES) else pd.DataFrame(columns=['txn', 'cost', 'd'])

# Save data to CSV
def save_data():
    st.session_state.paycheck1_expenses.to_csv(PAYCHECK1_EXPENSES, index=False)

# Load second paycheck expenses data
def load_second_paycheck_data():
    return pd.read_csv(PAYCHECK2_EXPENSES) if os.path.exists(PAYCHECK2_EXPENSES) else pd.DataFrame(columns=['txn', 'cost', 'd'])

# Save second paycheck expenses data
def save_second_paycheck_data():
    st.session_state.second_paycheck_expenses.to_csv(PAYCHECK2_EXPENSES, index=False)

# Load grocery data
def load_grocery_expense_data():
    return pd.read_csv(GROCERY_EXPENSES) if os.path.exists(GROCERY_EXPENSES) else pd.DataFrame(columns=['date', 'store', 'amount'])

# Save grocery data
def save_grocery_expense_data():
    st.session_state.grocery_expense_data.to_csv(GROCERY_EXPENSES, index=False)

# Load income data (ensure it's a float)
def load_paycheck1():
    if os.path.exists(PAYCHECK1_INCOME):
        with open(PAYCHECK1_INCOME, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# SAVE Paycheck 1 INCOME
def save_paycheck1():
    with open(PAYCHECK1_INCOME, 'w') as f:
        json.dump({'paycheck1_key': st.session_state.paycheck1_key}, f)

# LOAD Paycheck 2 INCOME
def load_paycheck2():
    if os.path.exists(PAYCHECK2_INCOME):
        with open(PAYCHECK2_INCOME, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# SAVE Paycheck 2 INCOME
def save_paycheck2():
    with open(PAYCHECK2_INCOME, 'w') as f:
        json.dump({'paycheck2_key': st.session_state.paycheck2_key}, f)

# LOAD Grocery Budget
def load_groc_budget():
    if os.path.exists(GROCERY_BUDGET):
        with open(GROCERY_BUDGET, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# SAVE Grocery Budget
def save_groc_budget():
    with open(GROCERY_BUDGET, 'w') as f:
        json.dump({'grocery_budget_key': st.session_state.grocery_budget_key}, f)

# Initialize session state
if 'paycheck1_expenses' not in st.session_state:
    st.session_state.paycheck1_expenses = load_data()

if 'second_paycheck_expenses' not in st.session_state:
    st.session_state.second_paycheck_expenses = load_second_paycheck_data()

if 'grocery_expense_data' not in st.session_state:
    st.session_state.grocery_expense_data = load_grocery_expense_data()

session_paycheck1 = load_paycheck1()
st.session_state.setdefault(
    'paycheck1_key', session_paycheck1.get('paycheck1_key', 0.0)
    )

session_paycheck2 = load_paycheck2()
st.session_state.setdefault(
    'paycheck2_key', session_paycheck2.get('paycheck2_key', 0.0)
    )

session_grocery = load_groc_budget()
st.session_state.setdefault(
    'grocery_budget_key', session_grocery.get('grocery_budget_key', 0.0)
    )

# User sets their income (persists across sessions, but defaults to `most_recent_income`)
st.sidebar.header("Income Settings")
st.sidebar.number_input(
    "Set Paycheck 1 Income",
    min_value=0.0,
    value=float(most_recent_income),  # Ensure it's float
    step=100.0,
    key='paycheck1_key',
    on_change=save_paycheck1
)

st.sidebar.number_input(
    "Set Paycheck 2 Income",
    min_value=0.0,
    value=float(most_recent_income),  # Ensure it's float
    step=100.0,
    key='paycheck2_key',
    on_change=save_paycheck2
)

# Calculate total cost of paycheck1_expenses and second paycheck expenses
paycheck1_total_expenses = st.session_state.paycheck1_expenses['cost'].sum(
) if not st.session_state.paycheck1_expenses.empty else 0
paycheck2_total_expense = st.session_state.second_paycheck_expenses['cost'].sum(
) if not st.session_state.second_paycheck_expenses.empty else 0

# Calculate total cost of groceries so far
grocery_total_expenses = st.session_state.grocery_expense_data['amount'].sum(
) if not st.session_state.grocery_expense_data.empty else 0

# Remaining balance for first and second paycheck
remaining_balance_first_paycheck = st.session_state.paycheck1_key - paycheck1_total_expenses
remaining_balance_second_paycheck = st.session_state.paycheck2_key - paycheck2_total_expense

# Remaining balance for grocery budget
remaining_grocery_budget = st.session_state.grocery_budget_key - grocery_total_expenses

st.write("### Paycheck 1 Expenses")
# Display the remaining balance for paycheck 1
st.metric(label="Remaining Balance (Paycheck 1)",
          value=f"${remaining_balance_first_paycheck:,.2f}", delta=f"-${paycheck1_total_expenses:,.2f}")

# Subscription Entry Form for first paycheck
with st.form('New Subscription'):
    st.write('Enter the details of your new expense for Paycheck 1')
    txn = st.text_input("Transaction Name")
    cost = st.number_input("Cost", min_value=0.0, step=0.01)
    d = st.date_input("Charge Date")
    submitted = st.form_submit_button("Submit")

if submitted and txn:
    new_entry = pd.DataFrame([[txn, cost, d]], columns=['txn', 'cost', 'd'])
    st.session_state.paycheck1_expenses = pd.concat(
        [st.session_state.paycheck1_expenses, new_entry], ignore_index=True)
    save_data()
    st.rerun()

# # Display subscription list for Paycheck 1
# st.write("### Expense List (Paycheck 1)")
# for index, row in st.session_state.paycheck1_expenses.iterrows():
#     col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
#     col1.write(row['txn'])
#     col2.write(f"${row['cost']:.2f}")
#     col3.write(row['d'])

#     if col4.button("❌", key=f"del_{index}"):
#         st.session_state.paycheck1_expenses.drop(index, inplace=True)
#         st.session_state.paycheck1_expenses.reset_index(drop=True, inplace=True)
#         save_data()
#         st.rerun()

# st.write("### Expense List (Paycheck 1)")

# updated_expenses = st.session_state.paycheck1_expenses.copy()

# for index, row in updated_expenses.iterrows():
#     col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
    
#     # Editable fields
#     txn = col1.text_input("Transaction", row['txn'], key=f"txn_{index}")
#     cost = col2.number_input("Cost", value=row['cost'], min_value=0.0, step=0.01, key=f"cost_{index}")
#     d = col3.date_input("Charge Date", row['d'], key=f"date_{index}")

#     # Delete button
#     if col4.button("❌", key=f"del_{index}"):
#         updated_expenses.drop(index, inplace=True)
#         updated_expenses.reset_index(drop=True, inplace=True)
#         st.session_state.paycheck1_expenses = updated_expenses
#         save_data()
#         st.rerun()

# # Save updates if anything changed
# if not updated_expenses.equals(st.session_state.paycheck1_expenses):
#     st.session_state.paycheck1_expenses = updated_expenses
#     save_data()
#     st.rerun()

import datetime

st.write("### Expense List (Paycheck 1)")

updated_expenses = st.session_state.paycheck1_expenses.copy()

for index, row in st.session_state.paycheck1_expenses.iterrows():
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

    # Unique keys for session state storage
    txn_key = f"txn_{index}"
    cost_key = f"cost_{index}"
    date_key = f"date_{index}"

    # Initialize session state with existing row values
    if txn_key not in st.session_state:
        st.session_state[txn_key] = row['txn']
    if cost_key not in st.session_state:
        st.session_state[cost_key] = row['cost']
    if date_key not in st.session_state:
        # Convert string to date if necessary
        if isinstance(row['d'], str):
            st.session_state[date_key] = datetime.datetime.strptime(row['d'], "%Y-%m-%d").date()
        else:
            st.session_state[date_key] = row['d']

    # Editable fields
    txn = col1.text_input("Transaction", st.session_state[txn_key], key=txn_key)
    cost = col2.number_input("Cost", value=st.session_state[cost_key], min_value=0.0, step=0.01, key=cost_key)
    d = col3.date_input("Charge Date", value=st.session_state[date_key], key=date_key)

    # Update DataFrame with new values
    updated_expenses.at[index, 'txn'] = txn
    updated_expenses.at[index, 'cost'] = cost
    updated_expenses.at[index, 'd'] = d

    # Delete button
    if col4.button("❌", key=f"del_{index + 1}"):
        updated_expenses.drop(index, inplace=True)
        updated_expenses.reset_index(drop=True, inplace=True)
        st.session_state.paycheck1_expenses = updated_expenses
        save_data()
        st.rerun()

# Save updates back to session state if there are changes
if not updated_expenses.equals(st.session_state.paycheck1_expenses):
    st.session_state.paycheck1_expenses = updated_expenses
    save_data()


if st.button("Clear All Paycheck 1 Expenses"):
    st.session_state.paycheck1_expenses = pd.DataFrame(columns=['txn', 'cost', 'd'])
    save_data()
    st.rerun()

# Second Paycheck Expenses Form
# Show the remaining balance for the second paycheck
st.write("### Paycheck 2 Expenses")
st.metric(label="Remaining Balance (Paycheck 2)",
          value=f"${remaining_balance_second_paycheck:,.2f}", delta=f"-${paycheck2_total_expense:,.2f}")

st.write("### Paycheck 2 Expenses")
with st.form('New Second Paycheck Expense'):
    st.write('Enter the details of your new expense for Paycheck 2')
    txn_2 = st.text_input("Transaction Name (Paycheck 2)")
    cost_2 = st.number_input("Cost (Paycheck 2)", min_value=0.0, step=0.01)
    d_2 = st.date_input("Charge Date (Paycheck 2)")
    submitted_2 = st.form_submit_button("Submit (Paycheck 2)")

if submitted_2 and txn_2:
    new_entry_2 = pd.DataFrame(
        [[txn_2, cost_2, d_2]], columns=['txn', 'cost', 'd'])
    st.session_state.second_paycheck_expenses = pd.concat(
        [st.session_state.second_paycheck_expenses, new_entry_2], ignore_index=True)
    save_second_paycheck_data()
    st.rerun()

# # Display second paycheck expense list
# st.write("### Expense List (Paycheck 2)")
# for index, row in st.session_state.second_paycheck_expenses.iterrows():
#     col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
#     col1.write(row['txn'])
#     col2.write(f"${row['cost']:.2f}")
#     col3.write(row['d'])

#     if col4.button("❌", key=f"del_2_{index}"):
#         st.session_state.second_paycheck_expenses.drop(index, inplace=True)
#         st.session_state.second_paycheck_expenses.reset_index(
#             drop=True, inplace=True)
#         save_second_paycheck_data()
#         st.rerun()

#############################################################
import datetime

st.write("### Expense List (Paycheck 2)")

updated_expenses = st.session_state.second_paycheck_expenses.copy()

for index, row in st.session_state.second_paycheck_expenses.iterrows():
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

    # Unique keys for session state storage
    txn_key = f"txn2_{index}"
    cost_key = f"cost2_{index}"
    date_key = f"date2_{index}"

    # Initialize session state with existing row values
    if txn_key not in st.session_state:
        st.session_state[txn_key] = row['txn']
    if cost_key not in st.session_state:
        st.session_state[cost_key] = row['cost']
    if date_key not in st.session_state:
        # Convert string to date if necessary
        if isinstance(row['d'], str):
            st.session_state[date_key] = datetime.datetime.strptime(row['d'], "%Y-%m-%d").date()
        else:
            st.session_state[date_key] = row['d']

    # Editable fields
    txn = col1.text_input("Transaction", st.session_state[txn_key], key=txn_key)
    cost = col2.number_input("Cost", value=st.session_state[cost_key], min_value=0.0, step=0.01, key=cost_key)
    d = col3.date_input("Charge Date", value=st.session_state[date_key], key=date_key)

    # Update DataFrame with new values
    updated_expenses.at[index, 'txn'] = txn
    updated_expenses.at[index, 'cost'] = cost
    updated_expenses.at[index, 'd'] = d

    # Delete button
    if col4.button("❌", key=f"del2_{index + 1}"):
        updated_expenses.drop(index, inplace=True)
        updated_expenses.reset_index(drop=True, inplace=True)
        st.session_state.second_paycheck_expenses = updated_expenses
        save_second_paycheck_data()
        st.rerun()

# Save updates back to session state if there are changes
if not updated_expenses.equals(st.session_state.second_paycheck_expenses):
    st.session_state.second_paycheck_expenses = updated_expenses
    save_second_paycheck_data()

# Button to clear all second paycheck expenses
if st.button("Clear All Paycheck 2 Expenses"):
    st.session_state.second_paycheck_expenses = pd.DataFrame(
        columns=['txn', 'cost', 'd'])
    save_second_paycheck_data()
    st.rerun()

# Grocery
st.write('### Grocery Budget')
# Budget decision input
st.number_input(
    'Decision',
    min_value=0.0,
    value=0.0,
    step=10.0,
    key='grocery_budget_key',
    on_change=save_groc_budget
    )
# Metric
st.metric(
    label='Remaining Balance',
    value=f'${remaining_grocery_budget:,.2f}',
    delta=f'-${grocery_total_expenses:,.2f}'
          )

# Grocery Form
st.write('Grocery Expense List')
with st.form('New Grocery Expense'):
    st.write('Enter the details of your new grocery expense')
    store = st.text_input('Store')
    costt = st.number_input('Cost', min_value=0.0, step=1.0)
    dt = st.date_input('Charge Date')
    submit = st.form_submit_button('Submit Expense')

if submit and store:
    nw_entry = pd.DataFrame(
        [[dt, store, costt]], columns=['date', 'store', 'amount']
    )
    st.session_state.grocery_expense_data = pd.concat(
        [st.session_state.grocery_expense_data, nw_entry], ignore_index=True
    )
    save_grocery_expense_data()
    st.rerun()

# # Display second paycheck expense list
# st.write("### Expense List (Groceries)")
# for index, row in st.session_state.grocery_expense_data.iterrows():
#     col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
#     col1.write(row['store'])
#     col2.write(f"${row['amount']:.2f}")
#     col3.write(row['date'])

#     if col4.button("❌", key=f"del_3_{index}"):
#         st.session_state.grocery_expense_data.drop(index, inplace=True)
#         st.session_state.grocery_expense_data.reset_index(
#             drop=True, inplace=True)
#         save_grocery_expense_data()
#         st.rerun()
import datetime

st.write("### Expense List (Groceries)")

updated_expenses = st.session_state.grocery_expense_data.copy()

for index, row in st.session_state.grocery_expense_data.iterrows():
    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

    # Unique keys for session state storage
    txn_key = f"txn3_{index}"
    cost_key = f"cost3_{index}"
    date_key = f"date3_{index}"

    # Initialize session state with existing row values
    if txn_key not in st.session_state:
        st.session_state[txn_key] = row['store']
    if cost_key not in st.session_state:
        st.session_state[cost_key] = row['amount']
    if date_key not in st.session_state:
        # Convert string to date if necessary
        if isinstance(row['date'], str):
            st.session_state[date_key] = datetime.datetime.strptime(row['date'], "%Y-%m-%d").date()
        else:
            st.session_state[date_key] = row['date']

    # Editable fields
    txn = col1.text_input("Transaction", st.session_state[txn_key], key=txn_key)
    cost = col2.number_input("Cost", value=st.session_state[cost_key], min_value=0.0, step=0.01, key=cost_key)
    d = col3.date_input("Charge Date", value=st.session_state[date_key], key=date_key)

    # Update DataFrame with new values
    updated_expenses.at[index, 'store'] = txn
    updated_expenses.at[index, 'amount'] = cost
    updated_expenses.at[index, 'date'] = d

    # Delete button
    if col4.button("❌", key=f"del3_{index}"):
        updated_expenses.drop(index, inplace=True)
        updated_expenses.reset_index(drop=True, inplace=True)
        st.session_state.grocery_expense_data = updated_expenses
        save_grocery_expense_data()
        st.rerun()

# Save updates back to session state if there are changes
if not updated_expenses.equals(st.session_state.grocery_expense_data):
    st.session_state.grocery_expense_data = updated_expenses
    save_grocery_expense_data()
# Button to clear all second paycheck expenses
if st.button("Clear All Grocery Expenses"):
    st.session_state.grocery_expense_data = pd.DataFrame(
        columns=['date', 'store', 'amount'])
    save_grocery_expense_data()
    st.rerun()

st.write('Grocery Budget App: https://grocery-budget-9n4dqk3iap.streamlit.app/')

# Sidebar for managing uploaded files
st.sidebar.title("Uploaded Files")

# If there are files in the session state, display them with options
if 'data_files' in st.session_state and st.session_state['data_files']:
    # Display the list of files with delete options in columns
    for i, file_info in enumerate(st.session_state['data_files']):
        file_name = file_info['file_name']

        # Create two columns: one for the file name, one for the delete button
        # Adjust column width as needed
        col1, col2 = st.sidebar.columns([4, 1])

        with col1:
            st.write(file_name)

        with col2:
            # Create a unique key for each button to avoid conflicts
            if st.button(f":x:", key=f"delete_{i}"):
                st.session_state['data_files'].pop(i)
                # Save the updated session state to persistent storage
                with open(data_file_path, "wb") as f:
                    pickle.dump(st.session_state['data_files'], f)
                st.sidebar.write(f"{file_name} deleted.")
                break  # Ensure only one file is deleted at a time

    # Option to clear all files
    if st.sidebar.button("Clear All Files"):
        st.session_state['data_files'] = []
        # Save the empty list to persistent storage
        with open(data_file_path, "wb") as f:
            pickle.dump(st.session_state['data_files'], f)
        st.sidebar.write("All files cleared.")
