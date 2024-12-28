import random
import re
import string
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import MySQLdb

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 配置MySQL数据库连接
db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="xianyang245",
    db="bank"
)

# 定义全局变量
current_user_uid = None


@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    global current_user_uid
    uid = request.form['uid']
    upassword = request.form['upassword']
    cursor = db.cursor()
    cursor.execute("SELECT Utype FROM Users WHERE Uid=%s AND Upassword=%s", (uid, upassword))
    user = cursor.fetchone()
    if user:
        session['uid'] = uid
        session['utype'] = user[0]
        current_user_uid = uid
        if user[0] == '客户':
            return redirect(url_for('customer_home'))
        elif user[0] == '员工':
            return redirect(url_for('employee_home'))
        elif user[0] == '管理员':
            return redirect(url_for('admin_home'))
    else:
        flash("账号或密码错误，请重新输入", "error")
        return redirect(url_for('home'))


@app.route('/kehu/customer_home')
def customer_home():
    if 'uid' in session and session['utype'] == '客户':
        return render_template('kehu/customer_home.html', uid=session['uid'])
    return redirect(url_for('home'))
# @app.route('/kehu/customer_home')
# def customer_home():
#     if 'uid' in session and session['utype'] == '客户':
#         return render_template('kehu/customer_home.html')
#     return redirect(url_for('home'))

@app.route('/employee/employee_home')
def employee_home():
    if 'uid' in session and session['utype'] == '员工':
        return render_template('employee/employee_home.html',uid=session['uid'])
    return redirect(url_for('home'))

@app.route('/manager/admin_home')
def admin_home():
    if 'uid' in session and session['utype'] == '管理员':
        return render_template('manager/admin_home.html',uid=session['uid'])
    return redirect(url_for('home'))

######################客户界面######################
@app.route('/kehu/transfer')
def transfer():
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))
    return render_template('kehu/transfer.html')
#########
# ##获取所有Aid
# @app.route('/fetch_accounts', methods=['GET'])
# def fetch_accounts():
#     cursor = db.cursor()
#     cursor.execute("SELECT Aid FROM accounts")
#     accounts = cursor.fetchall()
#     cursor.close()
#     return jsonify([account[0] for account in accounts])
# ##获取与当前Uid关联的Aid
# @app.route('/fetch_customer_accounts', methods=['GET'])
# def fetch_customer_accounts():
#     if 'uid' not in session:
#         return redirect(url_for('home'))
#     uid = session['uid']
#     cursor = db.cursor()
#     cursor.execute("SELECT Aid FROM customers WHERE Uid=%s", (uid,))
#     accounts = cursor.fetchall()
#     cursor.close()
#     return jsonify([account[0] for account in accounts])
@app.route('/fetch_accounts', methods=['GET'])
def fetch_accounts():
    cursor = db.cursor()
    cursor.execute("SELECT Aid FROM accounts")
    accounts = cursor.fetchall()
    cursor.close()
    print("Accounts:", accounts)
    return jsonify([account[0] for account in accounts])

@app.route('/fetch_customer_accounts', methods=['GET'])
def fetch_customer_accounts():
    if 'uid' not in session:
        return redirect(url_for('home'))
    uid = session['uid']
    cursor = db.cursor()
    cursor.execute("SELECT Aid FROM customers WHERE Uid=%s", (uid,))
    accounts = cursor.fetchall()
    cursor.close()
    print("Customer Accounts for Uid", uid, ":", accounts)
    return jsonify([account[0] for account in accounts])

##获取指定账户的余额
@app.route('/fetch_account_balance/<int:aid>', methods=['GET'])
def fetch_account_balance(aid):
    cursor = db.cursor()
    cursor.execute("SELECT Abalance FROM accounts WHERE Aid=%s", (aid,))
    balance = cursor.fetchone()
    cursor.close()
    return jsonify(balance[0] if balance else 0)
##验证支付密码是否正确
@app.route('/validate_password', methods=['POST'])
def validate_password():
    data = request.json
    aid = data['aid']
    password = data['password']

    cursor = db.cursor()
    cursor.execute("SELECT Apassword FROM accounts WHERE Aid=%s", (aid,))
    actual_password = cursor.fetchone()
    cursor.close()

    return jsonify(password == actual_password[0] if actual_password else False)
@app.route('/kehu/payment_password')
def payment_password():
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))
    return render_template('kehu/payment_password.html')

##处理账户之间的转账请求
@app.route('/perform_transfer', methods=['POST'])
def perform_transfer():
    data = request.json
    from_account = data['from_account']
    to_account = data['to_account']
    amount = data['amount']
    print('from_account:',from_account,'to_account:',to_account,'amount:',amount)

    cursor = db.cursor()

    # Check balances and update accounts
    cursor.execute("SELECT Abalance FROM accounts WHERE Aid=%s", (from_account,))
    from_balance = cursor.fetchone()[0]
    print('from_balance:',from_balance)
    cursor.execute("SELECT Abalance FROM accounts WHERE Aid=%s", (to_account,))
    to_balance = cursor.fetchone()[0]
    print('to_balance:',to_balance)

    if from_balance < amount:
        return jsonify({'message': '余额不足'}), 400

    new_from_balance = from_balance - amount
    new_to_balance = to_balance + amount

    cursor.execute("UPDATE accounts SET Abalance=%s WHERE Aid=%s", (new_from_balance, from_account))
    cursor.execute("UPDATE accounts SET Abalance=%s WHERE Aid=%s", (new_to_balance, to_account))

    # Insert transaction record
    tid = ''.join(random.choices(string.digits, k=10))
    cursor.execute("INSERT INTO transactions (Tid, Tamount, FromAccount, ToAccount) VALUES (%s, %s, %s, %s)",
                   (tid, amount, from_account, to_account))

    db.commit()
    cursor.close()
    return jsonify({'message': '转账成功'})


######

##############
@app.route('/kehu/cards')
def cards():
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))

    uid = session['uid']
    cursor = db.cursor()
    cursor.execute("""
        SELECT accounts.Aid, accounts.Abalance 
        FROM accounts 
        JOIN customers ON accounts.Aid = customers.Aid 
        WHERE customers.Uid = %s
    """, (uid,))
    cards = cursor.fetchall()
    cursor.close()

    return render_template('kehu/cards.html', cards=cards)

##支付密码修改
@app.route('/kehu/set_password/<int:card_id>', methods=['GET', 'POST'])
def set_password(card_id):
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        cursor = db.cursor()
        cursor.execute("SELECT Apassword FROM accounts WHERE Aid = %s", (card_id,))
        account = cursor.fetchone()

        if account and account[0] == current_password:
            if new_password == confirm_password and new_password.isdigit() and len(new_password) == 6:
                cursor.execute("UPDATE accounts SET Apassword = %s WHERE Aid = %s", (new_password, card_id))
                db.commit()
                cursor.close()
                flash('支付密码修改成功！', 'success')
                return redirect(url_for('cards'))
            else:
                flash('新密码必须是6位数字且两次输入相同。', 'error')
        else:
            flash('当前密码错误。', 'error')
        cursor.close()

    return render_template('kehu/password_setting.html', card_id=card_id)


############
##########
@app.route('/kehu/user_setting', methods=['GET', 'POST'])
def user_setting():
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        print('new_password:',new_password)
        confirm_password = request.form['confirm_password']

        cursor = db.cursor()
        uid = session['uid']
        cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (uid,))
        account = cursor.fetchone()

        if account and account[0] == current_password:
            # 调试输出
            print("new_password:", new_password)
            print("Pattern match:", re.fullmatch(r'[A-Za-z0-9]{8,16}', new_password))

            if new_password == confirm_password and re.fullmatch(r'[A-Za-z0-9]{8,16}', new_password):
                cursor.execute("UPDATE users SET Upassword = %s WHERE Uid = %s", (new_password, uid))
                db.commit()
                cursor.close()
                flash('密码修改成功！', 'success')
                return render_template('kehu/user_setting.html', success=True)
            else:
                flash('新密码必须是8-16位且只能包含大小写字母或数字。', 'error')
        else:
            flash('当前密码错误。', 'error')
        cursor.close()

    return render_template('kehu/user_setting.html', success=False)
####################
####################
@app.route('/kehu/wealth')
def wealth():
    if 'uid' not in session or session['utype'] != '客户':
        return redirect(url_for('home'))

    cursor = db.cursor()
    uid = session['uid']
    # 查询用户所有持有的卡号
    cursor.execute("SELECT Aid FROM customers WHERE Uid = %s", (uid,))
    uid_accounts = [account[0] for account in cursor.fetchall()]

    # 确认查询到的用户账户
    print("uid_accounts:", uid_accounts)
    # 查询总余额
    cursor.execute("""
        SELECT SUM(accounts.Abalance)
        FROM accounts 
        JOIN customers ON accounts.Aid = customers.Aid 
        WHERE customers.Uid = %s
    """, (uid,))
    total_balance = cursor.fetchone()[0] or 0
    total_balance = f"{total_balance:.2f}"  # 保留两位小数

    # 查询交易记录
    cursor.execute("""
        SELECT Tid, Tamount, FromAccount, ToAccount 
        FROM transactions 
        WHERE FromAccount IN (SELECT Aid FROM customers WHERE Uid = %s)
           OR ToAccount IN (SELECT Aid FROM customers WHERE Uid = %s)
    """, (uid, uid))
    transactions = cursor.fetchall()
    print('transactions:',transactions)

    cursor.close()

    return render_template('kehu/wealth.html', total_balance=total_balance, transactions=transactions,
                           uid_accounts=uid_accounts)


####################员工界面##################
####################
@app.route('/employee/customer_management', methods=['GET', 'POST'])
def customer_management():
    if 'uid' not in session or session['utype'] != '员工':
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'u.Uid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(DISTINCT u.Uid)
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询客户信息
    query = f"""
        SELECT DISTINCT  u.Uid, c.Cname, c.Csex, c.Cphone, c.Cage
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    customers = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('employee/customer_management.html', customers=customers, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)


# 添加用于验证员工密码的路由
@app.route('/employee/verify_password', methods=['POST'])
def verify_password():
    if 'uid' not in session or session['utype'] != '员工':
        return jsonify({'error': '未登录或权限不足'})

    uid = session['uid']
    password = request.form['password']
    customer_uid = request.form['customer_uid']

    cursor = db.cursor()
    cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (uid,))
    employee_password = cursor.fetchone()[0]

    if password == employee_password:
        cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (customer_uid,))
        customer_password = cursor.fetchone()[0]
        cursor.close()
        return jsonify({'success': True, 'customer_password': customer_password})
    else:
        cursor.close()
        return jsonify({'success': False, 'error': '密码错误'})


# 添加用于筛选客户信息的路由
@app.route('/employee/filter_customers', methods=['POST'])
def filter_customers():
    if 'uid' not in session or session['utype'] != '员工':
        return redirect(url_for('home'))

    filter_column = request.form['filter_column']
    filter_value = request.form['filter_value']

    cursor = db.cursor()

    # 获取当前页码，默认为第一页
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 每页显示20条记录
    offset = (page - 1) * per_page

    # 根据筛选条件查询客户信息
    query = f"""
        SELECT users.Uid, customers.Cname, customers.Csex, customers.Cphone, customers.Cage
        FROM users
        JOIN customers ON users.Uid = customers.Uid
        WHERE users.Utype = '客户' AND {filter_column} LIKE %s
    """
    cursor.execute(query, (f"%{filter_value}%",))
    total_customers = cursor.fetchall()

    cursor.execute(query + f" LIMIT {per_page} OFFSET {offset}", (f"%{filter_value}%",))
    customers = cursor.fetchall()

    total_pages = len(total_customers) // per_page + (1 if len(total_customers) % per_page > 0 else 0)

    cursor.close()

    return render_template('employee/customer_management.html', customers=customers, page=page, total_pages=total_pages,
                           filter_column=filter_column, filter_value=filter_value)

#############################
@app.route('/employee/bank_account_management', methods=['GET', 'POST'])
def bank_account_management():
    if 'uid' not in session or session['utype'] != '员工':
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'u.Uid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        JOIN accounts a ON c.Aid = a.Aid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询客户账户信息
    query = f"""
        SELECT u.Uid, c.Cname, c.Aid, a.Abalance
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        JOIN accounts a ON c.Aid = a.Aid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    accounts = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('employee/bank_account_management.html', accounts=accounts, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)
##################################
###############################
@app.route('/employee/transaction_management', methods=['GET', 'POST'])
def transaction_management():
    if 'uid' not in session or session['utype'] != '员工':
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'Tid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM transactions
        WHERE {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询交易记录
    query = f"""
        SELECT Tid, Tamount, FromAccount, ToAccount
        FROM transactions
        WHERE {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    transactions = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('employee/transaction_management.html', transactions=transactions, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)


###############管理员界面#################
###############
@app.route('/manager/employee_management', methods=['GET', 'POST'])
def manager_employee_management():
    if 'uid' not in session or session['utype'] not in ['管理员']:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'u.Uid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM users u
        JOIN employees e ON u.Uid = e.Uid
        WHERE u.Utype IN ('员工', '管理员') AND {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询员工信息
    query = f"""
        SELECT u.Uid, e.Ename, e.Ephone, e.Eage, e.Epost
        FROM users u
        JOIN employees e ON u.Uid = e.Uid
        WHERE u.Utype IN ('员工', '管理员') AND {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    employees = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('manager/employee_management.html', employees=employees, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)
############################

@app.route('/manager/Atransaction_management', methods=['GET', 'POST'])
def Atransaction_management():
    if 'uid' not in session or session['utype'] != '管理员':
        return redirect(url_for('home'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'Tid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM transactions
        WHERE {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询交易记录
    query = f"""
        SELECT Tid, Tamount, FromAccount, ToAccount
        FROM transactions
        WHERE {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    transactions = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('manager/Atransaction_management.html', transactions=transactions, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)
###########################
@app.route('/manager/Abank_account_management', methods=['GET', 'POST'])
def Abank_account_management():
    if 'uid' not in session or session['utype'] != '管理员':
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'u.Uid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        JOIN accounts a ON c.Aid = a.Aid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询客户账户信息
    query = f"""
        SELECT u.Uid, c.Cname, c.Aid, a.Abalance
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        JOIN accounts a ON c.Aid = a.Aid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    accounts = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('manager/Abank_account_management.html', accounts=accounts, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)

@app.route('/manager/Avalidate_password', methods=['POST'])
def Avalidate_password():
    if 'uid' not in session or session['utype'] != '管理员':
        return jsonify({'error': '用户未登录或权限不足'}), 403

    admin_password = request.form['password']
    customer_uid = request.form['customer_uid']

    cursor = db.cursor()
    cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (session['uid'],))
    result = cursor.fetchone()
    cursor.close()

    if not result or result[0] != admin_password:
        return jsonify({'error': '管理员密码错误'}), 403

    cursor = db.cursor()
    cursor.execute("SELECT Apassword FROM customers,accounts WHERE customers.Aid=accounts.Aid and Uid = %s", (customer_uid,))
    customer_password = cursor.fetchone()[0]
    print(customer_password)
    cursor.close()

    return jsonify({'password': customer_password})



#############
@app.route('/manager/Acustomer_management', methods=['GET', 'POST'])
def Acustomer_management():
    if 'uid' not in session or session['utype'] != '管理员':
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    search_by = request.args.get('search_by', 'u.Uid')
    search_value = request.args.get('search_value', '')

    cursor = db.cursor()

    # 查询总记录数
    query_count = f"""
        SELECT COUNT(*)
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
    """
    cursor.execute(query_count, ('%' + search_value + '%',))
    total = cursor.fetchone()[0]

    # 查询客户信息
    query = f"""
        SELECT u.Uid, c.Cname, c.Csex, c.Cphone, c.Cage
        FROM users u
        JOIN customers c ON u.Uid = c.Uid
        WHERE u.Utype = '客户' AND {search_by} LIKE %s
        LIMIT %s OFFSET %s
    """
    cursor.execute(query, ('%' + search_value + '%', per_page, (page - 1) * per_page))
    customers = cursor.fetchall()

    cursor.close()

    total_pages = (total // per_page) + (1 if total % per_page > 0 else 0)

    return render_template('manager/Acustomer_management.html', customers=customers, page=page, total=total, total_pages=total_pages, search_by=search_by, search_value=search_value)

@app.route('/manager/Avalidate_password_customer', methods=['POST'])
def Avalidate_password_customer():
    if 'uid' not in session or session['utype'] != '管理员':
        return jsonify({'error': '用户未登录或权限不足'}), 403

    admin_password = request.form['password']
    customer_uid = request.form['customer_uid']

    cursor = db.cursor()
    cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (session['uid'],))
    result = cursor.fetchone()
    cursor.close()

    if not result or result[0] != admin_password:
        return jsonify({'error': '管理员密码错误'}), 403

    cursor = db.cursor()
    cursor.execute("SELECT Upassword FROM users WHERE Uid = %s", (customer_uid,))
    customer_password = cursor.fetchone()[0]
    cursor.close()

    return jsonify({'password': customer_password})



###################

if __name__ == "__main__":
    app.run(debug=True)

