from pprint import pprint
import datetime
import random
import ast
import requests
import hashlib
import gspread
from oauth2client.service_account import ServiceAccountCredentials



class DBmanager():


    def __init__(self, env):
        
        self.client = self.__authorize( env )
        self.workspace = self.client.open("PythonTrainer")
        self.POKE_API_URL = "https://pokeapi.co/api/v2/pokemon/"

        self.record_model = [ 'good', 'pokename', 'verdict', 'answers', 'img_url', 'datetime', 'qIDs' ]

        self.mapping = {
            'easy': {'easy':2, 'medium': 1},
            'medium': {'easy':1, 'medium': 1, 'hard': 1},
            'hard': {'hard':2, 'medium': 1}
        }
        self.pool2rarity = {
            'easy': 'zwykły',
            'medium': 'niezwykły',
            'hard': 'rzadki'
        }
        self.lvl2pokepool = {
            'easy': ['easy'],
            'medium': ['easy', 'medium'],
            'hard': ['easy', 'medium', 'hard']
        }

        self.poke_sheet = self.workspace.worksheet( 'Pokemon' )
        self.poke_dict = self.__get_poke_dict()

        self.quest_sheet = self.workspace.worksheet( 'Questions' )
        self.quest_dict, self.quest_ID_dict = self.__get_quest_dict()
        
        self.users_sheet = self.workspace.worksheet( 'Users' )
        self.users_dict = self.get_users_dict()

        self.COOLDOWN_MIN = 70


    def __get_quest_dict(self):

        questions = self.quest_sheet.get_all_values()
        quest_dict = { lvl:[] for lvl in ['easy', 'medium', 'hard'] }
        quest_ID_dict = {}

        for q in questions:

            if any([ q[i] == '' for i in range(5) ]):
                continue

            qobj = {
                'ID': q[0],
                'question': q[2],
                'code': q[3],
                'lines': q[3].count('\n') + 2,
                # 'answers': [ a for a in q[4:] if a != '' ]
                'answers': q[4]
            }

            quest_dict[ q[1] ].append( qobj )
            quest_ID_dict[ q[0] ] = qobj

        return quest_dict, quest_ID_dict


    def __get_poke_dict(self):

        poke = self.poke_sheet.get_all_values()        
        headers = poke[0]
        poke_dict = { h:[] for h in headers }
        
        for row in poke[1:]:
            for header, pokename in zip( headers, row ):
                if pokename != '':
                    poke_dict[ header ].append( pokename )

        return poke_dict


    def get_users_dict(self):
        
        users = self.users_sheet.get_all_values()
        users_dict = {}
        for row in users:
            if row:

                username = row[0]
                userhash = row[1]

                # User model
                users_dict[ username ] = {
                    'hashed': userhash,
                    'pokelen': 0
                }

                if len(row) > 3:    
                    for pokestring in row[3:]:
                        if len(pokestring) > 1:
                            users_dict[ username ]['pokelen'] += 1
        return users_dict


    def __authorize(self, env):

        scope = [
            env.get('scope_1'),
            env.get('scope_2')
        ]

        client_dict = {
            'type': env.get( 'type' ),
            'project_id': env.get( 'project_id' ),
            'private_key_id': env.get( 'private_key_id' ),
            'private_key': env.get( 'private_key' ),
            'client_email': env.get( 'client_email' ),
            'client_id': env.get( 'client_id' ),
            'auth_uri': env.get( 'auth_uri' ),
            'token_uri': env.get( 'token_uri' ),
            'auth_provider_x509_cert_url': env.get( 'auth_provider_x509_cert_url' ),
            'client_x509_cert_url': env.get( 'client_x509_cert_url' )
        }

        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            client_dict,
            scopes=scope
        )

        return gspread.authorize( creds )



    def custom_hash( self, plain ):
        return str(int(hashlib.sha256( plain.encode('utf-8') ).hexdigest(), 16) % 10**8)


    # Get three random pokemon according to game level
    def random_three( self, lvl ):
        
        counter = self.mapping[ lvl ]
        three = []

        for category, howmany in counter.items():
            qlist = self.quest_dict[category]
            random.shuffle( qlist )
            for i in range(howmany):
                three.append( qlist[i] )

        return three


    def create_user(self, userdata):

        username = userdata.get('username')
        hashed = self.custom_hash( userdata.get('password') )
        hashed2 = self.custom_hash( userdata.get('password2') )
        
        flashes = []

        users_dict = self.get_users_dict()

        # Fields validation
        if len(username) < 3:
            flashes.append( 'Nazwa użytkownika ma mieć minimum 3 znaki' )

        if username in users_dict.keys():
            flashes.append( 'Nazwa użytkownika jest zajęta' )
            
        if len(userdata.get('password')) < 8:
            flashes.append( 'Hasło ma mieć minimum 8 znaków' )

        if hashed != hashed2:
            flashes.append( 'Hasła muszą się zgadzać' )

        if flashes:
            return flashes
        else:
            newrow = [ username, hashed, '' ]
            
            self.users_sheet.insert_row( newrow, len(users_dict) + 1 )
            # self._update_users_locally()



    def get_random_poke( self, lvl ):

        pokepool = self.lvl2pokepool[ lvl ]

        # Some names are not fetchable from PokeAPI
        while True:
            pool = random.choice(pokepool)
            rarity = self.pool2rarity[ pool ]
            pokename = random.choice( self.poke_dict[ pool ] )
            r = requests.get( self.POKE_API_URL + pokename )
            try:
                img_url = r.json()["sprites"]["front_default"]
                return pokename, img_url, rarity
            except:
                continue


    # Parser...?
    # https://stackoverflow.com/questions/8982163/how-do-i-tell-python-to-convert-integers-into-words
    def is_correct( self, answer, acceptable ):

        # print( f'{answer} in {acceptable}' )
        ans_list = [ a.strip() for a in acceptable.split(',') ]
        answer = answer.strip()
        # answer = answer.lower()
        if answer[0] == '\'' and answer[-1] == '\'':
            answer = answer[1:-1]
        elif answer[0] == '\"' and answer[-1] == '\"':
            answer = answer[1:-1]

        if ',' in answer:
            try_list = [ a.strip() for a in answer.split(',') ]
            for i, j in zip(try_list, ans_list):
                if i != j:
                    return False
            return True
        
        # print( f'{answer} in {ans_list}' )
        return answer in ans_list



    def add_poke_to_collection( self, session ):

        # Stringification
        correct_string = []
        verdict = []

        for i in range(3):
            acceptable = session.get('three')[i]['answers']
            # ans_list = acceptable.split(',')
            # ans_str = ', '.join( ans_list )
            correct_string.append( acceptable )

            ans = session['answers'][i]
            OK = self.is_correct( ans, acceptable )
            verdict.append( "Poprawna" if OK else "Niepoprawna" )

        good = all([ v=="Poprawna" for v in verdict ])

        # Needed in HTML
        session['correct_string'] = correct_string
        session['verdict'] = verdict
        session['good'] = good
        session['datetime'] = str(datetime.datetime.now()).split(".")[0]
        session['qIDs'] = [ q['ID'] for q in session['three'] ]


        # if not good:
            # return

        # Preparation to writing
        username = session['username']
        users_dict = self.get_users_dict()

        target_row = list(users_dict.keys()).index( username ) + 1
        target_column = users_dict[ username ]['pokelen'] + 4
        

        # New record
        pokestring = '&'.join(
            [ str(session[field]) for field in self.record_model ]
        )
        self.users_sheet.update_cell( target_row, target_column, pokestring )

        # Update datetime
        self.users_sheet.update_cell( target_row, 3, session['datetime'] )
        

    # DB lookup and fetching a list for user
    def get_userpoke_list( self, username, only_catched=False ):

        users = self.users_sheet.get_all_values()
        userpoke = []
        for row in users:
            if row[0] == username:
                if len(row)>3:
                    for pokestring in row[3:]:
                        if pokestring != '':
                            splitted = pokestring.split('&')
                            pokerecord = {}
                            for i, field in enumerate( self.record_model ):
                                try:
                                    pokerecord[ field ] = ast.literal_eval( splitted[i] )
                                except:
                                    pokerecord[ field ] = splitted[i]

                            if only_catched:
                                if not pokerecord['good']:
                                    continue

                            userpoke.append( pokerecord )
                        
        return userpoke



    def too_fast( self, username ):
        users = self.users_sheet.get_all_values()
        for row in users:
            if row[0] == username:
                dt = row[2]
                if len(dt) == 0:
                    return False
                else:
                    last_time = datetime.datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
                    now = str(datetime.datetime.now()).split(".")[0]
                    now = datetime.datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
                    diff = now - last_time
                    
                    print( diff < datetime.timedelta(minutes=self.COOLDOWN_MIN) )
                
                    return diff < datetime.timedelta(minutes=self.COOLDOWN_MIN)





# if __name__ == "__main__":
    
