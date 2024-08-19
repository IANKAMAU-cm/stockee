from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, InventoryItem

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# Initialize the db with the Flask app
db.init_app(app)

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

@app.route('/')
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

@app.route('/inventory', methods=['GET'])
def inventory():
    items = InventoryItem.query.all()
    return render_template('inventory.html', items=items)

@app.route('/add-item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form.get('name')
        quantity = request.form.get('quantity')
        price = request.form.get('price')
        description = request.form.get('description')

        new_item = InventoryItem(name=name, quantity=quantity, price=price, description=description)
        db.session.add(new_item)
        db.session.commit()

        flash('Item added successfully.')
        return redirect(url_for('inventory'))

    return render_template('add_item.html')

@app.route('/edit-item/<int:item_id>', methods=['GET', 'POST'])
def edit_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)

    if request.method == 'POST':
        item.name = request.form.get('name')
        item.quantity = request.form.get('quantity')
        item.price = request.form.get('price')
        item.description = request.form.get('description')

        db.session.commit()

        flash('Item updated successfully.')
        return redirect(url_for('inventory'))

    return render_template('edit_item.html', item=item)

@app.route('/delete-item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash('Item deleted successfully.')
    return redirect(url_for('inventory'))

@app.route('/orders')
def orders():
    return render_template('orders.html')

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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

