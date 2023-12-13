from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import requests
from flask_login import LoginManager, login_user, UserMixin, login_required, logout_user, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import ForeignKey


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///techtool.db'
app.config['SECRET_KEY'] = '2e2a62d88e6edb6bf1580f9c81eb1d4a27621febdf81d854a8635c931b958667'
db = SQLAlchemy(app)


login_manager = LoginManager(app)
login_manager.login_view = 'login'

login_manager.init_app(app)


class Customer(db.Model, UserMixin):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.Integer, unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)




class MachineTool(db.Model):
    __tablename__ = 'machinetool'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    picture = db.Column(db.String)
    price = db.Column(db.Float, nullable=False)
    warranty = db.Column(db.Integer)
    model_name = db.Column(db.String(50))
    manufacturer = db.Column(db.String(100), nullable=False)



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    machinetool_id = db.Column(db.Integer, db.ForeignKey('machinetool.id'), nullable=False)
    delivery_address = db.Column(db.String(255), nullable=False)
    order_status = db.Column(db.Boolean, default=False)
    cart_status = db.Column(db.Boolean, default=False)

class Admin(db.Model, UserMixin):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.Integer, unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)




with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Customer.query.get(int(user_id))

@app.route("/")
def home():
    tools=MachineTool.query.all()
    return render_template("index.html",tools=tools)

@app.route("/adminlogin", methods=['GET', 'POST'])
def adminlogin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        admin =Admin.query.filter_by(email=email, password=password).first()

        if admin:
            login_user(admin)
            return redirect(url_for('admindashboard'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')

    return render_template('adminlogin.html')

@app.route("/admindashboard")
@login_required
def admindashboard():
    orders = Order.query.all()

    return render_template("admindashboard.html", orders=orders)

@app.route('/deliver_order/<int:order_id>', methods=['POST'])
@login_required
def deliver_order(order_id):
    try:

        order = Order.query.get(order_id)

        if order:
            # Delete the order from the database
            db.session.delete(order)
            db.session.commit()

            return jsonify(success=True)
        else:
            return jsonify(success=False, error='Order not found')

    except Exception as e:
        print(e)
        return jsonify(success=False, error='An error occurred while processing the request')


@app.route('/adminlogout')
@login_required
def adminlogout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_machine_tool', methods=['GET', 'POST'])
@login_required
def add_machine_tool():
    if request.method == 'POST':
        picture = request.files['picture']
        picture_filename = secure_filename(picture.filename)
        picture.save(os.path.join('static', picture_filename))

        name = request.form['name']
        price = float(request.form['price'])
        warranty = int(request.form['warranty']) if request.form['warranty'] else None
        model_name = request.form['model_name']
        manufacturer = request.form['manufacturer']

        new_tool = MachineTool(
            name=name,
            picture=picture_filename,
            price=price,
            warranty=warranty,
            model_name=model_name,
            manufacturer=manufacturer
        )

        db.session.add(new_tool)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('add_machine_tool.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.form.get('next')
    if next_url:
        flash('You need to sign up or log in to make a purchase.', 'info')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        customer = Customer.query.filter_by(email=email, password=password).first()

        if customer:
            login_user(customer)
            session['customer_name'] = customer.name
            #flash('Login successful!', 'success')
            # Redirect to the customer's dashboard or another page
            return redirect(url_for('dashboard', name=customer.name))
        else:
            flash('Login failed. Please check your email and password.', 'danger')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')

        #hashed_password = generate_password_hash(password, method='sha256')

        new_customer = Customer(name=name, email=email, phone=phone, password=password)
        db.session.add(new_customer)
        db.session.commit()

        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route("/dashboard/<name>")
@login_required
def dashboard(name):
    tools = MachineTool.query.all()
    #customer_id=current_user(Customer.id)
    return render_template("dashboard.html", tools=tools, name=name)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_to_cart/<int:machine_tool_id>', methods=['POST'])
@login_required
def add_to_cart(machine_tool_id):
    customer_id=current_user.id
    name=current_user.name
    delivery_address = request.form.get('delivery_address')
    if not delivery_address:
        flash('Please enter a delivery address.', 'error')
        return redirect(url_for('dashboard'))

    new_order = Order(customer_id=customer_id, machinetool_id=machine_tool_id, delivery_address=delivery_address,
                      cart_status=True)
    db.session.add(new_order)
    db.session.commit()

    flash('Product added to cart successfully!', 'success')
    return redirect(url_for('dashboard', name=name))

@app.route('/buy/<int:machine_tool_id>', methods=['POST'])
@login_required
def buy(machine_tool_id):
    customer_id = current_user.id
    name = current_user.name
    delivery_address = request.form.get('delivery_address')

    if not delivery_address:
        flash('Please enter a delivery address.', 'error')
        return redirect(url_for('dashboard'))

    new_order = Order(customer_id=customer_id, machinetool_id=machine_tool_id, delivery_address=delivery_address,
                      order_status=True)
    db.session.add(new_order)
    db.session.commit()

    flash('Purchase successful!', 'success')
    return redirect(url_for('dashboard',name=name))

@app.route('/my_orders')
@login_required
def my_orders():
    customer_id=current_user.id
    name=current_user.name
    orders = Order.query.filter_by(customer_id=customer_id, order_status=True).all()

    ordered_tools = []

    for order in orders:
        machinetool_id=order.machinetool_id
        tool_details=MachineTool.query.get(machinetool_id)
        ordered_tools.append(tool_details)

    return render_template('orders.html', ordered_tools=ordered_tools, name=name)

@app.route('/my_cart')
@login_required
def my_cart():
    customer_id = current_user.id
    name=current_user.name
    carts = Order.query.filter_by(customer_id=customer_id, cart_status=True).all()

    carted_tools=[]

    for cart in carts:
        machinetool_id = cart.machinetool_id
        tool_details = MachineTool.query.get(machinetool_id)
        carted_tools.append(tool_details)

    return  render_template('cart.html', carted_tools=carted_tools, name=name)

def update_order_status(customer_id, tool_id):
    try:

        order = Order.query.filter_by(customer_id=customer_id, machinetool_id=tool_id, cart_status=True).first()


        order.cart_status=False
        order.order_status=True


        db.session.commit()

        return True  # Success
    except Exception as e:
        print(e)
        return False  # Failed


@app.route('/buy_now/<int:tool_id>', methods=['POST'])
def buy_now(tool_id):
    success = update_order_status(current_user.id, tool_id)
    return jsonify(success=success)




if __name__ == '__main__':
    app.run(debug=True)

#admininstration : /adminlogin
#email:admin@email.com
#password:123@admin
