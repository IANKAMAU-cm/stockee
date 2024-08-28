from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, InventoryItem, Order, OrderItem
from forms import OrderForm
from datetime import datetime
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired
import os
from werkzeug.utils import secure_filename
from forms import ProductForm


#import stripe 

#stripe.api_key = "your-stripe-secret-key"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# Define where to store uploaded images
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize the db with the Flask app
db.init_app(app)



@app.before_request
def before_request():
    if 'cart' not in session:
        session['cart'] = {}  # Initialize cart as a dictionary

@app.route('/')
def products():
    items = InventoryItem.query.all()
    return render_template('products.html', items=items)

#login and registering
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            flash('Login Failed. Check your Username and Password.')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. Proceed to log in')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/index')
def index():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

#inventory management
@app.route('/inventory', methods=['GET'])
def inventory():
    items = InventoryItem.query.all()
    return render_template('inventory.html', items=items)

@app.route('/add-item', methods=['GET', 'POST'])
def add_item():
    form = ProductForm()
    if form.validate_on_submit():
        image_file = form.image.data
        filename = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                image_file.save(image_path)
            except Exception as e:
                flash(f'Error saving image: {str(e)}')
                return redirect(url_for('add_item'))
        
        new_item = InventoryItem(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            quantity=form.quantity.data,
            unit=form.unit.data,
            stock=form.stock.data,
            image=filename
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully.')
        return redirect(url_for('inventory'))
    return render_template('add_item.html', form=form)

@app.route('/edit-item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    form = ProductForm(obj=item)

    if form.validate_on_submit():
        item.name = form.name.data
        item.description = form.description.data
        item.price = form.price.data
        item.quantity = form.quantity.data
        item.stock = form.stock.data
        
        image_file = form.image.data
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                image_file.save(image_path)
                item.image = filename
            except Exception as e:
                flash(f'Error saving image: {str(e)}')
                return redirect(url_for('edit_item', item_id=item_id))
        
        db.session.commit()
        flash('Item updated successfully.')
        return redirect(url_for('inventory'))

    return render_template('edit_item.html', form=form, item=item)

#deleting an item from inventory
@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    try:
        # Fetch the item to be deleted
        item = InventoryItem.query.get(item_id)
        
        # Check if the item exists
        if not item:
            flash('Item not found.', 'error')
            return redirect(url_for('inventory_list'))
        
        # Remove all references to this item in other tables
        OrderItem.query.filter_by(inventory_item_id=item_id).delete()
        
        # Delete the item
        db.session.delete(item)
        db.session.commit()
        
        flash('Item deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error occurred: {str(e)}', 'error')
    
    return redirect(url_for('inventory'))
@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/notifications')
def notifications():
    return render_template('notifications.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/users')
def users():
    return render_template('users.html')

#ordering, cart and checkout
@app.route('/orders', methods=['GET'])
def orders():
    orders = Order.query.all()
    return render_template('orders.html', orders=orders)

@app.route('/order/new', methods=['GET', 'POST'])
def new_order():
    form = OrderForm()
    form.inventory_item.choices = [(item.id, item.name) for item in InventoryItem.query.all()]
    if form.validate_on_submit():
        order = Order(user_id=1)  # Replace with actual user_id
        db.session.add(order)
        db.session.commit()
        order_item = OrderItem(order_id=order.id,
                               inventory_item_id=form.inventory_item.data,
                               quantity=form.quantity.data,
                               price=InventoryItem.query.get(form.inventory_item.data).price)
        db.session.add(order_item)
        db.session.commit()
        return redirect(url_for('orders'))
    return render_template('new_order.html', form=form)

@app.route('/order/<int:order_id>', methods=['GET'])
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_detail.html', order=order)

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    cart = session['cart']
    item_id_str = str(item_id)  # Always convert item_id to string when storing in session
    cart[item_id_str] = cart.get(item_id_str, 0) + 1

    session.modified = True  # Mark session as modified to save changes
    return redirect(url_for('products'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    items = [(InventoryItem.query.get(int(item_id)), quantity) for item_id, quantity in cart.items()]
    # Calculate the total value
    total_value = sum(item.price * quantity for item, quantity in items)
    return render_template('cart.html', items=items, total_value=total_value)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart = session.get('cart', {})
    item_id_str = str(item_id)  # Convert item_id to string to match session keys
    
    if item_id_str in cart:
        del cart[item_id_str]  # Remove the item from the cart dictionary
        session['cart'] = cart
        session.modified = True  # Mark session as modified to save changes
    
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        address = request.form.get('address')
        user_id = 1  # Replace with actual user ID
        order = Order(user_id=user_id, name=name, phone=phone, address=address)
        db.session.add(order)
        db.session.commit()
        cart = session.get('cart', {})
        for item_id, quantity in cart.items():
            item = InventoryItem.query.get(item_id)
            order_item = OrderItem(order_id=order.id,
                                   inventory_item_id=item_id,
                                   quantity=quantity,
                                   price=item.price)
            db.session.add(order_item)
        db.session.commit()
        session.pop('cart', None)
        return redirect(url_for('order_confirmation', order_id=order.id))
    return render_template('checkout.html')

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)


#currency
@app.template_filter('currency')
def currency_format(value, currency="KES"):
    if not isinstance(value, (int, float)):
        return value  # Return the value unchanged if it's not a number
    return f"{currency} {value:,.2f}"

#dispatch
@app.route('/dispatch_order/<int:order_id>', methods=['POST'])
def dispatch_order(order_id):
    order = Order.query.get_or_404(order_id)
    
    if order.status != 'Dispatched':
        for item in order.items:
            inventory_item = InventoryItem.query.get(item.inventory_item_id)
            if inventory_item:
                inventory_item.stock -= item.quantity
                db.session.commit()
        
        order.status = 'Dispatched'
        db.session.commit()
    
    return redirect(url_for('order_detail', order_id=order_id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)