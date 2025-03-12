import json
import streamlit as st
import pandas as pd
import os

GROCERY_BUDGET = 'grocery_budget.csv'
GROCERY_EXPENSES = 'grocery_expenses.csv'

# Load grocery data
def load_grocery_expense_data():
    return pd.read_csv(GROCERY_EXPENSES) if os.path.exists(GROCERY_EXPENSES) else pd.DataFrame(columns=['date', 'store', 'amount'])

# Save grocery data
def save_grocery_expense_data():
    st.session_state.grocery_expense_data.to_csv(GROCERY_EXPENSES, index=False)

# Initialize
if 'grocery_expense_data' not in st.session_state:
    st.session_state.grocery_expense_data = load_grocery_expense_data()

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

# Calculate total cost of groceries so far
grocery_total_expenses = st.session_state.grocery_expense_data['amount'].sum(
) if not st.session_state.grocery_expense_data.empty else 0

# Remaining balance for grocery budget
remaining_grocery_budget = st.session_state.grocery_budget_key - grocery_total_expenses

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