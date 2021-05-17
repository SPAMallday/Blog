from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired


class EditPost(FlaskForm):
    title = StringField(label="Title", validators=[DataRequired()])
    subtitle = StringField(label="Description", validators=[DataRequired()])
    submit = SubmitField(label="Submit")


class NewCategory(FlaskForm):
    name = StringField(label="Name", validators=[DataRequired()])
    submit = SubmitField(label="Submit")


class LoginForm(FlaskForm):
    password = PasswordField(label="Password", validators=[DataRequired()])
    submit = SubmitField(label="LOGIN!")
