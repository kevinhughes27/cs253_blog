#!/usr/bin/env python

import os
import re
import webapp2
import jinja2
import json
import hmac
import time

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

from google.appengine.ext import db
from google.appengine.api import memcache

from user import User
from blog import BlogEntry

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json(self, d):
        self.response.headers['Content-Type'] = 'application/json'
        self.write(json.dumps(d))

    SECRET = 'imsosecret'
    def hash_str(self,s):
        return hmac.new(self.SECRET,s).hexdigest()

    def make_secure_val(self,val):
        return '%s|%s' % (val, self.hash_str(val))

    def check_secure_val(self,secure_val):
        val = secure_val.split('|')[0]
        if secure_val == self.make_secure_val(val):
            return val

    def set_secure_cookie(self, name, val):
        cookie_val = self.make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))
            
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and self.check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))
    
    def logout(self):
        self.response.headers.add_header('Set-Cookie','user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))
        
        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'    



class MainPage(Handler):
    def get(self):
        self.write('Hello, Udacity!')



class SignupHandler(Handler):
  
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    PWD_RE = re.compile("^.{3,20}$")
    EMAIL_RE = re.compile("^[\S]+@[\S]+\.[\S]+$")
    
    def valid_username(self, username):
        return self.USER_RE.match(username)

    def valid_password(self, password):
        return self.PWD_RE.match(password)

    def valid_email(self, email):
        return self.EMAIL_RE.match(email)
    
    def get(self):
        self.render('signup.html')

    def post(self):
        error = False
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email")
	    
        params = dict(username=username, email=email)
        
        if not self.valid_username(username):
            error = True
            params['username_error'] = "That's not a valid username."
        if User.by_username(username):
            error = True
            params['username_error'] = "username in use."
        if not self.valid_password(password):
            error = True
            params['password_error'] = "That's not a valid password."
        if password != verify:
            error = True
            params['verify_error'] = "Your passwords didn't match."
        if email != "":
            if not self.valid_email(email):
                error = True
                params['email_error'] = "That's not a valid email."

        if not error:
            u = User.register(username=username, password=password, email=email)
            u.put()
            self.login(u)
            self.redirect('/blog/welcome')
        else:
            self.render('signup.html', **params)



class LoginHandler(Handler):
    def get(self):
        self.render('login.html')

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
         
        u,e = User.login(username,password)        

        if u:
            self.login(u)
            self.redirect('/blog/welcome')
        else:    
            self.render('login.html', **e)



class LogoutHandler(Handler):
    def get(self):
        self.logout()
        self.redirect('/blog/signup')



class WelcomeHandler(Handler):
     def get(self):
        if self.user:
            self.render('welcome.html', username=self.user.username)    
        else:
            self.redirect('/blog/signup')    



def get_recent_posts(update = False):
        key = 'recent'
        if memcache.get(key) is None or update:
            posts = db.GqlQuery("SELECT * from BlogEntry ORDER BY post_date desc limit 10")
            memcache.set(key, (posts,time.time()) )
            age = 0
        else:
            posts, qtime = memcache.get(key)
            age = int(time.time() - qtime)
        return posts, age



class BlogHandler(Handler): 
    def get(self):
        posts, age = get_recent_posts()     
        if self.format == 'json':
            self.render_json( [post.as_dict() for post in posts] )
        else:
            self.render('blog.html', posts=posts, queryage=age)

    

class NewPostHandler(Handler):
    def get(self):
        self.render('newpost.html')
        
    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")
        
        if subject=="" or content=="":
            self.render('newpost.html', error="Must have Subject and Content")    
        
        new_entry = BlogEntry(subject=subject, content=content)
        new_entry.put()
        get_recent_posts(update = True)
        self.redirect('/blog/%d' % new_entry.key().id())



class PostHandler(BlogHandler):
    def get_BlogEntry(self, blog_id):
        key = str(blog_id)
        if memcache.get(key) is None:
            post = BlogEntry.get_by_id(int(blog_id))
            memcache.set(key, (post,time.time()) )
            age = 0
        else:
            post, qtime = memcache.get(key)
            age = int(time.time() - qtime)
        return post, age
    
    def get(self, blog_id):
        post, age = self.get_BlogEntry(blog_id)
        
        if not post:
            self.error(404)
            return
        
        if self.format == 'json':
            self.render_json(post.as_dict())
        else:
            self.render('blog.html', posts=[post], queryage=age)

        

class FlushHandler(BlogHandler):
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/blog/signup', SignupHandler),
                               ('/blog/login', LoginHandler),
                               ('/blog/logout', LogoutHandler),
                               ('/blog/welcome', WelcomeHandler),
                               ('/blog/?(?:.json)?', BlogHandler),
                               ('/blog/newpost', NewPostHandler),
                               ('/blog/([0-9]+)(?:.json)?', PostHandler),
                               ('/blog/flush', FlushHandler)],
                               debug=True)



