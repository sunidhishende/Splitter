from backend.db import db
from datetime import datetime
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
class Transaction(db.Model):
    __tablename__ = 'transactions'
    __table_args__ = (db.Index('ix_transactions_group_id_datetime', 'group_id', 'datetime_transaction', postgresql_ops={'datetime_transaction': 'DESC'}),
                      CheckConstraint('amount > 0', name='check_amount_positive'),)
    id = db.Column(db.Integer, primary_key=True) 
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False) 
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False) 
    paid_by = db.Column(JSONB) #JSON array of usernames 
    mode= db.Column(db.Text) 
    paid_for = db.Column(JSONB)  # JSON array of usernames
    share_details = db.Column(JSONB)  # JSON array of (username, amount)
    datetime_transaction = db.Column(db.TIMESTAMP(timezone=True), nullable=False, default=datetime.now()) 
    is_saved = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Transaction {self.id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'group_id': self.group_id,
            'description': self.description,
            'amount': self.amount,
            'paid_by': self.paid_by,
            'mode': self.mode,
            'paid_for': self.paid_for,
            'share_details': self.share_details,
            'datetime_transaction': self.datetime_transaction.isoformat(),
            'is_saved': self.is_saved
        }
