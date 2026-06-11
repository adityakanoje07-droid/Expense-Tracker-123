from datetime import datetime
import os

from flask import Flask, render_template, request, url_for, flash, redirect
from forms import RegistrationForm, LoginForm
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from collections import defaultdict
import plotly.express as px

# app = Flask(__name__)
# app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'


# db = SQLAlchemy(app)
# if os.environ.get('VERCEL'):
#     app = Flask(__name__, instance_path='/tmp/instance')
# else:
#     app = Flask(__name__)

# # 2. Point your SQLite URI to the writeable /tmp/ directory
# if os.environ.get('VERCEL'):
#     app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/expenses.db'
# else:
#     app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'

# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# # 3. Initialize your database
# db = SQLAlchemy(app)
app = Flask(__name__)

database_uri = os.environ.get("DATABASE_URL")

if not database_uri:
    database_uri = "sqlite:///expenses.db"

if database_uri.startswith("postgres://"):
    database_uri = database_uri.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SECRET_KEY"] = "dev-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    description = db.Column(db.String(200))
    date = db.Column(db.String(20))

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(20), unique=True, nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(60), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



@app.route("/")
@app.route("/home")
@login_required
def home():

    if current_user.is_authenticated:
     expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()
    else:
     expenses = []

    total_expense = sum(exp.amount for exp in expenses)

    current_month = datetime.now().month

    monthly_expense = sum(
        exp.amount
        for exp in expenses
        if datetime.strptime(exp.date, "%Y-%m-%d").month == current_month
    )

    total_categories = len(set(exp.category for exp in expenses))

    return render_template(
        'home.html',
        total_expense=total_expense,
        monthly_expense=monthly_expense,
        total_categories=total_categories
    )


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():

    form = RegistrationForm()

    if form.validate_on_submit():

        existing_user = User.query.filter_by(
            email=form.email.data
        ).first()

        if existing_user:
            flash(
                'Email already registered!',
                'danger'
            )
            return redirect(url_for('register'))

        user = User(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )

        db.session.add(user)
        db.session.commit()

        flash(
            'Account created successfully!',
            'success'
        )

        return redirect(url_for('login'))

    return render_template(
        'register.html',
        title='Register',
        form=form
    )

@app.route("/login", methods=['GET', 'POST'])
def login():

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(
            email=form.email.data
        ).first()

        if user and user.password == form.password.data:
            login_user(user)
            flash(
                'Login Successful!',
                'success'
            )

            return redirect(url_for('home'))

        else:

            flash(
                'Invalid Email or Password',
                'danger'
            )

    return render_template(
        'login.html',
        title='Login',
        form=form
    )

@app.route('/logout')
@login_required
def logout():

    logout_user()

    flash(
        'Logged out successfully!',
        'success'
    )

    return redirect(url_for('home'))


@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():

    if request.method == 'POST':

        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        date = request.form['date']

        new_expense = Expense(
            amount=amount,
            category=category,
            description=description,
            date=date,
            user_id=current_user.id
        )

        db.session.add(new_expense)
        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('add_expense.html')

@app.route('/dashboard')
@login_required
def dashboard():

    expenses = Expense.query.filter_by(
      user_id=current_user.id
    ).all()

    return render_template(
        'dashboard.html',
        expenses=expenses
    )

@app.route('/edit_expense/<int:id>',
           methods=['GET', 'POST'])
@login_required
def edit_expense(id):

    expense = Expense.query.get_or_404(id)

    if request.method == 'POST':

        expense.amount = request.form['amount']
        expense.category = request.form['category']
        expense.description = request.form['description']
        expense.date = request.form['date']

        db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template(
        'edit_expense.html',
        expense=expense
    )

@app.route('/delete_expense/<int:id>')
@login_required
def delete_expense(id):

    expense = Expense.query.filter_by(
    id=id,
    user_id=current_user.id
).first_or_404()

    db.session.delete(expense)
    db.session.commit()

    return redirect(url_for('dashboard'))

@app.route('/monthly_report')
@login_required
def monthly_report():

    expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).all()

    current_month = datetime.now().month

    monthly_expenses = [
        exp for exp in expenses
        if datetime.strptime(
            exp.date,
            "%Y-%m-%d"
        ).month == current_month
    ]

    total_monthly = sum(
        exp.amount
        for exp in monthly_expenses
    )

    category_totals = defaultdict(float)

    for exp in monthly_expenses:
        category_totals[exp.category] += exp.amount

    highest_category = (
        max(category_totals,
            key=category_totals.get)
        if category_totals
        else "None"
    )

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    chart_html = ""

    if values:
        fig = px.pie(
            names=labels,
            values=values,
            title="Expense Distribution"
        )

        chart_html = fig.to_html(
            full_html=False
        )

    return render_template(
        'monthly_report.html',
        total_monthly=total_monthly,
        total_transactions=len(monthly_expenses),
        highest_category=highest_category,
        category_totals=category_totals,
        chart_html=chart_html
    )

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
