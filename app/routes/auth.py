import secrets
import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app import db, bcrypt, mail
from app.models import User, AuditLog

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def _log(action, user_id=None):
    db.session.add(AuditLog(action=action, user_id=user_id, ip_address=_get_ip()))
    db.session.commit()


def _send_email(to, subject, html_body):
    msg = Message(subject, recipients=[to], html=html_body)
    mail.send(msg)


# ── REGISTER ─────────────────────────────────────────────────

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Validation
        errors = []
        if len(name) < 2:
            errors.append("Name must be at least 2 characters.")
        if "@" not in email or "." not in email:
            errors.append("Enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("signup.html", name=name, email=email)

        # Create user
        token = secrets.token_urlsafe(32)
        user = User(
            name=name,
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            verification_token=token,
        )
        db.session.add(user)
        db.session.commit()
        _log("register", user.id)

        # Send verification email
        verify_url = url_for("auth.verify_email", token=token, _external=True)
        html = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;
                    background:#0D1117;color:#E5E7EB;padding:40px;border-radius:12px;">
          <h1 style="color:#7C3AED;text-align:center;margin-bottom:24px;">🔐 ResumeVault</h1>
          <h2>Hi {name}, welcome!</h2>
          <p style="color:#9CA3AF;line-height:1.7;margin:16px 0;">
            Please verify your email to activate your account.
          </p>
          <div style="text-align:center;margin:32px 0;">
            <a href="{verify_url}"
               style="background:linear-gradient(135deg,#7C3AED,#06B6D4);color:white;
                      padding:14px 32px;border-radius:8px;text-decoration:none;
                      font-weight:600;font-size:16px;">
              Verify Email Address
            </a>
          </div>
          <p style="color:#6B7280;font-size:12px;text-align:center;">
            Link expires in 24 hours. Ignore if you did not create an account.
          </p>
        </div>"""
        try:
            _send_email(email, "Verify your ResumeVault email", html)
        except Exception as e:
            import traceback
            print(f"[EMAIL ERROR] Failed to send verification email to {email}: {e}")
            traceback.print_exc()

        # Auto-login the new user and redirect to landing page
        login_user(user)
        flash(f"Welcome to ResumeVault, {name.split()[0]}! 🎉 Check your email to verify your account.", "success")
        return redirect(url_for("main.index"))

    return render_template("signup.html", name="", email="")


# ── LOGIN ─────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()
        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            _log("login_failed")
            flash("Invalid email or password.", "error")
            return render_template("login.html", email=email)

        login_user(user, remember=remember)
        _log("login", user.id)
        flash(f"Welcome back, {user.name.split()[0]}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("login.html", email="")


# ── LOGOUT ────────────────────────────────────────────────────

@auth_bp.route("/logout")
@login_required
def logout():
    _log("logout", current_user.id)
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


# ── VERIFY EMAIL ──────────────────────────────────────────────

@auth_bp.route("/verify-email/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if not user:
        flash("Invalid or expired verification link. If you resent the email, please make sure you are clicking the link in the most recent email.", "error")
        return redirect(url_for("auth.login"))

    user.is_verified = True
    user.verification_token = None
    db.session.commit()
    _log("email_verified", user.id)
    
    # Auto-login the user on the browser/device where they clicked the link
    login_user(user)
    
    flash("✅ Email verified! Your account is now fully active.", "success")
    return redirect(url_for("main.dashboard"))


# ── RESEND VERIFICATION EMAIL ─────────────────────────────────

@auth_bp.route("/resend-verification", methods=["POST"])
@login_required
def resend_verification():
    # Load a real SQLAlchemy instance (not the Flask-Login proxy)
    user = User.query.get(current_user.id)

    if not user:
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    if user.is_verified:
        flash("Your email is already verified.", "info")
        return redirect(url_for("main.profile"))

    try:
        token = secrets.token_urlsafe(32)
        user.verification_token = token
        db.session.commit()

        first_name = (user.name or "there").split()[0]
        verify_url = url_for("auth.verify_email", token=token, _external=True)
        html = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;
                    background:#0D1117;color:#E5E7EB;padding:40px;border-radius:12px;">
          <h1 style="color:#7C3AED;text-align:center;margin-bottom:24px;">&#128272; ResumeVault</h1>
          <h2>Verify your email, {first_name}!</h2>
          <p style="color:#9CA3AF;line-height:1.7;margin:16px 0;">
            Click the button below to verify your email address and unlock full access.
          </p>
          <div style="text-align:center;margin:32px 0;">
            <a href="{verify_url}"
               style="background:linear-gradient(135deg,#7C3AED,#06B6D4);color:white;
                      padding:14px 32px;border-radius:8px;text-decoration:none;
                      font-weight:600;font-size:16px;">
              Verify Email Address
            </a>
          </div>
          <p style="color:#6B7280;font-size:12px;text-align:center;">
            This link is valid for 24 hours. Ignore if you did not request this.
          </p>
        </div>"""

        _send_email(user.email, "Verify your ResumeVault email", html)
        flash("✅ Verification email sent! Check your inbox (and spam folder).", "success")

    except Exception as e:
        import traceback
        db.session.rollback()
        print(f"[RESEND VERIFY ERROR] {e}")
        traceback.print_exc()
        flash("⚠️ Could not send verification email. Please check your email settings in Render.", "error")

    return redirect(url_for("main.profile"))


# ── FORGOT PASSWORD ───────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            db.session.commit()

            # Send reset email
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            html = f"""
            <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;
                        background:#0D1117;color:#E5E7EB;padding:40px;border-radius:12px;">
              <h1 style="color:#7C3AED;text-align:center;margin-bottom:24px;">🔐 ResumeVault</h1>
              <h2>Password Reset</h2>
              <p style="color:#9CA3AF;line-height:1.7;margin:16px 0;">
                Hi {user.name}, click below to reset your password.
              </p>
              <div style="text-align:center;margin:32px 0;">
                <a href="{reset_url}"
                   style="background:linear-gradient(135deg,#7C3AED,#06B6D4);color:white;
                          padding:14px 32px;border-radius:8px;text-decoration:none;
                          font-weight:600;font-size:16px;">
                  Reset Password
                </a>
              </div>
              <p style="color:#6B7280;font-size:12px;text-align:center;">
                This link expires in 1 hour.
              </p>
            </div>"""
            try:
                _send_email(email, "Reset your ResumeVault password", html)
            except Exception as e:
                import traceback
                print(f"[EMAIL ERROR] Failed to send reset email to {email}: {e}")
                traceback.print_exc()

        # Always show same message (prevent user enumeration)
        flash("If that email is registered, you'll receive a reset link shortly.", "success")
        return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")


# ── RESET PASSWORD ────────────────────────────────────────────

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        flash("Invalid or expired reset link.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("reset_password.html", token=token)
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html", token=token)

        user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        user.reset_token = None
        db.session.commit()
        _log("password_reset", user.id)
        flash("Password reset successfully! Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", token=token)
