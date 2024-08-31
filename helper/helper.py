from datetime import datetime

def update_balances_transaction(balances, transaction, operation, old_share_details=None, old_paid_by=None):
    paid_by = transaction.paid_by
    share_details = transaction.share_details

    if operation == 'add':
        for payer in paid_by:
            username, amount = payer['username'], payer['amount']
            balances[username] = balances.get(username, 0) + amount
        for share in share_details:
            username, amount = share['username'], share['amount']
            balances[username] = balances.get(username, 0) - amount
    elif operation == 'update':
        for payer in old_paid_by:
            username, amount = payer['username'], payer['amount']
            balances[username] = balances.get(username, 0) - amount
        for share in old_share_details:
            username, amount = share['username'], share['amount']
            balances[username] = balances.get(username, 0) + amount
        
        for payer in paid_by:
            username, amount = payer['username'], payer['amount']
            balances[username] = balances.get(username, 0) + amount
        for share in share_details:
            username, amount = share['username'], share['amount']
            balances[username] = balances.get(username, 0) - amount
    elif operation == 'delete':
        for payer in paid_by:
            username, amount = payer['username'], payer['amount']
            balances[username] = balances.get(username, 0) - amount
        for share in share_details:
            username, amount = share['username'], share['amount']
            balances[username] = balances.get(username, 0) + amount

    return balances

def update_balances_payment(balances, payment, operation, old_paid_from=None, old_paid_to=None, old_payment_amount=None):
    if operation == 'update':
        balances[old_paid_from] -= old_payment_amount
        balances[old_paid_to] += old_payment_amount

    balances[payment.paid_from] += payment.amount if operation != 'delete' else -payment.amount
    balances[payment.paid_to] -= payment.amount if operation != 'delete' else -payment.amount

    return balances


def settle_up(balances):
    creditors = sorted((user, balance) for user, balance in balances.items() if balance > 0)
    debtors = sorted((user, -balance) for user, balance in balances.items() if balance < 0)

    settlements = []
    while creditors and debtors:
        creditor, credit_amount = creditors.pop(0)
        debtor, debt_amount = debtors.pop(0)

        settlement_amount = min(credit_amount, debt_amount)

        settlements.append({
            "creditor": creditor,
            "debtor": debtor,
            "amount": settlement_amount
        })

        if credit_amount > settlement_amount:
            creditors.insert(0, (creditor, credit_amount - settlement_amount))
        if debt_amount > settlement_amount:
            debtors.insert(0, (debtor, debt_amount - settlement_amount))

    return settlements

def calculate_user_expenditures(transactions):
    user_expenditures = {}

    for transaction in transactions:
        share_details = transaction.share_details

        # Add expenditures for users based on their shares
        for share in share_details:
            username, amount = share['username'],share['amount']
            if username not in user_expenditures:
                user_expenditures[username] = 0
            user_expenditures[username] += amount

    return user_expenditures

def validate_usernames(group, data):
    group_usernames = {user['username'] for user in group.usernames}
    paid_by_usernames = {payer['username'] for payer in data.get('paid_by', [])}
    paid_for_usernames = set(data.get('paid_for', []))
    share_details_usernames = {share['username'] for share in data.get('share_details', [])}
    
    paid_from_username = data.get('paid_from', None)
    paid_to_username = data.get('paid_to', None)
    
    all_usernames = paid_by_usernames | paid_for_usernames | share_details_usernames
    
    if paid_from_username:
        all_usernames.add(paid_from_username)
    if paid_to_username:
        all_usernames.add(paid_to_username)
    
    return all(username in group_usernames for username in all_usernames)

def process_transaction_data(data, existing_transaction=None):
    return {
        'amount': data.get('amount', existing_transaction.amount if existing_transaction else None),
        'paid_by': data.get('paid_by', existing_transaction.paid_by if existing_transaction else None),
        'mode': data.get('mode', existing_transaction.mode if existing_transaction else None),
        'paid_for': data.get('paid_for', existing_transaction.paid_for if existing_transaction else None),
        'share_details': data.get('share_details', existing_transaction.share_details if existing_transaction else None),
        'datetime_transaction': data.get('datetime_transaction', existing_transaction.datetime_transaction if existing_transaction else datetime.now()),
        'is_saved': data.get('is_saved', existing_transaction.is_saved if existing_transaction else False),
        'description':data.get('description', existing_transaction.description if existing_transaction else 'Unnamed')
    }
    
def process_payment_data(data, existing_payment=None):
    return{
        'amount':data.get('amount',existing_payment.amount if existing_payment else None),
        'paid_from': data.get('paid_from',existing_payment.paid_from if existing_payment else None),
        'paid_to': data.get('paid_to', existing_payment.paid_to if existing_payment else None),
        'datetime_payment':data.get('datetime_payment',existing_payment.datetime_payment if existing_payment else datetime.now())
    }