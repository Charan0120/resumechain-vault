import secrets
import io
from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, send_file
from flask_login import login_required, current_user
from botocore.exceptions import ClientError

from app import db
from app.models import Resume, AuditLog, ShareLink
from app.services.s3_service import upload_resume, stream_file, delete_resume

main_bp = Blueprint("main", __name__)


def _log(action, user_id=None):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    db.session.add(AuditLog(action=action, user_id=user_id, ip_address=ip))
    db.session.commit()


# ── Landing Page ───────────────────────────────────────────────

@main_bp.route("/")
def index():
    return render_template("index.html")


# ── Dashboard ──────────────────────────────────────────────────

@main_bp.route("/dashboard")
@login_required
def dashboard():
    resumes = (
        Resume.query
        .filter_by(user_id=current_user.id)
        .order_by(Resume.uploaded_at.desc())
        .all()
    )
    return render_template("dashboard.html", user=current_user, resumes=resumes)


# ── Upload Resume ──────────────────────────────────────────────

@main_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    if "resume" not in request.files:
        flash("No file selected.", "error")
        return redirect(url_for("main.dashboard"))

    file = request.files["resume"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("main.dashboard"))

    try:
        result = upload_resume(file, current_user.id)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("main.dashboard"))
    except ClientError as e:
        flash("Cloud upload failed. Check your AWS credentials and bucket name.", "error")
        return redirect(url_for("main.dashboard"))

    # Count existing versions of this filename for this user
    same_name_count = Resume.query.filter_by(
        user_id=current_user.id,
        original_filename=result["original_filename"]
    ).count()

    resume = Resume(
        user_id=current_user.id,
        original_filename=result["original_filename"],
        s3_key=result["s3_key"],
        file_size=result["file_size"],
        file_hash=result["file_hash"],
        content_type=result["content_type"],
        version=same_name_count + 1,
    )
    db.session.add(resume)
    db.session.commit()

    _log("resume_upload", current_user.id)
    flash(f'"{result["original_filename"]}" uploaded and encrypted successfully! 🔒', "success")
    return redirect(url_for("main.dashboard"))


# ── Download Resume ────────────────────────────────────────────

@main_bp.route("/resume/<resume_id>/download")
@login_required
def download_resume(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()

    try:
        file_bytes = stream_file(resume.s3_key)
    except ClientError:
        flash("Could not download file from cloud. Please try again.", "error")
        return redirect(url_for("main.dashboard"))

    _log("resume_download", current_user.id)
    return send_file(
        io.BytesIO(file_bytes),
        download_name=resume.original_filename,
        as_attachment=True,
        mimetype=resume.content_type
    )


# ── Delete Resume ────────────────────────────────────────────

@main_bp.route("/resume/<resume_id>/delete", methods=["POST"])
@login_required
def delete_resume_route(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()
    filename = resume.original_filename  # save before session closes

    try:
        delete_resume(resume.s3_key)
    except ClientError:
        flash("Could not delete file from cloud. Please try again.", "error")
        return redirect(url_for("main.dashboard"))

    # Delete share links first at ORM level to avoid FK constraint errors
    from app.models import ShareLink
    ShareLink.query.filter_by(resume_id=resume.id).delete()
    db.session.delete(resume)
    db.session.commit()

    _log("resume_delete", current_user.id)
    flash(f'"{filename}" deleted successfully.', "info")
    return redirect(url_for("main.dashboard"))


# ── Create Share Link ──────────────────────────────────────────

EXPIRY_OPTIONS = {
    "15m":  timedelta(minutes=15),
    "1h":   timedelta(hours=1),
    "24h":  timedelta(hours=24),
    "7d":   timedelta(days=7),
}

@main_bp.route("/resume/<resume_id>/share", methods=["POST"])
@login_required
def create_share_link(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first_or_404()

    expiry_key = request.form.get("expiry", "1h")
    delta = EXPIRY_OPTIONS.get(expiry_key, timedelta(hours=1))
    expires_at = datetime.now(timezone.utc) + delta

    token = secrets.token_urlsafe(32)
    link = ShareLink(
        token=token,
        resume_id=resume.id,
        user_id=current_user.id,
        expires_at=expires_at,
    )
    db.session.add(link)
    db.session.commit()

    _log("share_link_created", current_user.id)
    share_url = url_for("main.access_share_link", token=token, _external=True)
    flash(f"Share link created! It expires in {expiry_key}. Copy it below. 🔗", "success")
    return redirect(url_for("main.dashboard", share_url=share_url))


# ── Public Share Link Access (no login required) ───────────────

@main_bp.route("/share/<token>")
def access_share_link(token):
    link = ShareLink.query.filter_by(token=token).first_or_404()

    if link.is_expired():
        return render_template("share_expired.html"), 410

    resume = link.resume
    try:
        file_bytes = stream_file(resume.s3_key)
    except ClientError:
        abort(500)

    # Track download
    link.download_count += 1
    db.session.commit()
    _log("share_link_accessed", link.user_id)

    return send_file(
        io.BytesIO(file_bytes),
        download_name=resume.original_filename,
        as_attachment=True,
        mimetype=resume.content_type
    )


# ── Delete Share Link ──────────────────────────────────────────

@main_bp.route("/share/<link_id>/delete", methods=["POST"])
@login_required
def delete_share_link(link_id):
    link = ShareLink.query.filter_by(id=link_id, user_id=current_user.id).first_or_404()
    db.session.delete(link)
    db.session.commit()
    flash("Share link revoked.", "info")
    return redirect(url_for("main.dashboard"))


# ══════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════

import functools
from flask import current_app
from app.models import User


def admin_required(f):
    """Decorator: only allows the ADMIN_EMAIL user through."""
    @functools.wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        admin_email = current_app.config.get("ADMIN_EMAIL", "")
        if not admin_email or current_user.email != admin_email:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@main_bp.route("/admin")
@admin_required
def admin_dashboard():
    users = User.query.order_by(User.created_at.desc()).all()

    # Build stats per user
    user_stats = []
    for user in users:
        resume_count = Resume.query.filter_by(user_id=user.id).count()
        last_action = (
            AuditLog.query
            .filter_by(user_id=user.id)
            .order_by(AuditLog.timestamp.desc())
            .first()
        )
        user_stats.append({
            "user": user,
            "resume_count": resume_count,
            "last_action": last_action,
        })

    return render_template("admin_dashboard.html", user_stats=user_stats)


@main_bp.route("/admin/delete/<user_id>", methods=["POST"])
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Delete all S3 files first
    resumes = Resume.query.filter_by(user_id=user.id).all()
    for resume in resumes:
        try:
            delete_resume(resume.s3_key)
        except ClientError:
            pass  # Log but don't block deletion

    # Cascade delete: share links → resumes → audit logs → user
    ShareLink.query.filter(
        ShareLink.resume_id.in_([r.id for r in resumes])
    ).delete(synchronize_session=False)
    Resume.query.filter_by(user_id=user.id).delete()
    AuditLog.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()

    flash(f"User {user.email} and all their data has been permanently deleted.", "info")
    return redirect(url_for("main.admin_dashboard"))
