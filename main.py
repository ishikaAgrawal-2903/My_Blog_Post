from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os

##CONFIGURE TABLES
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
logged_in = False


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


#using gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


#blog_posts table
class BlogPost(db.Model, UserMixin):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="blog_posts")
    title = db.Column(db.String(250),nullable=False, unique=True)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = relationship("Comment", back_populates="post")


#users table
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    blog_posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")


#comments table
class Comment(db.Model):
    __tablename__="comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    author = relationship("User", back_populates="comments")
    text = db.Column(db.String, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"), nullable=False)
    post = relationship("BlogPost", back_populates="comments")


# Python decorator to access path only by admin
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if getattr(current_user, "id", None) != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

#ceate Database
db.create_all()


#load user by its id
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


#home page that shows all posts
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user_id=getattr(current_user, "id", None), logged_in=logged_in)


#Regiser page
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user_exist = User.query.filter_by(email=form.email.data).first()
        if not user_exist:
            user_dict = {
                "email": form.email.data,
                "password": generate_password_hash(form.password.data),
                "name": form.name.data
            }
            user = User(**user_dict)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            global logged_in
            logged_in = True
            # return render_template("index.html", logged_in=logged_in, all_posts=posts, user_id=getattr(current_user, "id", None))
            return redirect(url_for("get_all_posts"))
        else:
            flash("User already exist. Try Log in")
    return render_template("register.html", form=form)


#login page
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user_exist = User.query.filter_by(email=form.email.data).first()
        if user_exist:
            user_pass = user_exist.password
            is_correct_pass = check_password_hash(user_pass, form.password.data)
            if is_correct_pass:
                global logged_in
                logged_in = True
                login_user(user_exist)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Incorrect Password. Try again")
        else:
            flash("User does not exist. Try to Register")
    return render_template("login.html", form=form)


#logout user session and redirect to home page
@app.route('/logout')
def logout():
    if current_user.__dict__:
        logout_user()
        global logged_in
        logged_in = False
    return redirect(url_for('get_all_posts'))


#page to show only particular post
@app.route("/post/<int:post_id>", methods=["GET","POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if not getattr(current_user, "id", None):
        return redirect(url_for('login'))

    if form.validate_on_submit():
        if current_user.is_authenticated:
            comment = Comment(
                author_id=current_user.id,
                post_id=post_id,
                text=form.text.data
            )
            db.session.add(comment)
            db.session.commit()
        else:
            flash("For Comment you need to Register or Login ")
    return render_template("post.html", form=form, post=requested_post, logged_in=logged_in, user_id=getattr(current_user, "id", None))


#About page
@app.route("/about")
def about():
    return render_template("about.html")


#Contact page
@app.route("/contact")
def contact():
    return render_template("contact.html")


#add post and redirect to home page
@app.route("/new-post", methods=['GET', 'POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, is_edit=False)


#edit post but only admin can edit it
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit() and current_user.is_authenticated:
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, user_id=current_user.id, is_edit=True, logged_in=logged_in)

#delete post and redirect to home but only admin can
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("get_all_posts"))

#run our app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
