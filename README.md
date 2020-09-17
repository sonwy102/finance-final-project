# Finance 
Finance is a web application where users can buy and sell stocks.

## Disclaimer
This app was a final project for CS50 course. Parts of code were provided from the course. The code I wrote is labeled as so.

## Project Background
Finance is a Flask app that allows users to register an account and manage their stock porfolio. The app provides a front-end facing platform
for users to log in/out, look up a current stock quote, buy/sell stocks, view a history of transactions, and deposit a cash balance. Stock quote 
data was provided by IEX via IEX's stocks API.

## Specification

### `register`
`register` allows users to register their account using a HTML form. The form collects username and password from the userand loads the username 
and password hash into a sqlite database.

### `quote`
`quote` allows users to look up the current price of a stock. The route queries the IEX API for a current quote and displays it to the user.

### `buy`
`buy` allows users to buy stocks using a HTML form. The form collects the stock name and amount from user and updates their portfolio in the database.

### `index`
`index` is the homepage for logged-in users; it displays a table of their current portfolio and their cash balance.

### `sell`
`sell` allows users to buy stocks using a HTML form. The form collects the stock name and amount from user and updates their portfolio in the database.

### `history`
`history` allows users to access a list of all transactions they have made thus far. It queries the sqlite database to fetch this data in an 
updated fashion.

### `deposit`
`deposit` allows users to deposit a cash balance using a HTML form. The form collects the dollar amount (USD) and updates the user's portfolio in the database.

## Quickstart
Before running the app, be sure to register on IEX for an API key. Then, in AWE's IDE terminal, run
```
export API_KEY=value
```
where `value` is your API key.

To run the app, execute
```
flask run
```
in the terminal and go to the URL provided by Flask as the output.
