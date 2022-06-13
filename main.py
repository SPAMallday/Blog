import datetime
import os

import psycopg2
from flask import Flask, render_template, request, redirect, url_for, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import relationship

from forms import EditPost, NewCategory, LoginForm


#To use PostgreSQL in Heroku (When URI starts with postgres will replace it to postgresql)
#flask doens't support postgres:// uri in this version

# only_uri = os.environ.get("DATABASE_URL", "sqlite:///my_data.db")
# connection = psycopg2.connect(only_uri, sslmode='require')

uri = os.environ.get("DATABASE_URL", "sqlite:///my_data.db")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("APP_SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)


# Composing DB
class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Date, nullable=False, default=datetime.datetime.today())

    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))
    category = relationship("Category", back_populates="posts")


class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), unique=True, nullable=False)
    count = db.Column(db.Integer, nullable=False)

    posts = relationship("Post", back_populates="category")

# Only admin
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(5), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)


# make User instance
# user = User()
# user.name = "######"
# user.password = generate_password_hash("######")
# db.session.add(user)
# db.session.commit()

# use once
db.create_all()


# define load_user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# variables for render templates (using it, i can transfer variable at once)
variable_dict = {"year": datetime.datetime.today().year,  # for copyright
                 "page": "",  # for navbar emphasis
                 "categories": Category.query.all(),  # for navbar dropdown content
                 "posts": "",  # for show posts by category
                 "selected_category_id": "",  # check category to show, count or edit post
                 "selected_category_name": "",  # to fill the certain category title
                 "selected_post": ""  # to show certain post
                 }


# for updating count column
def update_count(category_id):
    now_count = db.session.execute(Post.query.filter_by(category_id=category_id)
                                   .statement.with_only_columns([func.count()]).order_by(None)).scalar()
    target = Category.query.get(category_id)
    target.count = now_count
    db.session.commit()
    variable_dict["categories"] = Category.query.all()


# view function define
@app.route("/")
def home():
    variable_dict["page"] = "home"
    return render_template("index.html", variable_dict=variable_dict)


@app.route("/login", methods=["GET", "POST"])
def login_page():
    variable_dict["page"] = "login"
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.get("1")
        if check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("home"))
        else:
            return abort(403)
    return render_template("login.html", variable_dict=variable_dict, form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.route("/profile")
def show_profile():
    variable_dict["page"] = "profile"
    return render_template("profile.html", variable_dict=variable_dict)


@app.route("/posts")
def show_posts_by_category():
    variable_dict["page"] = "posts"
    target_category_id = request.args.get("category_id")
    variable_dict["selected_category_id"] = target_category_id
    variable_dict["selected_category_name"] = Category.query.get(target_category_id).name
    result = Post.query.filter_by(category_id=target_category_id).order_by(getattr(Post, "id").desc())
    variable_dict["posts"] = result
    return render_template("post_list.html", variable_dict=variable_dict)


@app.route("/posts/<post_id>")
def show_certain_post(post_id):
    variable_dict["page"] = "posts"
    variable_dict["selected_post"] = Post.query.get(post_id)
    return render_template("post.html", variable_dict=variable_dict)


@app.route("/make_post", methods=["GET", "POST"])
@login_required
def make_post():
    variable_dict["page"] = "posts"
    form = EditPost()

    if form.validate_on_submit():
        title_input = form.title.data
        subtitle_input = form.subtitle.data
        body_input = request.form.get("body")
        category_id = request.args.get("category_id")

        new_post = Post(title=title_input, subtitle=subtitle_input, body=body_input,
                        created_at=datetime.date.today(), category_id=category_id)
        db.session.add(new_post)
        db.session.commit()

        # count data refresh
        update_count(category_id)

        return redirect(url_for("show_posts_by_category", category_id=category_id))

    return render_template("make_post.html", variable_dict=variable_dict, form=form)


@app.route("/edit_post", methods=["GET", "POST"])
@login_required
def edit_post():
    variable_dict["page"] = "posts"
    form = EditPost()
    content_id = request.args.get("content_id")

    # edit post
    if form.validate_on_submit():
        body_input = request.form.get("body")
        category_id = request.args.get("category_id")

        target_post = Post.query.get(content_id)
        target_post.title = form.title.data
        target_post.subtitle = form.subtitle.data
        target_post.body = body_input

        db.session.commit()

        return redirect(url_for("show_posts_by_category", category_id=category_id))

    # get data from post to set default value
    target_post = Post.query.get(content_id)
    content_title = target_post.title
    content_subtitle = target_post.subtitle
    content_body = target_post.body

    form.title.data = content_title
    form.subtitle.data = content_subtitle

    return render_template("make_post.html", variable_dict=variable_dict, form=form, content_body=content_body)


@app.route("/delete")
@login_required
def delete_post():
    post_id = request.args.get("post_id")
    category_id = request.args.get("category_id")
    target_post = Post.query.get(post_id)

    db.session.delete(target_post)
    db.session.commit()

    update_count(category_id)

    return redirect(url_for("show_posts_by_category", category_id=category_id))


@app.route("/new_category", methods=["GET", "POST"])
@login_required
def make_category():
    variable_dict["page"] = "posts"
    form = NewCategory()
    if form.validate_on_submit():
        name_input = form.name.data

        new_category = Category(name=name_input, count=0)
        db.session.add(new_category)
        db.session.commit()

        target = Category.query.filter_by(name=name_input).first()
        variable_dict["categories"] = Category.query.all()

        return redirect(url_for("show_posts_by_category", category_id=target.id))

    return render_template("make_category.html", variable_dict=variable_dict, form=form)


# APP run
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
