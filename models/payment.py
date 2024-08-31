from backend.db import db
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB

class Payment(db.Model):
    __tablename__ = 'payments'
    __table_args__ = (db.Index('ix_payments_group_id_datetime', 'group_id', 'datetime_payment', postgresql_ops={'datetime_payment': 'DESC'}),
                      CheckConstraint('amount > 0', name='check_amount_positive'),)
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_from = db.Column(JSONB, nullable=False)
    paid_to = db.Column(JSONB, nullable=False)
    datetime_payment = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=datetime.now())
    

    def __repr__(self):
        return f"<Payment {self.id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'amount': self.amount,
            'paid_from': self.paid_from,
            'paid_to': self.paid_to,
            'datetime_payment': self.datetime_payment.isoformat(),
        }
