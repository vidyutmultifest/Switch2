import requests, datetime
from functools import wraps
from config import Config
from app import app, login
from flask import Blueprint, render_template, abort, redirect, request, url_for, jsonify
from jinja2 import TemplateNotFound
from app.models import User
from app.forms import AddTalk, AddWorkshop, MoreData, CABegin, CAQues, test, EduData, AmrSOY
from app.mail import farer_welcome_mail, amrsoy_reg_mail, testing_mail
from app.more import get_user_ip
from werkzeug.utils import secure_filename
from werkzeug.urls import url_parse
from flask_login import login_user, current_user, logout_user, login_required

farer = Blueprint('farer', __name__)

@login.user_loader
def load_user(id):
    
    # print("Loading user", id)
    if id is None:
        return None
    
    data = requests.get(Config.HUB_URL+'/farer/auth/user', headers={'Authorization':id})
    staff = requests.get(Config.HUB_URL+'/farer/staff', headers={'Authorization':id})
    
    if data.json().get('status') == 'fail':
        return None

    # print(data.json())
    # print(staff.json())
    
    user = User(id=id, data=data.json().get('data'), staff=staff.json())
    
    # print("End of loading user")
    
    return user

def f_login(request, point="None"):

    print("Inside authentication f_login")

    ip = get_user_ip(request)
    if current_user.is_authenticated:
        return jsonify(1)

    print("IDTOKEN = ", request.form['idtoken'])

    if request.method == 'POST':
        payload = {
            'idtoken': request.form['idtoken'],
            'user_ip': get_user_ip(request),
            'sender': 1
        }

        reply = requests.post(Config.HUB_URL+'/farer/auth/user', json=payload)
        print(reply.json())

        return reply

def staff_required(team="all", level=1):
    # Remember to not name any team as "all"
    def staff_required_wrap(func):
        @wraps(func)
        def d_view(*args, **kwargs):
            try:
                if current_user.super():
                    print("Super user. Yeah!")
                    return func(*args, **kwargs)
                elif current_user.staff == []:
                    print("No levels")
                    return redirect(url_for('home'))
                elif team=="all":
                    st = sorted(current_user.staff, key=lambda k: k['level'])
                    if st[0].get('level') < level:
                        print("No levels")
                        return redirect(url_for('home'))
                    return func(*args, **kwargs)
                else:
                    for i in current_user.staff:
                        if i.get('team') == team or i.get('team') == "web":
                            if i.get('level') >= level:
                                return func(*args, **kwargs)
                    print("Unauthorized within the team")
                    return redirect(url_for('home'))
            except Exception as e:
                print(e)
                # Send mail on the exception
                print("Exception occured")
                return redirect(url_for('home'))
            return func(*args, **kwargs)
        return d_view
    return staff_required_wrap

@farer.route('/logout/')
def logout():
    requests.post(Config.HUB_URL+'/farer/logout', headers={'Authorization':current_user.id})
    logout_user()
    print("Logging out user.")
    return redirect(url_for('home'))

@farer.route('/user/')
@login_required
def user_print():
    print(current_user.id)
    print("Email:", current_user.data.get('email'))
    return "User"

@farer.route('/tokensignin/', methods=['GET','POST'])
# Send G-ID for sigin
def loggingIn():
    
    print("Intiating login")
    if current_user.is_authenticated:
        print("Authenticated")
        return "Already authenticated"
    
    if request.method == 'POST':
        print("TESTING = ", request.form['idtoken'])
        print("PASSING TO F_LOGIN")
        reply_p = f_login(request).json()
        print("REPLY_P = ", reply_p)

        reply_g = requests.get(Config.HUB_URL+'/farer/auth/user', headers={'Authorization':reply_p.get('auth_token')})
        reply_g = reply_g.json()
        print("Reply-G", reply_g)
        print(reply_g.get('data'))

        u = User(id=reply_p.get('auth_token'), data=reply_g.get('data'))
        
        login_user(u, remember=True)
        
        return "Logged in"
    
    return "ERROR OCCURED DURING LOGIN"

@farer.route('/data/user/')
def farer_user():

    print("Inside Data farer")

    if current_user.is_authenticated:
        u = requests.get(Config.HUB_URL+'/farer/auth/user', headers={'Authorization':current_user.id})
        print(u.json())
        return jsonify(u.json().get('data'))

    return "false"

@farer.route('/details/')
@login_required
def farer_more():

    u = requests.get(Config.HUB_URL+'/farer/auth/user', headers={'Authorization':current_user.id})
    u = u.json().get('data')
    print(u)

    if u.get('detailscomp') is True:
        return render_template('index.html', page = "/home")
    return render_template('index.html', page = "/farer/forms/details")

@farer.route('/education/')
@login_required
def farer_education():
    
    u = requests.get(Config.HUB_URL+'/farer/auth/user', headers={'Authorization':current_user.id})
    u = u.json().get('data')
    print(u)

    if u.get('detailscomp') is None:
        return render_template('index.html',
                                page = "/farer/forms/details",
                                uchange="/farer/details/")
    if u.get('educomp') is True:
        return render_template('index.html',
                                page = "/home",
                                uchange="")

    return render_template('index.html',
                            page = "/farer/forms/education",
                            uchange="")
                            
@farer.route('/forms/details/', methods=['GET', 'POST'])
@login_required
def forms_farer_more():
    form = MoreData(request.form)

    if request.method == 'POST':

        print("Validation = " + str(form.validate()))
        if form.validate() == False:
            print(form.errors)
            return jsonify(form.errors)
        
        payload = {
            'fname': form.fname.data,
            'lname': form.lname.data,
            'phno': form.phno.data,
            'sex': form.sex.data,
            'referrer': form.referrer.data,
            'detailscomp': True
        }

        reply = requests.put(Config.HUB_URL+'/farer/user/details', json=payload,  headers={'Authorization':current_user.id})
        print("REPLY FOR DETAILS ( PUT REQUEST ) ", reply.json())

        return jsonify(reply.json().get('status'))

    return render_template('forms/details.html', user=current_user, form=form)

@farer.route('/forms/education/', methods=['GET', 'POST'])
@login_required
def forms_farer_edu():
    
    form = EduData(request.form)

    colleges = requests.get(Config.HUB_URL+'/college/list')
    colleges = colleges.json()

    if request.method == 'POST':

        print("Validation = " + str(form.validate()))

        if form.validate() == False:
            print(form.errors)
            return jsonify(form.errors)

        payload = {
            'course': form.course.data,
            'major': form.major.data,
            'college': form.college.data,
            'institution': form.institution.data,
            'year': form.year.data,
            'educomp': True
        }

        reply = requests.put(Config.HUB_URL+'/farer/user/education', json=payload, headers={'Authorization':current_user.id})
        
        print("REPLY FOR EDUCATION ( PUT REQUEST ) = ", reply.json())
        
        return jsonify(reply.json().get('status'))

    return render_template('forms/education.html', user=current_user, form=form, colleges=colleges)

@farer.route('/meta/user/', methods=['GET'])
def meta_user():
    
    mode = request.args.get('m')
    payload = {
        'vid': mode
    }
    meta = requests.get(Config.HUB_URL+'/farer/user/contact', json=payload)
    meta = meta.json()

    print(meta)

    return jsonify(meta)

@farer.route('/delete/<id>/')
# @level_required(15)
def delete_user(id):
    u = User.query.filter_by(id=id).first()
    v = AmrSoyParticipant.query.filter_by(id=id).first()
    w = CAData.query.filter_by(id=id).first()

    if u is not None:
        db.session.delete(u)
    if u is not None:
        db.session.delete(v)
    if w is not None:
        db.session.delete(w)
    db.session.commit()
    return ('', 204)