from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import bcrypt
import secrets

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

    # Brand the account is authorised for (required for MANUFACTURER / SERVICE_CENTER)
    brand  = db.Column(db.String(100), nullable=True)

    # Service center profile
    city   = db.Column(db.String(100))
    state  = db.Column(db.String(100))
    # active | pending | suspended  (manufacturers/owners always active)
    status = db.Column(db.String(20), default='active', nullable=False)

    # Account lockout
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str):
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def is_locked(self) -> bool:
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'phone': self.phone,
            'city': self.city,
            'state': self.state,
            'brand': self.brand,
            'status': self.status,
            'blockchain_address': self.blockchain_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True, cascade='all, delete-orphan'))

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(48)

    def is_valid(self) -> bool:
        return not self.revoked and self.expires_at > datetime.utcnow()


class DeviceToken(db.Model):
    __tablename__ = 'device_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = db.Column(db.String(512), nullable=False)
    platform = db.Column(db.String(10), nullable=False)  # 'ios' | 'android'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('device_tokens', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'platform', name='uq_device_user_platform'),
    )


class ServiceMetadata(db.Model):
    __tablename__ = 'service_metadata'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    metadata_hash = db.Column(db.String(66), nullable=False, index=True)
    service_center_address = db.Column(db.String(42), nullable=True, index=True)
    service_type = db.Column(db.String(100))
    service_date = db.Column(db.DateTime)
    mileage = db.Column(db.Integer)
    parts_replaced = db.Column(db.Text)
    technician_name = db.Column(db.String(255))
    service_notes = db.Column(db.Text)
    photos = db.Column(db.JSON)
    disputed = db.Column(db.Boolean, default=False, nullable=False)
    rebuttal_notes = db.Column(db.Text, nullable=True)
    rebuttal_submitted_at = db.Column(db.DateTime, nullable=True)
    resolution_decision = db.Column(db.String(20), nullable=True)  # approved | rejected | modified
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    escalated = db.Column(db.Boolean, default=False, nullable=False)
    escalated_at = db.Column(db.DateTime, nullable=True)
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
            'photos': self.photos,
            'disputed': self.disputed,
            'escalated': self.escalated,
            'escalated_at': self.escalated_at.isoformat() if self.escalated_at else None,
            'resolution_decision': self.resolution_decision,
            'resolution_notes': self.resolution_notes,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
        }


class WarrantyClaimMetadata(db.Model):
    __tablename__ = 'warranty_claim_metadata'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False)
    claim_hash = db.Column(db.String(66), nullable=False, unique=True)
    issue_description = db.Column(db.Text)
    photos = db.Column(db.JSON)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending | approved | denied
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'claim_hash': self.claim_hash,
            'issue_description': self.issue_description,
            'photos': self.photos,
            'status': self.status,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_notes': self.approved_notes,
            'created_at': self.created_at.isoformat()
        }


class VehicleVINMapping(db.Model):
    __tablename__ = 'vehicle_vin_mapping'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), unique=True, nullable=False, index=True)
    vin_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)
    owner_address = db.Column(db.String(42), nullable=False, index=True)
    registered_by = db.Column(db.String(42), nullable=True, index=True)
    registration_status = db.Column(db.String(20), default='active', nullable=False)
    # Email reserved by manufacturer for pending pre-registrations; if set, only this user can claim
    intended_owner_email = db.Column(db.String(255), nullable=True)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    warranty_expiry = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            'vin': self.vin,
            'vin_hash': self.vin_hash,
            'owner_address': self.owner_address,
            'registered_by': self.registered_by,
            'registration_status': self.registration_status,
            'intended_owner_email': self.intended_owner_email,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'warranty_expiry': self.warranty_expiry,
            'created_at': self.created_at.isoformat()
        }


class DisputeMessage(db.Model):
    __tablename__ = 'dispute_messages'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    record_index = db.Column(db.Integer, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    sender_role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref=db.backref('dispute_messages', lazy=True))

    __table_args__ = (
        db.Index('ix_dispute_msg_vin_idx', 'vin', 'record_index'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'record_index': self.record_index,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name if self.sender else 'Unknown',
            'sender_role': self.sender_role,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True, cascade='all, delete-orphan'))

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(48)

    def is_valid(self) -> bool:
        return not self.used and self.expires_at > datetime.utcnow()


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    # Who performed the action (None = unauthenticated / anonymous)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    event = db.Column(db.String(64), nullable=False, index=True)
    # free-form JSON blob: VIN, IP, extra context
    detail = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'event': self.event,
            'detail': self.detail,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
