import random
import string
import hashlib

from google.appengine.ext import db

def make_salt():
    return ''.join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def valid_pw(name, pw, h):
    salt = h.split(',')[1]
    return make_pw_hash(name,pw,salt) == h

class User(db.Model):
    username = db.StringProperty(required=True)
    password_hash = db.StringProperty(required=True)
    email = db.StringProperty()
    
    @classmethod
    def by_id(cls,uid):
        return User.get_by_id(uid)
        
    @classmethod
    def by_username(cls,username):
        u = User.all().filter('username =', username).get()
        return u
    
    @classmethod
    def register(cls,username,password,email):
        password_hash = make_pw_hash(username, password)
        u = User(username=username, password_hash=password_hash, email=email)
        return u    
    
    @classmethod
    def login(cls,username,pw):
        u = cls.by_username(username)
        e = dict(username=username)

        if u:
            if valid_pw(username,pw, u.password_hash):
                return u, None
            else:
                e['password_error'] = "Incorrect Password."
                return None, e
        else:
            e['username_error'] = "Invalid Username"
            return None, e 
            
            
            
