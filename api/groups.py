import sys
from flask import Blueprint, request, jsonify
from backend.db import db
from backend.models.group import Group
from backend.models.transaction import Transaction
from backend.models.payment import Payment
from backend.helper.helper import calculate_user_expenditures
from backend.helper.helper import settle_up
from sqlalchemy.orm.attributes import flag_modified

bp = Blueprint('groups', __name__)

@bp.route('/group', methods=['POST'])
def create_group():
    data = request.get_json()
    name = data.get('name')
    usernames = data.get('usernames', [])

    # Check if name is provided
    if not name:
        return jsonify({"message": "Group name is required"}), 400

    # Check for duplicate usernames
    if len(usernames) != len(set(user['username'] for user in usernames)):
        return jsonify({"message": "Duplicate usernames in the batch"}), 400

    try:
        # Initialize balances and ensure upi_id is set to None if not provided
        balances={}
        for user in usernames:
            user['upi_id'] = user.get('upi_id', None)  # Set upi_id to None if not provided
            balances[user['username']]=0
            

        # Create the group with usernames and balances
        group = Group(name=name, usernames=usernames,balances=balances)

        db.session.add(group)
        db.session.commit()

        return jsonify({"message": "Group added", "group": group.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@bp.route('/group/<int:group_id>/update_group_name', methods=['PUT'])
def update_group_name(group_id):
    group= Group.query.get(group_id)
    if group:
        data=request.get_json()
        new_group_name=data.get('new_group_name')
        if new_group_name:
            try:
                group.name=new_group_name
                db.session.commit()
                return jsonify({"message": "Group name updated","group":group.to_dict()}), 200
            
            except Exception as e:
                db.session.rollback()
                return jsonify({"message": f"An error occurred: {str(e)}"}), 500
        return jsonify({"message": "Invalid data"}), 400
    return jsonify({"message": "Group not found"}), 404
                
@bp.route('/group/<int:group_id>/add_username', methods=['PUT'])
def add_username(group_id):
    group = Group.query.get(group_id)
    if group:
        data = request.get_json()
        new_username = data.get('new_username')
        if new_username:
            # Check if the username already exists
            if any(user['username'] == new_username for user in group.usernames):
                return jsonify({"message": "Username already exists"}), 400
            
            try:
                group.usernames.append({"username": new_username, "upi_id": data.get('upi_id', None)})
                flag_modified(group, "usernames")
                group.balances[new_username] = 0
                # Mark the 'balances' field as modified
                flag_modified(group, "balances")
                db.session.commit()
                
                return jsonify({"message": "Username added","group":group.to_dict()}), 200
            except Exception as e:
                db.session.rollback()
                return jsonify({"message": f"An error occurred: {str(e)}"}), 500
        return jsonify({"message": "Invalid data"}), 400
    return jsonify({"message": "Group not found"}), 404


# Helper function to update transactions and payments
def update_transactions_and_payments(group_id, old_username, new_username):
    try:
        transactions = Transaction.query.filter_by(group_id=group_id).all()
        for transaction in transactions:
            # Update paid_by field
            transaction.paid_by = [{**entry, 'username': new_username} if entry['username'] == old_username else entry for entry in transaction.paid_by]   

            # Update paid_for field
            if old_username in transaction.paid_for:
                transaction.paid_for = [
                    new_username if u == old_username else u for u in transaction.paid_for
                ]

            # Update share_details field
            transaction.share_details = [
                {**detail, 'username': new_username} if detail['username'] == old_username else detail
                for detail in transaction.share_details
            ]
            db.session.add(transaction)

        payments = Payment.query.filter_by(group_id=group_id).all()
        for payment in payments:
            # Update paid_from field
            if old_username == payment.paid_from:
                payment.paid_from = new_username

            # Update paid_to field
            if old_username == payment.paid_to:
                payment.paid_to = new_username
            db.session.add(payment)

    except Exception as e:
        db.session.rollback()
        raise RuntimeError(f"Error updating transactions or payments: {e}")


# Route to update username
@bp.route('/group/<int:group_id>/update_username/<string:username>', methods=['PUT'])
def update_username(group_id, username):
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"message": "Group not found"}), 404

    data = request.get_json()
    new_username = data.get('new_username')
    new_upi_id = data.get('new_upi_id')

    if not new_username and not new_upi_id:
        return jsonify({"message": "Invalid data. Provide at least one field to update."}), 400

    # Find the user to update
    user = next((u for u in group.usernames if u['username'] == username), None)
    if not user:
        return jsonify({"message": "Username not found"}), 404

    try:
        # Handle username update
        if new_username:
            if any(u['username'] == new_username for u in group.usernames):
                return jsonify({"message": "Username already exists"}), 400

            # Update username in the usernames list and balances
            for u in group.usernames:
                if u['username'] == username:
                    u['username'] = new_username
                    if new_upi_id:
                        u['upi_id'] = new_upi_id
                    break
            group.balances[new_username] = group.balances.pop(username)

            # Update transactions and payments
            update_transactions_and_payments(group_id, username, new_username)

        # Handle UPI ID update
        if new_upi_id and not new_username:
            print("here")
            for u in group.usernames:
                if u['username'] == username:
                    u['upi_id'] = new_upi_id
                    break

        # Mark fields as modified and commit changes
        flag_modified(group, "usernames")
        flag_modified(group, "balances")
        db.session.commit()

        return jsonify({"message": "User information updated","group":group.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


# Route to delete username
@bp.route('/group/<int:group_id>/delete_username/<string:username>', methods=['DELETE'])
def delete_username(group_id, username):
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"message": "Group not found"}), 404

    if group.balances[username] != 0:
        return jsonify({"message": "Can delete user only when their settlement is done"}), 403

    try:
        # Remove the user from the group
        group.usernames = [user for user in group.usernames if user['username'] != username]
        del group.balances[username]

        # Update transactions and payments with a placeholder username
        new_username = f"<s>{username}</s> (deleted user)"
        update_transactions_and_payments(group_id, username, new_username)
        flag_modified(group, "balances")
        flag_modified(group, "usernames")
        db.session.commit()

        return jsonify({"message": "Username deleted","group":group.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500


@bp.route('/group/<int:group_id>/usernames',methods=['GET'])
def get_usernames(group_id):
    group=Group.query.get(group_id)
    if group:
        return jsonify({"name":group.name,"usernames":group.usernames})
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/transactions', methods=['GET'])
def get_group_transactions(group_id):
    group = Group.query.get(group_id)
    if group:
        transactions = Transaction.query.filter_by(group_id=group_id).order_by(Transaction.datetime_transaction.desc()).all()
        return jsonify([transaction.to_dict() for transaction in transactions]), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/saved_transactions', methods=['GET'])
def get_group_saved_transactions(group_id):
    group = Group.query.get(group_id)
    if group:
        transactions = Transaction.query.filter_by(group_id=group_id,is_saved=True).order_by(Transaction.datetime_transaction.desc()).all()
        return jsonify({transactions:[transaction.to_dict() for transaction in transactions]}), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/payments', methods=['GET'])
def get_group_payments(group_id):
    group = Group.query.get(group_id)
    if group:
        payments = Payment.query.filter_by(group_id=group_id).order_by(Payment.datetime_payment.desc()).all()
        return jsonify({"payments":[payment.to_dict() for payment in payments]}), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/total_expenditure', methods=['GET'])
def get_total_expenditure(group_id):
    group = Group.query.get(group_id)
    if group:
        total_expenditure = db.session.query(db.func.sum(Transaction.amount)).filter_by(group_id=group_id).scalar() or 0
        return jsonify({"total_expenditure": total_expenditure}), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/user_expenditure', methods=['GET'])
def get_user_expenditures(group_id):
    group = Group.query.get(group_id)
    if group:
        transactions = Transaction.query.filter_by(group_id=group_id).all()
        user_expenditures= calculate_user_expenditures(transactions)
        return jsonify({"user_expenditure":user_expenditures}), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/balances', methods=['GET'])
def get_balances(group_id):
    group = Group.query.get(group_id)
    if group:
        balances = group.balances
        return jsonify({"balances": balances}), 200
    return jsonify({"message": "Group not found"}), 404

@bp.route('/group/<int:group_id>/settlements', methods=['GET'])
def get_settlements(group_id):
    group = Group.query.get(group_id)
    if group:
        settlements = settle_up(group.balances)
        return jsonify({"settlements": settlements}), 200
    return jsonify({"message": "Group not found"}), 404
