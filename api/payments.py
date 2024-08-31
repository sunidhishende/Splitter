from flask import Blueprint, request, jsonify
from backend.db import db
from backend.websocket import socketio
from backend.models.payment import Payment
from backend.models.group import Group
from datetime import datetime
from backend.helper.helper import update_balances_payment, settle_up, validate_usernames,process_payment_data
from flask_socketio import emit
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.attributes import flag_modified

bp = Blueprint('payments', __name__)

@bp.route('/group/<int:group_id>/payment', methods=['POST'])
def add_payment(group_id):
    try:
        group = Group.query.get(group_id)
        if not group:
            return jsonify({"message": "Group not found"}), 404
        
        try:
            data = request.get_json()
        except ValueError:
            return jsonify({"message": "Invalid JSON input"}), 400
        
        if not validate_usernames(group, data):
            return jsonify({"message": "Invalid username(s) in the transaction"}), 400

        payment_data = process_payment_data(data) 
        payment = Payment(group_id=group_id, **payment_data)
        db.session.add(payment)

        # Update balances and get new settlements
        updated_balances = update_balances_payment(group.balances or {}, payment, 'add')

        # Update the group with new balances and commit
        group.balances = updated_balances
        flag_modified(group, "balances")
        db.session.commit()

        return jsonify({"message": "Payment added", "payment": payment.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@bp.route('/group/<int:group_id>/payment/<int:payment_id>', methods=['PUT'])
def update_payment(group_id, payment_id):
    try:
        group = Group.query.get(group_id)
        payment = Payment.query.filter_by(id=payment_id, group_id=group_id).first()

        if not group or not payment:
            return jsonify({"message": "Group or Payment not found"}), 404
        
        old_paid_from = payment.paid_from
        old_paid_to = payment.paid_to
        old_payment_amount = payment.amount

        try:
            data = request.get_json()
        except ValueError:
            return jsonify({"message": "Invalid JSON input"}), 400

        if not validate_usernames(group, data):
            return jsonify({"message": "Invalid username(s) in the transaction"}), 400
        
        updated_data= process_payment_data(data,payment)
        for key, value in updated_data.items():
            if value is not None:  
                setattr(payment, key, value)

        # Update balances and get new settlements
        updated_balances = update_balances_payment(group.balances or {}, payment, 'update', old_paid_from, old_paid_to, old_payment_amount)

        # Update the group with new balances and commit
        group.balances = updated_balances
        flag_modified(group,"balances")
        db.session.commit()

        return jsonify({"message": "Payment updated", "payment": payment.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500


@bp.route('/group/<int:group_id>/payment/<int:payment_id>', methods=['DELETE'])
def delete_payment(group_id, payment_id):
    try:
        group = Group.query.get(group_id)
        payment = Payment.query.filter_by(id=payment_id, group_id=group_id).first()

        if not group or not payment:
            return jsonify({"message": "Group or Payment not found"}), 404

        db.session.delete(payment)

        # Update balances and get new settlements
        updated_balances = update_balances_payment(group.balances or {}, payment, 'delete')

        # Update the group with new balances and commit
        group.balances = updated_balances
        flag_modified(group,"balances")
        db.session.commit()

        return jsonify({"message": "Payment deleted", "payment": payment.to_dict()}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500

    except Exception as e:
        return jsonify({"message": "An unexpected error occurred", "error": str(e)}), 500

@bp.route('/group/<int:group_id>/payment/<int:payment_id>', methods=['GET'])
def get_payment(group_id, payment_id):
    group=Group.query.get(group_id)
    if not group:
        return jsonify({"message": "Group not found"}), 404
    payment=Payment.query.filter_by(id=payment_id,group_id=group_id).first()
    if not payment:
        return jsonify({"message": "Payment not found"}), 404
    return jsonify({"payment":payment.to_dict()}),200