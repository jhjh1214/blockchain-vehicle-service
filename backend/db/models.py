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

    # Brand the account is authorised for (required for MANUFACTURER / authorized SERVICE_CENTER)
    brand  = db.Column(db.String(100), nullable=True)

    # Malaysian SSM company registration number (required for manufacturers; also stored for SCs)
    ssm_number = db.Column(db.String(50), nullable=True, index=True)

    # Service center profile
    city   = db.Column(db.String(100))
    state  = db.Column(db.String(100))
    # active | pending | suspended  (manufacturers/owners always active)
    status = db.Column(db.String(20), default='active', nullable=False)

    # Account lockout
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    # PDPA consent — timestamp user accepted Privacy Policy & Terms at registration
    consent_given_at = db.Column(db.DateTime, nullable=True)

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    theme_preference = db.Column(db.String(10), default='light', nullable=False)

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
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
            'consent_given_at': (self.consent_given_at.isoformat() + 'Z') if self.consent_given_at else None,
            'email_verified': self.email_verified,
            'theme_preference': self.theme_preference or 'light',
            'ssm_number': self.ssm_number,
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
    ecu_modules = db.Column(db.JSON, nullable=True)
    sc_brand = db.Column(db.String(100), nullable=True)  # null = independent/external workshop
    # 'ok' | 'tampered' | None (unverified — never reconciled)
    integrity_status = db.Column(db.String(20), nullable=True)
    integrity_checked_at = db.Column(db.DateTime, nullable=True)
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
            'service_date': (self.service_date.isoformat() + 'Z') if self.service_date else None,
            'mileage': self.mileage,
            'parts_replaced': self.parts_replaced,
            'technician_name': self.technician_name,
            'service_notes': self.service_notes,
            'photos': self.photos,
            'sc_brand': self.sc_brand,
            'integrity_status': self.integrity_status,
            'disputed': self.disputed,
            'escalated': self.escalated,
            'escalated_at': (self.escalated_at.isoformat() + 'Z') if self.escalated_at else None,
            'resolution_decision': self.resolution_decision,
            'resolution_notes': self.resolution_notes,
            'resolved_at': (self.resolved_at.isoformat() + 'Z') if self.resolved_at else None,
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
            'approved_at': (self.approved_at.isoformat() + 'Z') if self.approved_at else None,
            'approved_notes': self.approved_notes,
            'created_at': self.created_at.isoformat() + 'Z'
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
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'warranty_expiry': self.warranty_expiry,
            'created_at': self.created_at.isoformat() + 'Z'
        }


class DisputeMessage(db.Model):
    __tablename__ = 'dispute_messages'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    record_index = db.Column(db.Integer, nullable=False)
    # SET NULL so message records survive user deletion; message content is anonymised
    # in delete_account() to satisfy PDPA while preserving the dispute audit trail.
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    sender_name = db.Column(db.String(255), nullable=True)   # snapshot at creation
    sender_role = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref=db.backref('dispute_messages', lazy=True))

    __table_args__ = (
        db.Index('ix_dispute_msg_vin_idx', 'vin', 'record_index'),
    )

    def to_dict(self) -> dict:
        name = self.sender_name or (self.sender.name if self.sender else 'Deleted User')
        return {
            'id': self.id,
            'vin': self.vin,
            'record_index': self.record_index,
            'sender_id': self.sender_id,
            'sender_name': name,
            'sender_role': self.sender_role,
            'message': self.message,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
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


class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('verification_tokens', lazy=True, cascade='all, delete-orphan'))

    @staticmethod
    def generate() -> str:
        return secrets.token_urlsafe(48)

    def is_valid(self) -> bool:
        return self.expires_at > datetime.utcnow()


class AuthorizedSCLicense(db.Model):
    __tablename__ = 'authorized_sc_licenses'

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ssm_number = db.Column(db.String(50), nullable=False, index=True)
    sc_name = db.Column(db.String(255), nullable=True)
    brand = db.Column(db.String(100), nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    manufacturer = db.relationship('User', backref=db.backref('authorized_sc_licenses', lazy=True, cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('ssm_number', name='uq_authorized_ssm'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'ssm_number': self.ssm_number,
            'sc_name': self.sc_name,
            'brand': self.brand,
            'used': self.used,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }


class EthFundRequest(db.Model):
    __tablename__ = 'eth_fund_requests'

    id = db.Column(db.Integer, primary_key=True)
    sc_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    brand = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending | fulfilled | dismissed
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fulfilled_at = db.Column(db.DateTime, nullable=True)

    sc = db.relationship('User', backref=db.backref('eth_requests', lazy=True, cascade='all, delete-orphan'))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'sc_user_id': self.sc_user_id,
            'sc_name': self.sc.name if self.sc else None,
            'sc_email': self.sc.email if self.sc else None,
            'sc_id': self.sc.id if self.sc else None,
            'brand': self.brand,
            'status': self.status,
            'notes': self.notes,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
            'fulfilled_at': (self.fulfilled_at.isoformat() + 'Z') if self.fulfilled_at else None,
        }


class VehicleRecall(db.Model):
    __tablename__ = 'vehicle_recalls'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(100), nullable=False, index=True)
    issued_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    affected_models = db.Column(db.JSON, nullable=True)  # null = all models of brand
    vin_range_start = db.Column(db.String(17), nullable=True)  # null = no VIN range restriction
    vin_range_end   = db.Column(db.String(17), nullable=True)
    status = db.Column(db.String(20), default='active', nullable=False)  # active | closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    issued_by = db.relationship('User', backref=db.backref('recalls_issued', lazy=True))

    def is_vin_affected(self, vin: str) -> bool:
        """Return True if the given VIN falls within this recall's range (or no range set)."""
        if not self.vin_range_start or not self.vin_range_end:
            return True
        return self.vin_range_start.upper() <= vin.upper() <= self.vin_range_end.upper()

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'brand': self.brand,
            'issued_by': self.issued_by.name if self.issued_by else None,
            'title': self.title,
            'description': self.description,
            'affected_models': self.affected_models,
            'vin_range_start': self.vin_range_start,
            'vin_range_end': self.vin_range_end,
            'status': self.status,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }


class RecallVINService(db.Model):
    __tablename__ = 'recall_vin_services'

    id = db.Column(db.Integer, primary_key=True)
    recall_id = db.Column(db.Integer, db.ForeignKey('vehicle_recalls.id', ondelete='CASCADE'), nullable=False)
    vin = db.Column(db.String(17), nullable=False)
    sc_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    serviced_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    recall = db.relationship('VehicleRecall', backref=db.backref('vin_services', lazy=True, cascade='all, delete-orphan'))
    sc = db.relationship('User', backref=db.backref('recall_services', lazy=True))

    __table_args__ = (
        db.UniqueConstraint('recall_id', 'vin', name='uq_recall_vin'),
    )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'recall_id': self.recall_id,
            'vin': self.vin,
            'sc_name': self.sc.name if self.sc else None,
            'serviced_at': (self.serviced_at.isoformat() + 'Z') if self.serviced_at else None,
            'notes': self.notes,
        }


class WarrantyVoidRequest(db.Model):
    __tablename__ = 'warranty_void_requests'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    sc_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reason = db.Column(db.Text, nullable=False)
    mileage_submitted = db.Column(db.Integer, nullable=True)
    last_authorized_mileage = db.Column(db.Integer, nullable=True)
    # pending | approved | denied | disputed
    status = db.Column(db.String(20), default='pending', nullable=False)
    manufacturer_notes = db.Column(db.Text, nullable=True)
    owner_dispute_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)

    sc = db.relationship('User', backref=db.backref('void_requests', lazy=True))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'sc_name': self.sc.name if self.sc else None,
            'sc_email': self.sc.email if self.sc else None,
            'sc_brand': self.sc.brand if self.sc else None,
            'reason': self.reason,
            'mileage_submitted': self.mileage_submitted,
            'last_authorized_mileage': self.last_authorized_mileage,
            'status': self.status,
            'manufacturer_notes': self.manufacturer_notes,
            'owner_dispute_reason': self.owner_dispute_reason,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
            'resolved_at': (self.resolved_at.isoformat() + 'Z') if self.resolved_at else None,
        }


class AbuseReport(db.Model):
    __tablename__ = 'abuse_reports'

    id = db.Column(db.Integer, primary_key=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reporter_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reporter_role = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    # spam | fake_service | harassment | other
    category = db.Column(db.String(30), default='other', nullable=False)
    vin = db.Column(db.String(17), nullable=True)  # relevant VIN if any
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reported = db.relationship('User', foreign_keys=[reported_user_id],
                               backref=db.backref('reports_against', lazy=True))
    reporter = db.relationship('User', foreign_keys=[reporter_user_id],
                               backref=db.backref('reports_filed', lazy=True))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'reported_user_id': self.reported_user_id,
            'reported_name': self.reported.name if self.reported else None,
            'reported_email': self.reported.email if self.reported else None,
            'reporter_role': self.reporter_role,
            'reason': self.reason,
            'category': self.category,
            'vin': self.vin,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    data = db.Column(db.JSON, nullable=True)
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'type': self.type,
            'data': self.data,
            'read': self.read,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }


class VehicleReclaimRequest(db.Model):
    __tablename__ = 'vehicle_reclaim_requests'

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), db.ForeignKey('vehicle_vin_mapping.vin', ondelete='CASCADE'), nullable=False, index=True)
    requester_address = db.Column(db.String(42), nullable=False)
    requester_email = db.Column(db.String(255), nullable=True)
    # pending | approved | rejected
    status = db.Column(db.String(20), default='pending', nullable=False)
    reviewer_address = db.Column(db.String(42), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'vin': self.vin,
            'requester_address': self.requester_address,
            'requester_email': self.requester_email,
            'status': self.status,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
            'reviewed_at': (self.reviewed_at.isoformat() + 'Z') if self.reviewed_at else None,
        }


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
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }
