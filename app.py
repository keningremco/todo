from functools import wraps
from flask import Flask, render_template, url_for, session, redirect, request
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pymysql
import os

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "userid" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    connection = pymysql.connect(
        host="localhost",
        user=os.getenv('USER'),
        password=os.getenv('WACHTWOORD'),
        database="todo",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    return connection

@app.route("/")
@app.route("/label/<label>")
@login_required
def home(label=None):
    db = get_db_connection()
    cursor = db.cursor()
    if label == None:
        query = """
            SELECT * FROM todo t
        """
        cursor.execute(query)
        todos = cursor.fetchall()
    else:
        query = """
            SELECT * FROM todo t
            JOIN todo_label tl ON t.id = tl.todo_id
            JOIN label l ON tl.label_id = l.id
            WHERE l.naam = %s
        """
        cursor.execute(query, (label,))
        todos = cursor.fetchall()

    query = """
        SELECT * FROM label l
        JOIN todo_label tl ON l.id = tl.label_id
    """
    cursor.execute(query)
    labels = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("index.html", todos=todos, labels=labels)

@app.route('/login', methods=['POST', "GET"])
def login():
    error = ''
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        db = get_db_connection()
        cursor = db.cursor()

        query = """
            SELECT * FROM users
            WHERE username = %s
        """
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        
        cursor.close()
        db.close()
        
        if not user:
            error = 'gebruiker bestaat niet'
            
            return render_template('login.html', error=error)
        if password == user['password']:
            session['userid'] = user['userid']
            session['username'] = user['username']
            return redirect(url_for('home'))
        elif password != user['password']:
            error = 'verkeerde wachtwoord'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/new')
@login_required
def new():
    return render_template('new.html')

@app.route('/makepost', methods=['POST'])
@login_required
def makepost():
    userid = session.get('userid')
    titel = request.form.get('titel')
    bijschrift = request.form.get('bijschrift')
    image = request.files.get('photo')

    if not titel:
        titel = 'geen titel'

    if not image:
        return "Geen afbeelding ontvangen", 400

    if image.filename == "":
        return "Geen bestand geselecteerd", 400

    # Veilige bestandsnaam
    filename = secure_filename(image.filename)

    # Zorg dat map bestaat
    upload_folder = os.path.join('static', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, filename)

    image.save(filepath)

    db = get_db_connection()
    cursor = db.cursor()

    query = """
        INSERT INTO todo (makerid, titel, image, bijschrift, gedaan)
        VALUES (%s, %s, %s, %s, 0)
    """
    cursor.execute(query, (userid, titel, filename, bijschrift))
    db.commit()
    cursor.close()
    db.close()

    return redirect(url_for('home'))

@app.route('/deletepost/<id>')
@login_required
def deletepost(id):
    db = get_db_connection()
    cursor = db.cursor()

    query = 'DELETE FROM todo WHERE id = %s'
    cursor.execute(query, (id,))

    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('home'))

@app.route('/makelabel', methods=['POST'])
@login_required
def makelabel():
    label = request.form.get('label')
    todoid = request.form.get('id')
    make_label(label)
    return redirect(url_for('home'))

def make_label(label):
    db = get_db_connection()
    cursor = db.cursor()
    query = 'SELECT * FROM label WHERE naam = %s'
    cursor.execute(query, (label,))
    if not cursor.fetchone():
        query = "INSERT INTO label (naam) VALUES (%s)"
        cursor.execute(query, (label,))
        db.commit()
    cursor.close()
    db.close()

@app.route('/addlabel', methods=['POST'])
@login_required
def addlabel():
    label = request.form.get('label')
    todoid = request.form.get('id')
    db = get_db_connection()
    cursor = db.cursor()

    make_label(label)

    query = "SELECT * FROM label WHERE naam = %s"
    cursor.execute(query, (label,))
    label_id = cursor.fetchone()['id']
    query = "INSERT INTO todo_label (todo_id, label_id) VALUES (%s, %s)"
    cursor.execute(query, (todoid, label_id))
    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('home'))



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6236, debug=True)