from flask import Flask, render_template, request, redirect, url_for, session, json, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
from werkzeug.security import generate_password_hash, check_password_hash
import random



app = Flask(__name__)
app.secret_key = ''

#Connect to MySQL Database
#MySQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'main'

# Intialize MySQL
mysql = MySQL(app)

# http://localhost:5000/Drunkfy - this will be the login page, we need to use both GET and POST requests
@app.route("/Drunkfy", methods=['GET', 'POST'])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'email' in request.form and 'password' in request.form:
        # Create variables for easy access
        email = request.form['email']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM user WHERE Email = %s", (email,))
        # Fetch one record and return result
        user = cursor.fetchone()
        # Check that password submitted matches the one stored in database
        if user and check_password_hash(user['Pwd'], password):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = user['UID']
            session['name'] = user['FirstName']
            session['lastname'] = user['LastName']
            session['email'] = user['Email']
            session['password'] = user['Pwd']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect email/password!'
    return render_template("login.html", msg=msg)

# http://localhost:5000/Drunkfy/Register - this will be the registration page, we need to use both GET and POST requests
@app.route('/Drunkfy/Register', methods=['GET', 'POST'])
def register():
    # Output messages
    negative = ''
    positive = ''
    # Check if "FirstName", "LastName", "email", "password" and "psw-repeat" POST requests exist (user submitted form)
    if request.method == 'POST' and 'FirstName' in request.form and 'LastName' in request.form and 'email' in request.form and 'password' in request.form and 'psw-repeat' in request.form:
        # Create variables for easy access
        firstName = request.form['FirstName']
        lastName = request.form['LastName']
        email = request.form['email']
        password = request.form['password']
        passwordvalidation = request.form['psw-repeat']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM user WHERE email = %s', (email,))
        account = cursor.fetchone()
        # If account exists show error, if not do validation checks
        if account:
            negative = 'Account already exists!'
        elif not re.match(r'^[A-Za-z]+$', firstName):
            negative = 'First Name must contain only characters!'
        elif not re.match(r'^[A-Za-z]+$', lastName):
            negative = 'Last Name must contain only characters!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            negative = 'Invalid email address!'
        elif password != passwordvalidation:
            negative = "Passwords don't match!"
        elif not firstName or not lastName or not email or not password or not passwordvalidation:
            negative = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into user table, with password encrypted
            cursor.execute('INSERT INTO user VALUES (NULL, %s, %s, %s, %s)', (firstName, lastName, email, generate_password_hash(password)))
            mysql.connection.commit()
            positive = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        negative = 'Please fill out the form!'
    # Show registration form with message
    return render_template('RegistrationForm.html', negative=negative, positive=positive)


# http://localhost:5000/Drunkfy/Home - this will be the home page
@app.route("/Drunkfy/Home")
def home():
    # Create variables for easy access
    firstname = session['name']
    lastname = session['lastname']
    # Create welcome message
    welcomeMsg = 'Welcome, ' + session['name']
    name = firstname + " " + lastname[0]
    # Show home page with messages
    return render_template("Home.html", welcomeMsg=welcomeMsg, name=name)

# http://localhost:5000/Drunkfy/Home/Search - this will be the hire a service page, we need to use both GET and POST requests
@app.route("/Drunkfy/Home/Search", methods=['GET', 'POST'])
def search():
    # Run query to get every non-onJourney driver from database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT CurrentLocation, FirstName, LastName, OverallRating FROM driver WHERE OnJourney=0")
    rows = cursor.fetchall()
    # Create data arrays
    locations = []
    firstname = []
    lastname = []
    rating = []
    # Append values to arrays
    for row in rows:
        locations.append(row['CurrentLocation'])
        firstname.append(row['FirstName'])
        lastname.append(row['LastName'])
        rating.append(row['OverallRating'])
    # Show search page and send available drivers information to page
    return render_template("Search.html", rows=rows, locations=locations, firstname=firstname, lastname=lastname, rating=rating)

# This will receive data that will be used to create SQL queries
@app.route('/_get_post_json/', methods=['POST'])
def get_post_json():
    # Get data
    data = request.get_json()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get driver id of a driver
    cursor.execute("SELECT DID FROM driver WHERE FirstName = %s", (data['name'],))
    row = cursor.fetchone()
    did = row['DID']
    # Insert row into userrequest table with request information
    cursor.execute("INSERT INTO userrequest VALUES (NULL, %s, %s, %s, %s, now(), now())", (did, session['id'], data['origin'], data['destination']))
    mysql.connection.commit()
    # Get request id of current request
    cursor.execute("SELECT RID FROM userrequest WHERE DID = %s AND UID = %s AND Pickup = %s AND Destination = %s AND RequestDate = curdate() AND RequestTime = curtime()", (did, session['id'], data['origin'], data['destination']))
    row = cursor.fetchone()
    rid = row['RID']
    cost = random.randint(1, 101)
    # Get last journey id and add 1 to create a new one in payment table
    cursor.execute("SELECT MAX(JID) FROM payment")
    row1 = cursor.fetchone()
    maxjid = row1['MAX(JID)']
    jid = maxjid + 1
    cursor.execute("INSERT INTO payment VALUES (NULL, %s, %s, True, %s)", (rid, cost, jid,))
    mysql.connection.commit()
    # Get payment id of current journey
    cursor.execute("SELECT PID FROM payment WHERE JID = %s", (jid,))
    row = cursor.fetchone()
    pid = row['PID']
    # Insert new journey data into journey table
    cursor.execute("INSERT INTO journey VALUES (NULL, %s, %s, %s, %s, curdate(), %s, %s)", (did, session['id'], data['origin'], data['destination'], data['pickup'], pid))
    mysql.connection.commit()
    # Return request successful
    return jsonify(status="success", data=data)

# This will be used to get the driver rating from feedback form
@app.route('/_get_feedback/', methods=['POST'])
def get_feedback():
    # Get rating
    data = request.get_json()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # Get journey id of the journey
    cursor.execute("SELECT MAX(JID) FROM journey")
    row = cursor.fetchone()
    jid = row['MAX(JID)']
    # Get driver id of the driver who did the journey and to who the rating is going to
    cursor.execute("SELECT DID FROM journey WHERE JID = %s", (jid,))
    row = cursor.fetchone()
    did = row['DID']
    # Insert rating into tblrating
    cursor.execute("INSERT INTO tblrating VALUES (%s, %s)", (jid, data['feedback'],))
    mysql.connection.commit()
    # Update driver's overall rating
    cursor.execute("UPDATE driver SET OverallRating =(SELECT AVG(rating) FROM tblRating INNER JOIN journey on tblRating.JID = journey.JID WHERE DID = %s) WHERE DID = %s", (did, did,)) #Update OverallRating in driver table
    mysql.connection.commit()
    # Return request successful
    return jsonify(status="success", data=data)

# This updates data in Myaccount section
@app.route("/Drunkfy/Home/Myaccount")
def myaccount():
    # Define global variables which will be used later on
    global fn, ln, eml, pwd
    # Get variables for easy access
    fn = session['name']
    ln = session['lastname']
    eml = session['email']
    pwd = session['password']
    # Return page with user's info
    return render_template("Myaccount.html", fn=fn, ln=ln, eml=eml)

# This is the page for Myaccount section, where user can alter his personal info
@app.route("/Drunkfy/Home/Myaccount", methods=['GET', 'POST'])
def savechanges():
    # Get messages
    negative = ""
    positive = ""
    # Check if "FirstName", "LastName" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'FirstName' in request.form and 'LastName' in request.form and 'email' in request.form:
        # Create variables for easy access
        id = session['id']
        firstName = request.form['FirstName']
        lastName = request.form['LastName']
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Validation checks
        if not firstName or not lastName or not email:
            negative = 'Please fill out the form!'
        elif not re.match(r'^[A-Za-z]+$', firstName):
            negative = 'First Name must contain only characters!'
        elif not re.match(r'^[A-Za-z]+$', lastName):
            negative = 'Last Name must contain only characters!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            negative = 'Invalid email address!'
        else:
            # If the form data is valid, now update user table
            cursor.execute("UPDATE user SET FirstName = %s, LastName = %s, Email = %s WHERE UID = %s", (firstName, lastName, email, id))
            mysql.connection.commit()
            positive = 'Changes successfully saved!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        negative = 'Please fill out the form!'
    # Show Myaccount page with personal info updated
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM user WHERE Email = %s", (email,))
    user = cursor.fetchone()
    session['name'] = user['FirstName']
    session['lastname'] = user['LastName']
    session['email'] = user['Email']
    myaccount()
    return render_template("Myaccount.html", fn=fn, ln=ln, eml=eml, pwd=pwd, negative=negative, positive=positive)

# This is the page where the user can change his password
@app.route("/Drunkfy/Home/Myaccount/Changepassword", methods=['GET', 'POST'])
def changepassword():
    # Get messages and current password
    negative = ""
    positive = ""
    currentpassword = session['password']
    # Check if "NewPassword" and "RepeatPassword" POST requests exist (user submitted form)
    if request.method == 'POST' and 'NewPassword' in request.form and 'RepeatPassword' in request.form:
        # Create variables for easy access
        id = session['id']
        password = request.form['NewPassword']
        password2 = request.form['RepeatPassword']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Validation checks
        if not password:
            negative = 'Please enter a new password!'
        elif not password2:
            negative = 'Please fill out both boxes!'
        elif password != password2:
            negative = "Passwords don't match!"
        elif check_password_hash(currentpassword, password):
            negative = "New password can't be the same as current one!"
        else:
            # If the form data is valid, now update password in user table
            cursor.execute("UPDATE user SET Pwd = %s WHERE UID = %s", (generate_password_hash(password), id,))
            mysql.connection.commit()
            positive = 'Password successfully updated!'
            cursor.execute("SELECT * FROM user WHERE Email = %s", (session['email'],))
            user = cursor.fetchone()
            session['password'] = user['Pwd']
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        negative = 'Please enter a new password!'
    # Show ChangePassword page with message
    return render_template("Changepassword.html", negative=negative, positive=positive)

# http://localhost:5000/Myaccount/logout - this will be the logout page
@app.route('/Drunkfy/Home/Myaccount/logout')
def logout():
# Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('name', None)
   session.pop('lastname', None)
   session.pop('email', None)
   session.pop('password', None)
   # Redirect to login page
   return redirect(url_for('login'))

# http://localhost:5000/Drunkfy/Home/Trips - this will be the user trips page
@app.route('/Drunkfy/Home/Trips')
def trips():
    # Get trips done by the user
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT journey.Pickup, journey.Destination, journey.JourneyDate, journey.PickupTime, payment.Jcost, tblrating.rating FROM journey INNER JOIN tblrating ON journey.JID=tblrating.JID INNER JOIN payment ON journey.JID=payment.JID WHERE UID = %s", (session['id'],))
    rows = cursor.fetchall()
    #Show page and send trips to html page
    return render_template("Trips.html", rows=rows)

# http://localhost:5000/Drunkfy/Home/PaymentDetails - this will be the user payment details page
@app.route('/Drunkfy/Home/Paymentdetails', methods=['GET', 'POST'])
def payment():
    # Get messages
    positive = ""
    negative = ""
    # Check if "CardHolder", "CardNumber", "ExpiryDate" and "SecretCode" POST requests exist (user submitted form)
    if request.method == 'POST' and 'CardHolder' in request.form and 'CardNumber' in request.form and 'ExpiryDate' in request.form and 'SecretCode' in request.form:
        # Create variables for easy access
        cardHolder = request.form['CardHolder']
        cardNumber = request.form['CardNumber']
        expiryDate = request.form['ExpiryDate']
        secretCode = request.form['SecretCode']
        # Check if card exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT CardNo FROM carddetails WHERE UID = %s', (session['id'],))
        card = cursor.fetchall()
        cardRegistered = False
        for row in card:
            if check_password_hash(row['CardNo'], cardNumber):
                cardRegistered = True

        # If card exists show error, if not, do validation checks
        if cardRegistered == True:
            negative = 'Card already registered!'
        elif not re.match(r'^((?:[A-Za-z]+ ?){1,3})$', cardHolder):
            negative = 'First Name must contain only characters!'
        elif not re.match(r'^(\d{16})$', cardNumber):
            negative = 'Card number must have 16 digits!'
        elif not re.match(r'^(0[1-9]|10|11|12)-2[0-9]$', expiryDate):
            negative = "Invalid expiry date! Make sure it's correct and in format MM-YY!"
        elif not re.match(r'^(\d{3})$', secretCode):
            negative = 'Secret code must have 3 digits!'
        elif not cardHolder or not cardNumber or not expiryDate or not secretCode:
            negative = 'Please fill out your card details!'
        else:
            # Card doesnt exists and the form data is valid, now insert new card into carddetails table
            cursor.execute('INSERT INTO carddetails VALUES (%s, %s, %s, %s, %s)', (generate_password_hash(cardNumber), session['id'], cardHolder, expiryDate, generate_password_hash(secretCode)))
            mysql.connection.commit()
            positive = 'Your card has successfully been added!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        negative = 'Please fill out your card details!'
    # Show page with message (if any) and send card info to html to display it in a table
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT CardNo, CardName, CardExpDate, CardSecretCode FROM carddetails WHERE UID=%s", (session['id'],))
    rows = cursor.fetchall()# data from database
    return render_template("paymentdetails.html", positive=positive, negative=negative, rows=rows)

# This will be used to delete a credit card if user wants to
@app.route('/deleterow/', methods=['POST'])
def deleterow():
    # Get data
    data = request.get_json()
    # Delete card from database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("DELETE FROM carddetails WHERE CardNo = %s AND UID = %s", (data['number'], session['id']))
    mysql.connection.commit()
    # Return request successful
    return jsonify(status="success", data=data)



if __name__ == "__main__":
    app.run("127.0.0.1", 5000)
