from flask import Blueprint, request, jsonify
from backend.db import db
from backend.models.transaction import Transaction
from backend.websocket import socketio
from backend.models.group import Group
from backend.helper.helper import update_balances_transaction,validate_usernames,process_transaction_data
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified


bp = Blueprint('transactions', __name__)

@bp.route('/group/<int:group_id>/transaction', methods=['POST'])
def add_transaction(group_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({"message": "Group not found"}), 404
        
        data = request.get_json()
        if not validate_usernames(group, data):
            return jsonify({"message": "Invalid username(s) in the transaction"}), 400

        # Validate that the total amount paid matches the transaction amount
        total_paid = sum(payer['amount'] for payer in data['paid_by'])
        total_shared = sum(share['amount'] for share in data['share_details'])
        if total_paid != data['amount'] or total_shared != data['amount']:
            return jsonify({"message": "Total amount paid or shared does not match the transaction amount"}), 400

        transaction_data = process_transaction_data(data)
        transaction = Transaction(group_id=group_id, **transaction_data)
        db.session.add(transaction)

        updated_balances = update_balances_transaction(group.balances or {}, transaction, 'add')
        group.balances = updated_balances
        flag_modified(group,"balances")
        db.session.commit()

        return jsonify({"message": "Transaction added", "transaction": transaction.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@bp.route('/group/<int:group_id>/transaction/<int:transaction_id>', methods=['PUT'])
def update_transaction(group_id, transaction_id):
    try:
        group = Group.query.get(group_id)
        transaction = Transaction.query.filter_by(id=transaction_id, group_id=group_id).first()
        if not group or not transaction:
            return jsonify({"message": "Group or Transaction not found"}), 404

        data = request.get_json()
        
        # Check if only datetime or is_saved is being updated
        if set(data.keys()).issubset({'datetime_transaction', 'is_saved','description'}):
            if 'datetime_transaction' in data:
                transaction.datetime_transaction = data['datetime_transaction']
            if 'is_saved' in data:
                transaction.is_saved = data['is_saved']
            if 'description' in data:
                transaction.description=data['description']
            
            db.session.commit()
    
            return jsonify({"message": "Transaction updated"}), 200

        # For other updates, proceed with full validation
        if not validate_usernames(group, data):
            return jsonify({"message": "Invalid username(s) in the transaction update"}), 400

        old_share_details = transaction.share_details
        old_paid_by = transaction.paid_by
        
        new_amount = data.get('amount', transaction.amount)
        new_paid_by = data.get('paid_by', transaction.paid_by)
        new_share_details = data.get('share_details', transaction.share_details)
        
        total_paid = sum(payer['amount'] for payer in new_paid_by)
        total_shared = sum(share['amount'] for share in new_share_details)
        
        if total_paid != new_amount or total_shared != new_amount:
            return jsonify({"message": "Total amount paid or shared does not match the transaction amount"}), 400

        updated_data = process_transaction_data(data, transaction)
        for key, value in updated_data.items():
            if value is not None:  # Only update fields that are provided
                setattr(transaction, key, value)


        updated_balances = update_balances_transaction(group.balances or {}, transaction, 'update', old_share_details, old_paid_by)
        group.balances = updated_balances
        flag_modified(group,"balances")
        db.session.commit()

        return jsonify({"message": "Transaction updated", "transaction": transaction.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500
    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500

@bp.route('/group/<int:group_id>/transaction/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(group_id, transaction_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({"message": "Group not found"}), 404 
        transaction = Transaction.query.filter_by(id=transaction_id, group_id=group_id).first()
        if not transaction:
            return jsonify({"message": "Transaction not found"}), 404

        db.session.delete(transaction)

        updated_balances = update_balances_transaction(group.balances or {}, transaction, 'delete')

        group.balances = updated_balances
        flag_modified(group,"balances")
        db.session.commit()

        return jsonify({"message": "Transaction deleted", "transaction": transaction.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500

@bp.route('/group/<int:group_id>/transaction/<int:transaction_id>', methods=['GET'])
def get_transaction(group_id, transaction_id):
    group=Group.query.get(group_id)
    if not group:
        return jsonify({"message": "Group not found"}), 404
    transaction=Transaction.query.filter_by(id=transaction_id,group_id=group_id).first()
    if not transaction:
        return jsonify({"message": "Transaction not found"}), 404
    return jsonify({"transaction":transaction.to_dict()}),200