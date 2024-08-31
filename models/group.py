from backend.db import db
from sqlalchemy.dialects.postgresql import JSONB

class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name= db.Column(db.Text, nullable=False)
    usernames = db.Column(JSONB, nullable=False)  # JSON array of (username, upi_id)
    balances = db.Column(JSONB, default=dict)  # JSON object to store user balances
    transactions = db.relationship('Transaction', backref='group', lazy='dynamic')
    payments=db.relationship('Payment', backref='group', lazy='dynamic')

    def __repr__(self):
        return f"<Group {self.id}>"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'usernames': self.usernames,
            'balances': self.balances
        }
