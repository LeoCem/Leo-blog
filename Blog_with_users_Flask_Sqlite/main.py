from datetime import date
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='x',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONFIGURE TABLES
with app.app_context():
    class User(UserMixin, db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(250), unique=True, nullable=False)
        password = db.Column(db.String(250), nullable=False)
        name = db.Column(db.String(250), nullable=False)
        posts = relationship("BlogPost", back_populates="author")
        comments = relationship("Comment", back_populates="comment_author")


    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)
        author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        author = relationship("User", back_populates="posts")
        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)
        comments = relationship("Comment", back_populates="parent_post")


    class Comment(db.Model):
        __tablename__ = "comments"
        id = db.Column(db.Integer, primary_key=True)
        text = db.Column(db.String(250), nullable=False)
        author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        comment_author = relationship("User", back_populates="comments")
        post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
        parent_post = relationship("BlogPost", back_populates="comments")


    db.create_all()


def admin_only(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if current_user.id == 1:
            return function(*args, **kwargs)
        else:
            return abort(403)

    return decorated_function


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user_that_exists = User.query.filter_by(email=form.email.data).first()
        if not user_that_exists:
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=generate_password_hash(form.password.data, method='pbkdf2:sha256',
                                                salt_length=8))

            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
        else:
            flash("User with this email already exists,please login.")
            return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash("You have entered incorrect password, please try again")
                return redirect(url_for('login'))
        else:
            flash("You have entered wrong email, please try again")
            return redirect(url_for('login'))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    post_comments = requested_post.comments

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to be logged in to leave a comment.")
            return redirect(url_for('login'))
        else:
            new_comment = Comment(
                text=form.comment_body.data,
                author_id=current_user.id,
                post_id=post_id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=requested_post.id))

    return render_template("post.html", post=requested_post, form=form, comments=post_comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
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
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
