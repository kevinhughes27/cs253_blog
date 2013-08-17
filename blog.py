import os
import jinja2

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

from google.appengine.ext import db

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class BlogEntry(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    post_date = db.DateTimeProperty(auto_now_add=True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)
        
    def as_dict(self):
        d = {}
        d["content"] = self.content
        d["created"] = self.post_date.strftime("%Y/%m/%d")
        d["subject"] = self.subject
        return d
