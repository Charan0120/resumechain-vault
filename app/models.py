import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(512), nullable=True)
    reset_token = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    resumes = db.relationship("Resume", backref="owner", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    s3_key = db.Column(db.String(1000), nullable=False, unique=True)
    file_size = db.Column(db.Integer, nullable=False)          # bytes
    file_hash = db.Column(db.String(64), nullable=False)       # SHA-256 hex
    content_type = db.Column(db.String(100), nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def size_display(self):
        """Human-readable file size."""
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        return f"{kb / 1024:.1f} MB"

    def __repr__(self):
        return f"<Resume {self.original_filename}>"


class ShareLink(db.Model):
    __tablename__ = "share_links"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    resume_id = db.Column(db.String(36), db.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    resume = db.relationship("Resume", backref="share_links")

    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    def expiry_display(self):
        """Human-readable time remaining."""
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        exp = self.expires_at.replace(tzinfo=timezone.utc)
        if now > exp:
            return "Expired"
        diff = exp - now
        hours = int(diff.total_seconds() // 3600)
        mins  = int((diff.total_seconds() % 3600) // 60)
        if hours >= 24:
            return f"{hours // 24}d remaining"
        if hours > 0:
            return f"{hours}h {mins}m remaining"
        return f"{mins}m remaining"

    def __repr__(self):
        return f"<ShareLink {self.token[:8]}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
