
from DBmanager import DBmanager

from pprint import pprint
import random
from flask import Flask, redirect, render_template, request, url_for, session, flash

from dotenv import load_dotenv, find_dotenv
from os import environ as env

app = Flask(__name__)
app.debug = False
# app.config['SESSION_TYPE'] = 'filesystem'


# Dotenv
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
app.secret_key = env.get('SECRET_KEY')

# Database
db = DBmanager( env )

# DONE
# questions in google sheets
# request to google sheets in generate_quest
# question hovers over Pytanie 0, Pytanie 1...
# verdict and save to google sheets
# collection table
# lvl increases the chance of getting more rare pokemon
# block collecion while game is on
# trainer: check if 1.5 hasn't passed since the last call
# pokemon image frame
# border match colors
# color palettes
# Pytanie 0, 1, 2...
# ability to manually remove time restriction
# basic answers parser


# TODO FATURES
# button -> rate the coolness
# better tooltips, separate window maybe?
# email when somebody catches a poke
# złapane border
# change flash front
# split CSS into different logical files
# 7&8 gen pokenoms
# better easy/medium/hard split
# animation
# copyright footer
# add poke level to collection (save it to db as well)
# admin page?

# TODO BUGS
# !!! remove ENV from github !!!
# shifted pokenames in collection (bug)
# make code box larger 
# logout can refresh pokemon (bug)



# BUG: google.auth.exceptions.RefreshError: ('invalid_grant: Invalid JWT
# SOLUTION: change system clock




@app.before_first_request
def initial_values():
    session.clear()

    # session['username'] = 'ooo'
    
    session['language'] = 'PL'



''' INDEX PAGE '''

@app.route('/', methods=['GET'])
def index():
    return render_template(
        'index.html',
        username = session.get('username')
    )



''' SIGNUP '''

@app.route('/signup', methods=['GET'])
def signup_page():
    # session['last_page'] = url_for('signup_page')
    return render_template(
        'signup.html',
        username = session.get('username')
    )

@app.route('/signup', methods=['POST'])
def new_user():

    flashes = db.create_user( request.form )
    if flashes:
        for f in flashes:
            flash( f )
        return redirect( url_for('signup_page') )
    else:
        flash( f'Zarejestrowano użytkownika {request.form.get("username")}' )
        return redirect( url_for('login_page') )




''' LOGIN '''

@app.route('/login', methods=['GET'])
def login_page():
    return render_template(
        'login.html',
        username = session.get('username')
    )


@app.route('/login', methods=['POST'])
def login_as_user():
    
    username = request.form.get('username')
    hashed = db.custom_hash( request.form.get('password') )

    existing_user = db.get_users_dict().get( username )

    if existing_user and (hashed == existing_user['hashed']):

        session['username'] = username

        flash( f'Witaj, {username}!' )
        return redirect( url_for('index') )

    else:
        flash( f'Niepoprawna nazwa użytkownika albo hasło' )
        flash( f'Duże i małe litery zawsze grają rolę' )
        return redirect( url_for('login_page') )

    

''' LOGOUT '''

@app.route('/logout', methods=['GET'])
def logout():

    if not session.get('username'):
        flash( 'Zaloguj się najpierw' )
        return redirect( url_for('login_page') )

    flash( f'Wylogowano użytkownika {session["username"]}' )
    
    lang = session.get('language')
    session.clear()
    session['language'] = lang
    
    return redirect( url_for('login_page') )




''' LANG '''

@app.route('/change_language', methods=['GET'])
def change_language():
    
    if session['language'] == 'ENG':
        session['language'] = 'PL'
    else:
        session['language'] = 'ENG'
    print('lang changed')
    return redirect( url_for('index') )



''' PYTHON TRAINER '''

@app.route('/python_trainer', methods=['GET', 'POST'])
def python_trainer():

    session['too_fast'] = False
    target = 'python_trainer.html'
    username = session.get('username')


    if not username:
        flash( 'Zaloguj się aby uzyskać dostęp do gier' )
        return redirect( url_for('login_page') )

    elif db.too_fast( username ):
        session['too_fast'] = True

    elif request.method == 'POST':

        if not session.get('game'):
            return redirect(url_for('login_page'))

        session['answers'][ session['no'] ] = request.form.get('answer')

        page = request.form.get('page')
        if page:
            session['no'] = int(page)


        if request.form.get('submit'):

            for i, ans in enumerate( session['answers'] ):
                if ans == '':
                    flash( 'Jeszcze nie podałeś wszystkich odpowiedzi' )
                    return redirect( url_for('python_trainer') )

            # Workaround because flask doesn't keep session after redirect (wtf?)
            target = 'result.html'
            
            # End of the game
            db.add_poke_to_collection( session )
            session['game'] = False

            

    return render_template(
        target,
        username=username,
        game=session.get('game'),
        img_url=session.get('img_url'),
        rarity=session.get('rarity'),
        pokename=session.get('pokename'),
        questions=session.get('three'),
        no=session.get('no'),
        answers=session.get('answers'),
        good=session.get('good'),
        correct_string=session.get('correct_string'),
        verdict=session.get('verdict'),
        too_fast=session.get('too_fast')
    )




@app.route('/generate_quest', methods=['POST'])
def generate_quest():

    session['game'] = True

    lvl = request.form.get('action')
    
    pokename, img_url, rarity = db.get_random_poke( lvl )
    
    session['pokename'] = pokename.upper()
    session['img_url'] = img_url
    session['rarity'] = rarity
    session['three'] = db.random_three( lvl )
    session['no'] = 0
    session['answers'] = [ '', '', '' ]

    return redirect( url_for('python_trainer') )



''' ACCOUNT '''

@app.route('/account', methods=['GET'])
def account_page():
    
    username = session.get('username')

    if not username:
        flash( 'Zaloguj się najpierw' )
        return redirect( url_for('login_page') )

    return render_template( 'account.html', username = username )



''' COLLECTION '''

@app.route('/collection', methods=['POST'])
def collection_vs_history():

    session['account_choice'] = request.form.get('action')
    return redirect( url_for('collection_history_page') )



@app.route('/collection', methods=['GET'])
def collection_history_page():


    username = session.get('username')

    if not username:
        flash( 'Zaloguj się najpierw' )
        return redirect( url_for('login_page') )

    only_catched = session.get('account_choice') == 'collection'

    userpoke = db.get_userpoke_list( username, only_catched=only_catched )

    for poke in userpoke:
        poke['questions'] = [
            db.quest_ID_dict[ qID ] for qID in poke['qIDs']
        ]

    return render_template('collection.html',
        game = session.get('game'),
        username = username,
        userpoke = list(reversed(userpoke)),
        nopoke = len(userpoke)==0
    )





if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
    
    # for i in range(100):
    #     _, _, target = db.get_random_poke('hard')
    #     print(target)
