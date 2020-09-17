import os
import re

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
# Written by CS50
app = Flask(__name__)

# Ensure templates are auto-reloaded
# Written by CS50
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
# Written by CS50
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
# Written by CS50
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
# Written by CS50
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# Written by CS50
db = SQL("sqlite:///finance.db")

# Create additional tables and indexes in SQLite database
# Written by Wooyang Son
db.execute("CREATE TABLE IF NOT EXISTS purchases (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL, time DATETIME NOT NULL)")
db.execute("CREATE UNIQUE INDEX IF NOT EXISTS time_index ON purchases (time)")
db.execute("CREATE INDEX IF NOT EXISTS id_index ON purchases (user_id)")

db.execute("CREATE TABLE IF NOT EXISTS sales (user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL, time DATETIME NOT NULL)")
db.execute("CREATE UNIQUE INDEX IF NOT EXISTS time_index ON sales (time)")
db.execute("CREATE INDEX IF NOT EXISTS id_index ON sales (user_id)")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Homepage of CS50 Finance
# Written by Wooyang Son
@app.route("/")
@login_required
def index():
    # query user's purchases and sales
    purchases = db.execute(
        "SELECT symbol, SUM(shares) AS shares FROM purchases WHERE user_id = :user_id GROUP BY symbol", user_id=session["user_id"])
    sales = db.execute("SELECT symbol, SUM(shares) AS shares FROM sales WHERE user_id = :user_id GROUP BY symbol",
                       user_id=session["user_id"])

    # initializing variable(s)
    total = 0

    # Iterate through each purchase and update net_share to reflect any sales of the stock as well as get its current price and update the total value of the user's shares
    for i, value in enumerate(purchases):

        symboldict = lookup(purchases[i]['symbol'])

        # Get name of the stock
        purchases[i]['name'] = symboldict['name']

        # Update and get net shares of the stock that user owns
        for j, value in enumerate(sales):
            if purchases[i]['symbol'] == sales[j]['symbol']:
                purchases[i]['shares'] = (purchases[i]['shares']) + (sales[j]['shares'])

        # Get current price of stock
        purchases[i]['price'] = usd(symboldict['price'])

        # Get updated total value of stock shares that user owns
        purchases[i]['total'] = usd(symboldict['price'] * purchases[i]['shares'])

        # Sum up the total values of each stock to get total balance in portfolio from shares
        total = total + (symboldict['price'] * purchases[i]['shares'])

    # Query user's cash balance and display on the portfolio as 'CASH' at the end of table
    balance = db.execute("SELECT cash FROM users where id=:user_id", user_id=session["user_id"])
    cash = usd(balance[0]['cash'])
    purchases.append({'symbol': 'CASH', 'total': cash})

    # Add cash balance to total balance from shares and display at the end of table
    total = usd(total + balance[0]['cash'])
    purchases.append({'total': total})

    return render_template("index.html", purchases=purchases)

# Buy Page
# Written by Wooyang Son
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":

        symboldict = lookup((request.form.get("symbol")).upper())
        shares = float(request.form.get("shares"))

        # Ensure stock symbol is valid/exists
        if not symboldict:
            return apology("Invalid symbol", 403)

        # Ensure the number of shares user inputs is a positive integer
        elif not shares.is_integer() or shares < 1:
            return apology("Invalid shares", 403)

        # Eusure user has sufficient cash balance to make the purchase
        balance = db.execute("SELECT cash FROM users WHERE id = :user_id",
                             user_id=session["user_id"])
        if float(balance[0]['cash']) < (symboldict['price'] * shares):
            return apology("Insufficient balance", 403)

        # Update user's cash balance after purchase
        balance[0]['cash'] = float(balance[0]['cash']) - (symboldict['price'] * shares)

        # populate the purchase information into SQL database
        db.execute("INSERT INTO purchases (user_id, symbol, shares, price, time) VALUES (?,?,?,?,?)",
                   session["user_id"], symboldict["symbol"], shares, usd(symboldict['price']), (datetime.utcnow()))

        # update user's cash balance in SQL users table
        db.execute("UPDATE users SET cash = :cash WHERE id= :user_id", {"cash": balance[0]['cash'], "user_id": session['user_id']})

        return redirect("/")

    else:
        return render_template("buy.html")

# History Page
# Written by Wooyang Son
@app.route("/history")
@login_required
def history():
    # Query all purchases and sales user made in the past ordered chronologically
    history = db.execute(
        "SELECT symbol, shares, price, time FROM purchases WHERE user_id= :user_id UNION SELECT symbol, shares, price, time FROM sales WHERE user_id= :user_id ORDER BY time", user_id=session['user_id'])

    return render_template("history.html", history=history)

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# Logout Page
@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

# Quote Page
# Written by Wooyang Son
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":

        # Access the stock's info from API
        symboldict = lookup((request.form.get("symbol")).upper())

        # Ensure stock symbol is valid/exists
        if not symboldict:
            return apology("Invalid symbol", 403)

        # Display Quoted Page that displays information of the stock that user input in the form
        return render_template("quoted.html", name=symboldict["name"], price=usd(symboldict["price"]), symbol=symboldict["symbol"])

    else:
        return render_template("quote.html")

# Register Page
# Written by Wooyang Son
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords do not match", 403)

        # Query database for username to ensure the username doesn't already exist
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        if len(rows) != 0:
            return apology("username already exists", 403)

        # Add new user to users table in SQL
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashval)",
                   {"username": request.form.get("username"), "hashval": generate_password_hash(request.form.get("password"))})

        # Redirect user to Login Page
        return redirect("login.html")

    else:
        return render_template("register.html")

# Sell Page
# Written by Wooyang Son
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":

        # Ensure user provided a stock symbol
        if request.form.get("symbol") == "symbol":
            return apology("must provide symbol", 403)

        # Ensure user owns some shares of the stock that they are trying to sell
        purchases = db.execute("SELECT symbol, shares FROM purchases WHERE user_id = :user_id AND symbol = :symbol",
                               {"user_id": session["user_id"], "symbol": request.form.get("symbol")})
        if request.form.get("symbol").upper() != purchases[0]['symbol']:
            return apology("Stock doesn't exist in portfolio", 403)

        # Ensure user provided a positive integer for the number of shares
        shares = float(request.form.get("shares"))
        if not shares.is_integer() or shares < 1:
            return apology("Invalid shares", 403)

        # Ensure user has sufficient shares to sell
        if shares > purchases[0]['shares']:
            return apology("Insufficient shares in portfolio", 403)

        # Query cash balance from user and update it after making the sale
        balance = db.execute("SELECT cash FROM users WHERE id = :user_id",
                             user_id=session["user_id"])
        symboldict = lookup(request.form.get("symbol").upper())
        balance[0]['cash'] = float(balance[0]['cash']) + (symboldict['price'] * shares)

        # Populate the sale information into sales table in SQL
        db.execute("INSERT INTO sales (user_id, symbol, shares, price, time) VALUES (?,?,?,?,?)",
                   session["user_id"], symboldict["symbol"], (-shares), usd(symboldict['price']), (datetime.utcnow()))

        # Update user's cash balance in users table in SQL
        db.execute("UPDATE users SET cash = :cash WHERE id= :user_id", {"cash": balance[0]['cash'], "user_id": session['user_id']})

        # Redirect user to homepage
        return redirect('/')

    else:
        purchases = db.execute("SELECT symbol, shares FROM purchases WHERE user_id = :user_id GROUP BY symbol",
                               user_id=session["user_id"])
        return render_template("sell.html", purchases=purchases)

# Deposit Page
# Written by Wooyang Son
@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":

        # Ensure user provided input
        if not request.form.get("deposit"):
            return apology("must provide $ amount")

        # Ensure user provided a valid dollar amount (a number with max 2 digits after decimal point)
        if not re.search("^\d*(\.\d{0,2})?$", request.form.get("deposit")):
            return apology("invalid $ amount")

        # Ensure user entered an amount greater than 0
        if float(request.form.get("deposit")) <= 0:
            return apology("must enter amount greater than $0.00")

        # Query user's cash balance and update it after making the deposit
        balance = db.execute("SELECT cash FROM users WHERE id = :user_id",
                             user_id=session["user_id"])
        balance[0]['cash'] = float(balance[0]['cash']) + float(request.form.get("deposit"))
        db.execute("UPDATE users SET cash = :cash WHERE id= :user_id", {"cash": balance[0]['cash'], "user_id": session['user_id']})

        # Redirect user to homepage
        return redirect("/")

    else:
        return render_template("deposit.html")

# Written by CS50
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
# Written by CS50
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
