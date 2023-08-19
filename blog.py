from flask import Flask, render_template, redirect, flash, url_for, session, logging, request
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

app.secret_key = "myBlog"

#Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField(label = "İsim Soyisim", validators = [validators.Length(min=4,max=25), validators.DataRequired()])
    username = StringField(label = "Kullanıcı Adı", validators = [validators.Length(min=5,max=35), validators.DataRequired()])
    email = StringField(label = "Email adresi", validators = [validators.Email(message="Lütfen geçerli bir email adresi giriniz!")])
    password = PasswordField(label = "Parola: ", validators = [
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm", message="Parolanız Uyuşmuyor")
    ])
    confirm = PasswordField(label = "Parola Doğrula", validators = [validators.Length(min=4,max=25), validators.DataRequired()])

#Kullanıcı giriş formu
class LoginForm(Form):

    username = StringField(label = "Kullanıcı Adı")
    password = PasswordField("Password")

#Article ekleme formu
class ArticleForm(Form):

    title = StringField("Makale'nin Başlığı", validators= [validators.Length(min=5, max=100)])
    content = TextAreaField("Makale'nin İçeriği", validators=[validators.Length(min=10)])



app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog_users"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


#Decorator function for login needed pages
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız!", "danger")
            return redirect(url_for("login"))
    return decorated_function

@app.route("/")
def index():
    return render_template(template_name_or_list="index.html")

@app.route("/about")
def about():
    return render_template("about.html")

#Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    inquiry = "SELECT * FROM articles WHERE author = %s"

    result = cursor.execute(inquiry, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        cursor.close()

        return render_template("dashboard.html", articles=articles)
    else:
        return render_template("dashboard.html")

#Makale Ekleme
@app.route("/add_article", methods=["GET", "POST"])
def add_article():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        inquiry = "Insert into articles(title, author, content) VALUES(%s,%s,%s)"

        cursor.execute(inquiry, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_article.html", form = form)

#to show articles
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    inquiry = "SELECT * FROM articles"
    result = cursor.execute(inquiry)

    if result > 0:
        articles = cursor.fetchall()
        cursor.close()

        return render_template("articles.html", articles=articles)
    else:
        return render_template("articles.html")

#to reach articles
@app.route("/article/<string:ID>")
def article(ID):
    cursor = mysql.connection.cursor()
    inquiry = "SELECT * FROM articles WHERE ID = %s"

    result = cursor.execute(inquiry, (ID,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        return  render_template("article.html")

#Register part
@app.route(rule = "/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        inquiry = "INSERT into users(name, email, username, password) VALUES(%s,%s,%s,%s)"

        cursor.execute(inquiry, (name, email, username, password)) #if you gave one elemnt tuple to inquiry you should write like this: (name,)
        mysql.connection.commit()

        cursor.close()

        flash(message="Başarıyla kayıt oldunuz...", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)

#login
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()


        inquiry = "Select * From users where username = %s"

        outcome = cursor.execute(inquiry, (username,))

        if (outcome > 0):
            data = cursor.fetchone()
            real_password = data["password"]

            cursor.close()

            if sha256_crypt.verify(password_entered, real_password): #sürekli şifrenizi yanlış girdiniz hatası veriyor
                flash(message="Başarıyla giriş yaptınız!", category="success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))

            else:
                flash(message="Şifrenizi yanlış girdiniz...", category="danger")

                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor", "danger")
            return redirect(url_for("login"))



    return render_template("login.html", form = form)

# Logout
@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()

    flash("Başarıyla çıkış yaptınız...", "success")

    return redirect(url_for("index"))

#delete article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    inquiry = "SELECT * FROM articles WHERE author = %s and ID = %s"

    result = cursor.execute(inquiry,(session["username"], id))

    if result > 0:
        inquiry_2 = "DELETE FROM articles WHERE ID = %s"

        cursor.execute(inquiry_2, (id, ))
        mysql.connection.commit()

        flash("Makalenizi başarıyla sildiniz", "success")

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")

        return redirect(url_for("index"))

#update article
@app.route("/edit/<string:id>", methods=["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        inquiry = "SELECt * FROM articles WHERE ID=%s and author=%s"
        result = cursor.execute(inquiry, (id, session["username"]))

        if result == 0:
            flash("Böyle bir makale veritabanında bulunmuyor veya böyle bir işlem yapmaya yetkiniz yok!", "warning")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form=form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        inquiry = "UPDATE articles SET title=%s, content=%s where ID=%s"

        cursor = mysql.connection.cursor()

        cursor.execute(inquiry, (newTitle, newContent, id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi...", "success")

        return redirect(url_for("dashboard"))

#search
@app.route("/search", methods=["GET", "POST"])
def search():

    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        inquiry = f"SELECT * FROM articles WHERE title LIKE '%{keyword}%' "

        result = cursor.execute(inquiry)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı...", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles=articles)

if __name__ == "__main__":
    app.run(debug=True)