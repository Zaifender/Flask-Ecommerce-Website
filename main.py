from flask import Flask,redirect,render_template,url_for,flash,session,request
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,login_required,login_user,logout_user,LoginManager,current_user,fresh_login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField,FileRequired,FileAllowed
from wtforms import StringField,PasswordField,ValidationError,SubmitField,FloatField,TextAreaField
from wtforms.validators import InputRequired
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "jojo"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nile.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))

class users(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String,unique=True)
    password = db.Column(db.String)
    role = db.Column(db.String)

    def __init__(self,name,password,role):
        self.name = name
        self.password = password
        self.role = role

class products(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String,db.ForeignKey('users.name'))
    pname = db.Column(db.String)
    desc = db.Column(db.String)
    price = db.Column(db.Integer)
    review = db.Column(db.Boolean)
    ipath = db.Column(db.String)
    
    def __init__(self,name,pname,desc,price,review,ipath):
        self.name = name
        self.pname = pname
        self.desc = desc
        self.price = price
        self.review = review
        self.ipath = ipath

class registerform(FlaskForm):
    username = StringField(validators=[InputRequired()],
                            render_kw={"placeholder":"username"})
    password = PasswordField(validators=[InputRequired()],
                            render_kw={"placeholder":"password"})
    cpassword = PasswordField(validators=[InputRequired()],
                            render_kw={"placeholder":"confirm password"})
    submit = SubmitField("Sign Up")

    def validate_user(self,username):
        user_found= users.query.filter_by(name=username).first()
        if user_found:
            raise ValidationError("User Already Exists")
        
class loginform(FlaskForm):
    username = StringField(validators=[InputRequired()],
                            render_kw={"placeholder":"username"})
    password = PasswordField(validators=[InputRequired()],
                            render_kw={"placeholder":"password"})
    submit = SubmitField("Log In")

class uplaodproduct(FlaskForm):
    pname = StringField(validators=[InputRequired()],
                            render_kw={"placeholder":"Product Name"})
    desc = TextAreaField(validators=[InputRequired()],
                            render_kw={"placeholder":"description of the product"})
    price = FloatField(validators=[InputRequired()],
                            render_kw={"placeholder":"Price of the product"})
    image = FileField('Product Image', validators=
                    [FileAllowed(['jpg', 'png', 'jpeg', 'gif', 'webp'],'Images only!')])
    submit = SubmitField("UPLOAD")

def save_image(form_image):
    if form_image and form_image.filename:

        original_filename = secure_filename(form_image.filename)
        file_extension = os.path.splitext(original_filename)[1]
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        new_filename = f"{timestamp}{file_extension}"
        
        uploads_dir = os.path.join(app.config['UPLOAD_FOLDER']) 
        
        os.makedirs(uploads_dir, exist_ok=True)
        
        file_path = os.path.join(uploads_dir, new_filename)
        
        form_image.save(file_path)
        
        return f"/{new_filename}"
    
    return None

def dictpro(all_product):
    P = []
    for i in all_product:
        if len(i.desc)>120:
            i.desc = i.desc[:120]+ "...."
        p = {"name":i.name,"pname":i.pname,"desc":i.desc,"price":i.price,"ipath":i.ipath,"review":i.review,"id":i.id}
        P.append(p)
    return P

@app.route('/')
def home():
    all_products = products.query.all()
    cards = dictpro(all_products)

    tag = request.args.get("tag")
    print(tag)
    if tag:
        filtered = products.query.filter(products.name.ilike(f"%{tag}%") | products.desc.ilike(f"%{tag}%")).all()
        fcards = dictpro(filtered)
        return render_template("index.html",cards=fcards)

    return render_template("index.html",cards=cards)
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = loginform()
    password = form.password.data
    user = users.query.filter_by(name=form.username.data).first()
    if not current_user.is_authenticated:
        if form.validate_on_submit():
            if user:
                if user.password==password:
                    login_user(user)
                    flash("Logged in Successfully!")
                    return redirect(url_for("home"))
                else:
                    flash("Incorrect Password!")
            else:
                flash("User not found!")
    else:
        flash("Already logged in!")
        return redirect(url_for("home"))
    return render_template("login.html",form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = registerform()

    name = form.username.data
    password = form.password.data
    cpassword = form.cpassword.data

    user = users.query.filter_by(name=name).first()
    if not current_user.is_authenticated:
        if form.validate_on_submit():
            if not user:
                if cpassword==password:
                    user = users(name=name,password=password,role="user")
                    db.session.add(user)
                    db.session.commit()
                    flash("Registed Successful! Please login to continue")
                    return redirect(url_for("login"))
                else:
                    flash("Confirm Password does not match!")
            else:
                flash("User is Already Registered!")
    else:
        flash("You have to logout first to register yourself!")
        return redirect(url_for("home"))
    return render_template("register.html",form=form)

@app.route('/addproduct', methods=['GET', 'POST'])
def addproduct():
    if current_user.role=="seller" or current_user.role=="admin":

        form = uplaodproduct()
        pname = form.pname.data
        desc = form.desc.data
        price = form.price.data
        ipath = None
        if form.image.data:
            ipath = save_image(form.image.data)

            if form.validate_on_submit():
                pro = products(name=current_user.name,pname=pname,desc=desc,price=price,review=None,ipath=ipath)
                db.session.add(pro)
                db.session.commit()

                flash("Uploaded succesfully")
                return redirect(url_for("home"))
        else:
            print("file not found!")
    else:
        flash("You can not Access this Page!")
        return redirect(url_for("home"))

    return render_template("addproduct.html",form=form)

@app.route('/product/<int:id>', methods=['GET', 'POST'])
def viewproduct(id):
    i = products.query.get(id)
    p = {"name":i.name,"pname":i.pname,"desc":i.desc,"price":i.price,"ipath":i.ipath,"review":i.review,"id":i.id}
    return render_template("product.html",data=p)

@app.route('/buy/<int:id>', methods=['GET', 'POST'])
@login_required
def buyitem(id):
    i = products.query.get(id)
    

    flash("You just ordered the item!")
    return redirect(url_for("home")) #change

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    pass

@app.route('/admin',methods=["POST","GET"])
def admin():
    if current_user.is_authenticated and current_user.role=="admin":
            all_products = products.query.all()
            cards = dictpro(all_products)
            return render_template("admin.html",cards=cards)
    else:
        flash("Access Denied to Admin Portal")
        return redirect(url_for("home"))


@app.route('/admin/login', methods=['GET', 'POST'])
def adminlogin():
    form = loginform()
    password = form.password.data
    user = users.query.filter_by(name=form.username.data,role="admin").first()
    if not current_user.is_authenticated: 
        if form.validate_on_submit():
            if user:
                if user.password == password:
                    login_user(user)
                    flash("Admin logged in Successfully!")
                    return redirect(url_for("admin"))
                else:
                    flash("Incorrect Password!")
            else:
                flash("Admin not found!")
    else:
        logout_user()
        flash("You have been logged out, Now login with Admin Account!")
    return render_template("admin_login.html",form=form)

@app.route('/admin/register', methods=['GET', 'POST'])
def adminregister():
    form = registerform()
    name = form.username.data
    password = form.password.data
    cpassword = form.cpassword.data

    user = users.query.filter_by(name=name).first()
    if form.validate_on_submit():
        if not user:
            if cpassword==password:
                user = users(name=name,password=password,role="admin")
                db.session.add(user)
                db.session.commit()
                flash("Admin Registed Successful! Please login to continue")
                return redirect(url_for("adminlogin"))
            else:
                flash("Confirm Password does not match!")
        else:
            flash("Username is Already Registered!")
    
    return render_template("admin_register.html",form=form)

@app.route('/admin/edit',methods=["POST","GET"])
def adminedit():
    if current_user.is_authenticated and current_user.role=="admin":
            all_products = products.query.all()
            cards = dictpro(all_products)

            return render_template("admin_edit.html",cards=cards)
    else:
        flash("Access Denied to Admin Portal")
        return redirect(url_for("home"))
    
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def admineditpost(id):
    product = products.query.get(id)

    form = uplaodproduct(obj=product)
    if current_user.is_authenticated and current_user.role=="admin":
        if form.validate_on_submit():
            if product:
                form.populate_obj(product)
                db.session.commit()
                flash("Details Updated!")
                return redirect(url_for("adminedit"))
            else:
                flash("Product not found")
                return redirect(url_for("adminedit"))
    else:
        flash("Access Denied to Admin Portal")
        return redirect(url_for("home"))
    
    return render_template("addproduct.html",form=form)
    
@app.route('/admin/delete/<int:id>',methods=['POST','GET'])
def delete(id):
    if current_user.is_authenticated and current_user.role=="admin":
        product = products.query.filter_by(id=id).first()
        if product:
            db.session.delete(product)
            db.session.commit()
            return redirect(url_for("adminedit"))
        else:
            flash("Product not found")
            return redirect(url_for("adminedit"))
    else:
        flash("Access Denied to Admin Portal")
        return redirect(url_for("home"))

@app.route('/seller', methods=['GET', 'POST'])
def seller():
    form = registerform()
    username = form.username.data
    password = form.password.data
    cpassword = form.cpassword.data

    if form.validate_on_submit():
        if cpassword==password:
            user = users.query.filter_by(name=username).first()
            if not user:
                us = users(name=username,password=password,role="seller")
                db.session.add(us)
                db.session.commit()

                flash("Seller Registered Successfully! You can Login in now")
                return redirect("login")

            else:
                if user.role=="seller":
                    flash("Seller Already Registered!")
                else:
                    user.role = "seller"
                    db.session.commit()
                    flash("Seller Registered Successfully! You can Login in now")
                    logout_user()
                    return redirect("login")
        else:
            flash("Confirm Password does not match!")
    return render_template("seller.html",form=form)

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash("Logged Out Successfully!")
    return redirect(url_for("home"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True) 