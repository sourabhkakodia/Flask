from flask import Flask, redirect, render_template, request, session, flash, url_for
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
import json
from flask_mail import Mail, Message
from datetime import datetime
from flask import jsonify
import os

# to run on ngrok command - ngrok http 5000


# to add name of business in print order
#json file
try:
    with open("config.json", "r") as c:
        params = json.load(c)["params"]
except FileNotFoundError:
    print("File not found.")
except json.decoder.JSONDecodeError as e:
    print(f"JSON decoding error: {e}")


#email sending
local_server=False
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS = True,
    MAIL_USE_SSL = False,
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
)
mail = Mail(app)
if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('LOCAL_URI')
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('PROD_URI')
db = SQLAlchemy(app)

#Query to enter customer information into database
class Customer (db.Model):
    Sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(12), unique=True, nullable=False)
    address = db.Column(db.String(120), nullable=False)
    Date = db.Column(db.DateTime, nullable=False)

#Query to enter Items information into database
class Items (db.Model):
    Sno = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80), nullable=False)
    Price = db.Column(db.Float, unique=True, nullable=False)
    image_url = db.Column(db.String(120), nullable=False)
    Quantity = db.Column(db.Integer, nullable=False)
    Date = db.Column(db.DateTime, nullable=False)

# Define the Order model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(200), nullable=False)
    customer_phone = db.Column(db.Integer, nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    customer_address = db.Column(db.String(200), nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    delivery_charges = db.Column(db.Integer, nullable=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = db.relationship('OrderItem', back_populates='order')


class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    order = db.relationship('Order', back_populates='items')

#site page related content
@app.route("/")
def index():
    return render_template('index.html', params = params)


@app.route("/admin", methods=['GET','POST'])
def admin(): 
    if request.method=='POST':
        username=request.form.get('username')
        password=request.form.get('password')
        if (username == os.environ.get('admin_user') and password == os.environ.get('admin_password')):
            session['user'] = username
            return redirect('/adminpage')
        else:
            msg="Invalid Username or Password"
            return render_template("admin.html", msg=msg, params = params)
    return render_template("admin.html", params = params)


@app.route("/items", methods = ['GET'])
def items_all():
    data = Items.query.all()
    return render_template('items.html', params = params, data = data)


@app.route('/search_items')
def search_items():
    query = request.args.get('query', '')
    if query:
        items = Items.query.filter(Items.Name.ilike(f"{query}%")).all()
    else:
        items = Items.query.all()
    return jsonify([{
        'id': item.Sno,
        'name': item.Name,
        'price': item.Price,
        'image_url': item.image_url
    } for item in items])


@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        customer_name = request.form.get('name')
        customer_phone = request.form.get('phone')
        customer_email = request.form.get('email')
        customer_address = request.form.get('address')
        cart_items_json = request.form.get('cart_items_json')
        cart_total = request.form.get('cart_total')
        delivery_charges = request.form.get('delivery_charges')

        if not cart_items_json or not cart_total or not delivery_charges:
            return "Missing cart data", 400

        cart_items = json.loads(cart_items_json)

        # ✅ Create Order object
        order = Order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            customer_address=customer_address,
            total_amount=float(cart_total.replace('₹', '')),
            delivery_charges=float(delivery_charges.replace('₹', ''))
        )

        # ✅ Add each item to OrderItem
        for item in cart_items:
            order_item = OrderItem(
                name=item['name'],
                quantity=item['quantity'],
                price=item['price'],
                total_price=item['totalPrice']
            )
            order.items.append(order_item)

        db.session.add(order)
        db.session.commit()

        # ✅ Store data in session to pass to cash.html
        session['orderInfo'] = json.dumps({
            'cartItems': cart_items,
            'cartTotal': cart_total,
            'deliveryCharges': float(delivery_charges.replace('₹', ''))
        })

        # ✅ Email content
        if customer_email:
            subject = f'Order Confirmation - {customer_name}'
            sender = os.environ.get('MAIL_USERNAME')
            recipients = [sender]
            body = f"New Order\n\nName: {customer_name}\nPhone: {customer_phone}\nAddress: {customer_address}\n\nItems:\n"
            for item in cart_items:
                body += f"{item['name']} - Qty: {item['quantity']} - ₹{item['totalPrice']}\n"
            body += f"\nDelivery: ₹{delivery_charges}\nTotal: ₹{cart_total}"

            msg = Message(subject=subject, sender=sender, recipients=recipients)
            msg.body = body
            mail.send(msg)

        # ✅ Redirect to cash.html
        return redirect(url_for('cash'))

    except Exception as e:
        print(f"Create order error: {e}")
        return "Internal Server Error", 500



@app.route("/edit/<string:Sno>", methods=['GET', 'POST'])
def edit(Sno):
    if ('user' in session and session['user'] == os.environ.get('admin_user')):
        if request.method == 'POST':
            P_name = request.form.get('Name')
            P_price = request.form.get('Price')
            P_image = request.form.get('image_url')
            P_Quantity = request.form.get('Quantity')

            if Sno != '0':
                item = Items.query.filter_by(Sno=Sno).first()
                item.Name = P_name
                item.Price = P_price
                item.image_url = P_image
                item.Quantity = P_Quantity
                db.session.commit()
                return redirect('/edit/'+Sno)

        item = Items.query.filter_by(Sno=Sno).first()
        return render_template('edit.html', params=params, item=item)
    return render_template('edit.html', params=params, item=None, Sno=Sno)



@app.route("/about")
def review():
    return render_template('about.html', params = params)


@app.route("/delete/<string:Sno>", methods = ['GET', 'POST'])
def delete(Sno):
    if ('user' in session and session['user'] == os.environ.get('admin_user')):
        items = Items.query.filter_by(Sno=Sno).first()
        db.session.delete(items)
        db.session.commit()
    return redirect('/adminpage')

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/admin')



@app.route("/adminpage", methods=['GET', 'POST'])
def adminpage():
    # Check if the user is authenticated (logged in)
    if 'user' not in session or session['user'] != os.environ.get('admin_user'):
        return redirect('/admin')

    if request.method == 'POST':
        Name = request.form.get('Name')
        Price = request.form.get('Price')
        image_url = request.form.get('image_url')
        Quantity = request.form.get('Quantity')

        if Quantity is None:
            Quantity = 0

        entry = Items(Name=Name, Price=Price, image_url=image_url, Quantity=Quantity, Date=datetime.now())
        db.session.add(entry)
        db.session.commit()

        # Check if the entered quantity is a valid integer
        try:
            Quantity = int(Quantity)
        except ValueError:
            Quantity = 0

        # Ensure the entered quantity is non-negative
        if Quantity < 0:
            Quantity = 0

        # Find the item in the database by its name
        item = Items.query.filter_by(Name=Name).first()

        if item:
            # Check if there's enough quantity to be deducted
            if item.Quantity >= Quantity:
                # Update the item's quantity
                item.Quantity -= Quantity
                db.session.commit()
            else:
                flash("Not enough quantity in stock.")

    # Query the updated item list
    items = Items.query.all()

    return render_template('adminpage.html', params=params, items=items)


@app.route('/update_cart', methods=['POST'])
def update_cart():
    if request.method == 'POST':
        data = request.get_json()
        cart_items_list = data['cartItems']
        session['cartItems'] = json.dumps(cart_items_list)
        session['cartTotal'] = data['cartTotal']
        print("Updated cartItems in session:", cart_items_list)
        print("Updated cartTotal in session:", data['cartTotal'])
        return 'Cart updated', 200
    return 'Invalid request', 400


@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    if request.method == 'POST':
        try:
            data = request.get_json()
            item_name = data.get('name')
            item_quantity = data.get('quantity')

            if item_name is None:
                return 'Item name is missing', 400

            # Validate item_quantity
            if item_quantity is not None:
                try:
                    item_quantity = int(item_quantity)
                    if item_quantity < 0:
                        return 'Invalid quantity', 400
                except ValueError:
                    return 'Invalid quantity', 400

                # Find the item in the database by its name
                item = Items.query.filter_by(Name=item_name).first()

                if item:
                    if item.Quantity is not None and item.Quantity >= item_quantity:
                        # Update the item's quantity
                        item.Quantity -= item_quantity
                        db.session.commit()
                        return 'Item quantity updated', 200
                    else:
                        return 'Not enough quantity in stock.', 400
                else:
                    return 'Item not found', 404
            else:
                return 'Quantity is missing', 400
        except Exception as e:
            return f'Error: {str(e)}', 500
    return 'Invalid request', 400


@app.route("/cash", methods=['GET'])
def cash():
    order_info_json = session.get('orderInfo')
    if order_info_json:
        order_info = json.loads(order_info_json)
        session.pop('orderInfo', None)  # Clear after use
    else:
        order_info = {
            'cartItems': [],
            'cartTotal': '₹0',
            'deliveryCharges': 0
        }

    return render_template('cash.html', params=params, order_info=order_info)




from sqlalchemy import create_engine

db_uri = 'postgresql://piyush_website_user:uPxXe3RXyYC0SzGj1562FW8D1ph9Onu7@dpg-d12bupje5dus73f53is0-a/piyush_website'
engine = create_engine(db_uri)

try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("Connection successful:", result.fetchone())
except Exception as e:
    print("Connection failed:", e)

from flasktest import OrderItem  # or just `OrderItem` if in same file
#Run the main app
with app.app_context():
    db.create_all()
    print("✅ All tables created (if they didn't exist already).")

if __name__ == "__main__":
    app.run(debug=True)