from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, InventoryItem, Order, OrderItem
from forms import OrderForm
from datetime import datetime, timedelta
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired
import os
from werkzeug.utils import secure_filename
from forms import ProductForm
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from io import BytesIO

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
    # Set the limit for the maximum number of users
    max_users = 3  # Change this value to your desired limit

    if request.method == 'POST':
        # Check if the current number of users has reached the limit
        user_count = User.query.count()
        if user_count >= max_users:
            flash('Registration limit reached. No more users can be registered.')
            return redirect(url_for('register'))

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
    # Define the threshold for low stock
    low_stock_threshold = 20

    # Calculate total inventory value
    inventory_items = InventoryItem.query.all()
    total_inventory_value = sum(item.price * item.stock for item in inventory_items)
    # Identify low stock items
    low_stock_items = [item for item in inventory_items if item.stock < low_stock_threshold]
    # Retrieve the most recent orders (limit to, say, 5 most recent)
    recent_orders = Order.query.order_by(Order.date_created.desc()).limit(5).all()

    # Fetch stock levels by product
    stock_data = db.session.query(InventoryItem.name, InventoryItem.stock).all()
    
    # Query to get the top-selling products
    top_selling_products = db.session.query(
        InventoryItem.name, db.func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).group_by(InventoryItem.name).order_by(db.func.sum(OrderItem.quantity).desc()).limit(5).all()

    # Adjusted code to handle data correctly top-selling products
    product_names = [item for item, total_sold in top_selling_products]
    total_sold = [total_sold for item, total_sold in top_selling_products]


    if 'user_id' not in session:
        flash('Please log in to access the dashboard')
        return redirect(url_for('login'))
    return render_template('index.html', total_inventory_value=total_inventory_value, low_stock_items=low_stock_items, recent_orders=recent_orders, stock_data=stock_data, product_names=product_names, total_sold=total_sold) # Retrieve sales data from the database

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


@app.route('/download-reports')
def download_reports():
    # Fetch data from your database models
    items = InventoryItem.query.all()
    orders = Order.query.all()

    # Prepare data for the Inventory DataFrame
    inventory_data = {
        "Product": [item.name for item in items],
        "Quantity": [item.quantity for item in items],
        "Unit": [item.unit for item in items],
        "Price": [item.price for item in items],
        "Stock": [item.stock for item in items],
        "Description": [item.description for item in items]
    }

    df_inventory = pd.DataFrame(inventory_data)
    


    # Convert the 'Quantity' column to numeric, forcing errors to NaN
    df_inventory['Quantity'] = pd.to_numeric(df_inventory['Quantity'], errors='coerce')

    # Fill NaN values with 0 or drop them, depending on your use case
    df_inventory['Quantity'].fillna(0, inplace=True)
    # Alternatively, drop rows with NaN values
    # df_inventory.dropna(subset=['Quantity'], inplace=True)

    # Filter low stock items
    df_low_stock = df_inventory[df_inventory['Quantity'] < 20]

    # Prepare data for the Orders DataFrame
    order_data = []
    for order in orders:
        for order_item in order.order_items:
            order_data.append({
                "Order ID": order.id,
                "Customer Name": order.name,
                "Phone": order.phone,
                "Location": order.address,
                "Product": order_item.inventory_item,
                "Quantity": order_item.quantity
            })

    df_orders = pd.DataFrame(order_data)

    # Generate PDF report
    buffer = BytesIO()

    # Create the figure and the PDF document
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_inventory.to_excel(writer, sheet_name='Inventory', index=False)
        df_low_stock.to_excel(writer, sheet_name='Low Stock Items', index=False)
        df_orders.to_excel(writer, sheet_name='Orders', index=False)

        workbook  = writer.book
        worksheet = writer.sheets['Inventory']

        # You can add some formatting here if needed
        format1 = workbook.add_format({'num_format': '#,##0.00'})
        worksheet.set_column('C:C', None, format1)  # Format price column

    # Move to the beginning of the stream
    buffer.seek(0)

    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Disposition'] = 'inline; filename=report.xlsx'
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    return response


#@app.route('/reports')
#def reports():
#    return render_template('reports.html')



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