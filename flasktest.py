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
    with open("c:\\Users\\Sourabh kumar\\Desktop\\Flask\\config.json", "r") as c:
        params = json.load(c)["params"]
except FileNotFoundError:
    print("File not found.")
except json.decoder.JSONDecodeError as e:
    print(f"JSON decoding error: {e}")


#email sending
local_server=True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
)
mail = Mail(app)
if(local_server):
    app.config["SQLALCHEMY_DATABASE_URI"] = params['local_uri']
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = params['prod_uri']
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
    customer_address = db.Column(db.String(200), nullable=False)
    total_amount = db.Column(db.Integer, nullable=False)
    delivery_charges = db.Column(db.Integer, nullable=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    items = relationship('OrderItem', back_populates='order')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    order = relationship('Order', back_populates='items')

#site page related content
@app.route("/")
def index():
    return render_template('index.html', params = params)


@app.route("/admin", methods=['GET','POST'])
def admin(): 
    if request.method=='POST':
        username=request.form.get('username')
        password=request.form.get('password')
        if (username == os.environ.get['admin_user'] and password == os.environ.get['admin_password']):
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
        # Retrieve form data
        customer_name = request.form.get('name')
        customer_phone = request.form.get('phone')
        customer_email = request.form.get('email')
        customer_address = request.form.get('address')
        # customer_landmark = request.form.get('landmark')
        cart_items_json = request.form.get('cart_items_json')

        if not cart_items_json:
            return "Cart items JSON data is missing", 400

        try:
            cart_items = json.loads(cart_items_json)
        except json.JSONDecodeError as e:
            return f"Error decoding cart items JSON: {str(e)}", 400

        cart_total = request.form.get('cart_total')
        delivery_charges = request.form.get('delivery_charges')

        # Create a new order
        order = Order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            customer_address=customer_address,
            # customer_landmark = customer_landmark,
            total_amount=float(cart_total.replace('₹', '')) + float(delivery_charges.replace('₹', '')),
            delivery_charges=float(delivery_charges.replace('₹', '')),
            order_date=datetime.now()
        )

        # Add order items
        for item in cart_items:
            order_item = OrderItem(
                name=item['name'],
                quantity=item['quantity'],
                price=item['price'],
                total_price=item['totalPrice']
            )
            order.items.append(order_item)

        # Save to the database
        db.session.add(order)
        db.session.commit()

        # Redirect to the cash page
        return redirect(url_for('cash'))

    except Exception as e:
        # Handle exceptions, log the error, and redirect to an error page
        print(f"Error creating order: {str(e)}")
        return redirect(url_for('error_page'))
    
@app.route("/order", methods=['GET', 'POST'])
def order():
    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        landmark = request.form.get('landmark')

        entry = Customer(name=name, phone=phone, email=email, address=address, landmark=landmark)
        db.session.add(entry)
        db.session.commit()

        # Retrieve cart items and total from session storage
        cartItems = json.loads(session.get('cartItems', '[]'))
        cartTotal = session.get('cartTotal', '₹0')

        customer = Customer.query.all()

        return render_template('order.html', params=params, cartItems=cartItems, cartTotal=cartTotal, customer=customer)

    return render_template('order.html', params=params)


@app.route("/edit/<string:Sno>", methods=['GET', 'POST'])
def edit(Sno):
    if ('user' in session and session['user'] == params['admin_user']):
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
    if ('user' in session and session['user'] == params['admin_user']):
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
    if 'user' not in session or session['user'] != params['admin_user']:
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


@app.route("/cash", methods=['GET', 'POST'])
def cash():

    cart_items_json = session.get('cartItems', '[]')
    cart_items = json.loads(cart_items_json)
    cart_total = session.get('cartTotal', '₹0')

    # print("cartItems in session:", cart_items)
    # print("cartTotal in session:", cart_total)

    if request.method == 'POST':
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        address = request.form.get('address')
        landmark= request.form.get('landmark')
        
        order_date = datetime.now().strftime("%d %b %Y (%H:%M:%S)")

        #print("cartItems in session:", session.get('cartItems', '[]'))
        #print("cartTotal in session:", session.get('cartTotal', '₹0'))

        # Retrieve cart items and total from session storage
        cartItems = json.loads(session.get('cartItems', '[]'))
        cartTotal = session.get('cartTotal', '₹0')

        # print("Structure of cartItems:", cartItems)
        
        # Calculate delivery charges based on cart total
        deliveryCharges = 0
        if cartTotal:
            totalValue = float(cartTotal.replace("₹", ""))
            if totalValue > 0 and totalValue <= 500:
                deliveryCharges = 40
            elif totalValue > 500 and totalValue<= 1000:
                deliveryCharges = 20
            else:
                deliveryCharges = 0

        # Update the cart total by adding delivery charges
        cartTotalValue = totalValue + deliveryCharges
        cartTotal = f'₹{cartTotalValue}'

        # Save order information in session
        order_info = {
            'cartItems': cartItems,
            'cartTotal': cartTotal,
            'deliveryCharges': deliveryCharges
        }
        session['orderInfo'] = json.dumps(order_info)

        subject = 'New Order From ' + name
        sender = params['gmail-user']
        recipients = [sender]

        # Generate the HTML content for the email
        email_body = f'''
            <html>
            <head></head>
            <body>
                <h2>Customer Information:</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Phone:</strong> {phone}</p>
                <p><strong>Address:</strong> {address}</p>
                <p><strong>Landmark:</strong> {landmark}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Order Date:</strong> {order_date}</p>

                <h2>Order Summary:</h2>
                <table border="1">
                    <thead>
                        <tr>
                            <th>Item Name</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Total Price</th>
                        </tr>
                    </thead>
                    <tbody>
        '''

        for dat in cartItems:
            # print("Processing item:", dat)
            email_body += f'''
                <tr>
                    <td>{dat['name']}</td>
                    <td>{dat['quantity']}</td>
                    <td>₹{dat['price']}</td>
                    <td>₹{dat['totalPrice']}</td>
                </tr>
            '''

        email_body += f'''
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3">Delivery Charges:</td>
                            <td>₹{deliveryCharges}</td>
                        </tr>
                        <tr>
                            <td colspan="3">Total:</td>
                            <td>{cartTotal}</td>
                        </tr>
                    </tfoot>
                </table>
            </body>
            </html>
        '''

        msg = Message(subject=subject, sender=sender, recipients=recipients)
        msg.html = email_body
        mail.send(msg)

        # Clear the cart
        session['cartItems'] = '[]'
        session['cartTotal'] = '₹0'

        return render_template('cash.html', params=params, order_info=order_info)

    return render_template('cash.html', params=params)

#Run the main app
if __name__ == "__main__":
    app.run(debug=True)