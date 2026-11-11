import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, EmailField, PasswordField, StringField, SubmitField
from wtforms.validators import Email, EqualTo, Length, Regexp, ValidationError, DataRequired

from app.models import User


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(r"^[A-Za-z0-9_.-]+$", message="Use letters, numbers, dots, dashes, or underscores."),
        ],
    )
    email = EmailField("Email address", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm_password = PasswordField(
        "Confirm password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Create account")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("That username is already in use.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account already uses that email.")

    def validate_password(self, field):
        if not re.search(r"[A-Za-z]", field.data) or not re.search(r"\d", field.data):
            raise ValidationError("Use at least one letter and one number.")


class LoginForm(FlaskForm):
    email = EmailField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=10, max=128)])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Update password")

    def validate_new_password(self, field):
        if not re.search(r"[A-Za-z]", field.data) or not re.search(r"\d", field.data):
            raise ValidationError("Use at least one letter and one number.")
