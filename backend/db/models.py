from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    blockchain_address = db.Column(db.String(42), unique=True, nullable=False)
    name = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'blockchain_address': self.blockchain_address
        }


class ServiceMetadata(db.Model):
    __tablename__ = 'service_metadata'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False)
    metadata_hash = db.Column(db.String(66), nullable=False)
    service_type = db.Column(db.String(100))
    service_date = db.Column(db.DateTime)
    mileage = db.Column(db.Integer)
    parts_replaced = db.Column(db.Text)
    technician_name = db.Column(db.String(255))
    service_notes = db.Column(db.Text)
    photos = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'metadata_hash': self.metadata_hash,
            'service_type': self.service_type,
            'service_date': self.service_date.isoformat() if self.service_date else None,
            'mileage': self.mileage,
            'parts_replaced': self.parts_replaced,
            'technician_name': self.technician_name,
            'service_notes': self.service_notes,
            'photos': self.photos
        }


class WarrantyClaimMetadata(db.Model):
    __tablename__ = 'warranty_claim_metadata'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False)
    claim_hash = db.Column(db.String(66), nullable=False, unique=True)
    issue_description = db.Column(db.Text)
    photos = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'claim_hash': self.claim_hash,
            'issue_description': self.issue_description,
            'photos': self.photos,
            'created_at': self.created_at.isoformat()
        }


class VehicleVINMapping(db.Model):
    __tablename__ = 'vehicle_vin_mapping'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), unique=True, nullable=False, index=True)
    vin_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)
    owner_address = db.Column(db.String(42), nullable=False, index=True)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'vin': self.vin,
            'vin_hash': self.vin_hash,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'created_at': self.created_at.isoformat()
        }
