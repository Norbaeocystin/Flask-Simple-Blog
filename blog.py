'''
date: Oktober 2018
'''
# non Flask imports
from collections import OrderedDict
import datetime
import json
import pymongo
from pymongo import ASCENDING, DESCENDING
import re
import string
import time

# Flask imports
from flask import Flask, render_template, request, Response
from flask_httpauth import HTTPBasicAuth
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired
from flask_ckeditor import CKEditor, CKEditorField
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


#connection to database
client = pymongo.MongoClient('mongodb://localhost/my_database', connect = False)
db = client.my_database #you can change name to whatever name you want 
blog = db.blog

# define folder for templates delete when deploying on pythonanywhere 
app = Flask(__name__, template_folder='template')
auth = HTTPBasicAuth()
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_HEIGHT'] = 800
app.secret_key = 'secret string'
ckeditor = CKEditor(app)

# users login and password
users = {
    "admin": generate_password_hash("admin")
}

#search in collection and return link and name
def get_search(search):
    '''
    querying collection in the body of text returning tuple with link and name,
    in the case of not foud any result returns None
    '''
    results = list(blog.find({'body':{"$regex": re.compile(search, re.IGNORECASE)}}))
    if results:
        return [['/blog/'+item['title'].replace(' ','-'), item['title']] for item in results]
    else:
        return None


#convert time.asctime to weeks ago, days ago, minutes ago and so on ...
def get_delta(time_to_strip = 'Sat Oct 6 23:07:59 2018'):
    '''
    >>>get_delta('Sat Oct 6 23:07:59 2018')
    >>>'32 minutes ago'
    '''
    d = datetime.datetime.strptime(time_to_strip, "%a %b %d %H:%M:%S %Y")
    d2 = datetime.datetime.strptime(time.asctime(), "%a %b %d %H:%M:%S %Y")
    delta = d2 -d
    weeks = delta.days//2
    hours = delta.seconds//3600
    minutes = delta.seconds//60
    if weeks >1:
        return '{} weeks ago'.format(weeks)
    elif weeks == 1:
        return '{} week ago'.format(weeks)
    elif delta.days >1 and weeks == 0:
        return '{} days ago'.format(weeks)
    elif delta.days == 1 and weeks == 0:
        return '{} day ago'.format(weeks)
    elif delta.days == 0 and hours >1:
        return '{} hours ago'.format(hours)
    elif delta.days == 0 and hours == 1:
        return '{} hour ago'.format(hours) 
    elif hours == 0 and minutes >1:
        return '{} minutes ago'.format(minutes)
    elif hours == 0 and minutes == 1:
        return '{} minute ago'.format(minutes) 
    elif minutes == 0 and delta.seconds != 1:
        return '{} seconds ago'.format(delta.seconds)
    elif hours == 0 and delta.seconds == 1:
        return '{} seconds ago'.format(delta.seconds)
    
def get_tags():
    '''
    return list of unique tags in alphabetical order with first letter as capital
    '''
    data = []
    [data.extend(item.split(', ')) for item in list(blog.distinct('tags'))]
    return sorted({string.capwords(item) for item in data})

def get_titles_from_tag(tag):
    '''
    search in tags for a tag returns list of titles for the tag
    '''
    return [item.get('title') for item in list(blog.find({'publish':True,'tags':{"$regex": re.compile(tag, re.IGNORECASE)}},{"title":1,'_id':0}))]
    
def get_tags_and_titles():
    '''
    in alphabetical order returns sorted nested list of tags with titles
    '''
    tags = get_tags()
    results = [[item, get_titles_from_tag(item)] for item in tags]
    return [item for item in results if item[1] ]

def get_months_and_year():
    posts = list(blog.find({'publish':True},{'creationTime':1, 
            'title':1}).sort([("creationTime", pymongo.DESCENDING)]))
    result = OrderedDict()
    for item in posts:
        month_year = time.strftime('%B %Y',time.gmtime(item.get('creationTime')))
        if result.get(month_year):
            result.get(month_year).append(item.get('title'))
        else:
            result[month_year] = [item.get('title')]
    return result
                            
                            
class PostForm(FlaskForm):
    '''
    Form for writing blogs
    '''
    author = StringField('author', validators=[DataRequired()])
    title = StringField('title', validators=[DataRequired()])
    tags =  StringField('tags', validators=[DataRequired()])
    body = CKEditorField('body', validators=[DataRequired()])
    publish = BooleanField('Publish', default="checked")
    submit = SubmitField('Submit')

class SearchForm(FlaskForm):
    '''
    Form for searching in database
    '''
    search = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Submit')

@auth.verify_password
def verify_password(username, password):
    
    '''
    check hash of password for user
    '''
    
    if username in users:
        return check_password_hash(users.get(username), password)
    return False




@app.route('/', methods=['GET', 'POST'])
def get_home():
    '''
    main webpage
    '''
    form = SearchForm() #Search form below code for returning search from database
    posts = list(blog.find({'publish':True}).sort([("creationTime", pymongo.DESCENDING)]))
    posts = [['/blog/'+item['title'].replace(' ','-'), item['title']] for item in posts ]
    if request.method == 'POST':
        search =  request.form['search']
        results = get_search(search)
        if results:
            return render_template ("blog.html", posts = posts, form = form, results = results )
        else:
            return render_template ("blog.html", posts = posts, form = form, result = '' )
    return render_template ("blog.html", posts = posts, form = form )

@app.route('/about', methods=['GET', 'POST'])
def get_about():
    '''
    about webpage 
    '''
    about = '''Whatever you want to write :)\n
    '''
    return render_template ("about.html", about = about)


    
@app.route('/categories', methods=['GET', 'POST'])
def get_achive():
    '''
    archive website 
    '''
    tags_titles = get_tags_and_titles()
    return render_template('categories.html', tags_titles = tags_titles)
    

@app.route('/blog/<string:name>')
def get_posts(name):
    
    '''
    generates urls for blog posts
    '''
    
    post = list(blog.find({'title':name.replace('-',' '), 'publish':True}))[0]
    if post:
        author = post['author']
        title = post['title']
        tags = post['tags']
        body = post['body']
        creationTime = get_delta(time.asctime(time.gmtime(post['creationTime'])))
        return render_template('post.html', title=title, body=body, tags = tags, 
                               creationTime = creationTime, author = author)
    
@app.route('/admin')
@auth.login_required
def get_admin_panel():
    '''
    admin panel
    '''
    posts = list(blog.find())
    posts = [['/admin/edit/'+item['title'].replace(' ','-'), item['title']] for item in posts ]
    return render_template ("admin.html", posts = posts )

@app.route('/admin/write', methods=['GET', 'POST'])
@auth.login_required
def get_new_post():
    
    '''
    for writing new post with required login 
    and ckeditor also after submiting storing data in mongo and redirecting 
    to see it
    '''
    
    form = PostForm()
    if form.validate_on_submit():
        author = form.author.data
        creationTime = int(time.time())
        title = form.title.data
        tags = form.tags.data
        body = form.body.data
        publish = True if request.form.get('publish') else False
        blog.insert( 
            { 
                'title': title , 'tags' : tags , 'body' : body, 'creationTime' : creationTime, 'author': author, 
                'publish': publish
            } 
        )
        creationTime = get_delta(time.asctime(time.gmtime(creationTime)))
        return render_template('post-edit.html', title=title, body=body, tags = tags, creationTime = creationTime, 
                               author = author, publish = publish)
    return render_template('write.html', form=form, name_ = 'Write a post')

@app.route('/admin/edit')
@auth.login_required
def get_edits():
    
    '''
    shows list of posts for editing
    '''
    
    posts = list(blog.find())
    posts = [['/admin/edit/'+item['title'].replace(' ','-'), item['title']] for item in posts ]
    return render_template ("edit.html", posts = posts )

@app.route('/admin/edit/<string:name>', methods=['GET', 'POST'])
@auth.login_required
def get_post_edit(name):
    
    '''
    for editing post
    '''
    
    post = list(blog.find({'title':name.replace('-',' ')}))[0]
    data = post
    form = PostForm()
    #code below to file fields with text
    form.title.data = data['title']
    form.tags.data = data['tags']
    form.body.data = data['body']
    form.author.data = data['author']
    if request.method == 'POST' and form.validate():
        # after editing press sumbit will return these data from post request
        author = request.form.get('author')
        title = request.form.get('title')
        tags = request.form.get('tags')
        body = request.form.get('body')
        publish = True if request.form.get('publish') else False
        # will add time with last change
        changeTime = int(time.time())
        # update data in database
        blog.update( 
            { 
                '_id' : data['_id'] 
            },
            
            { 
                '$set': {'title': title , 'tags' : tags , 'body' : body, 'changeTime' : changeTime, 'publish':publish}
            } 
        )
        creationTime = get_delta(time.asctime(time.gmtime(data['creationTime'])))                        
        return render_template('post-edit.html', title = title, body = body, tags = tags, 
                               creationTime = creationTime, publish = publish, author = author)
    return render_template('write.html', form = form, name_ = 'Edit')

@app.route('/admin/logout')
def get_logout():
    
    '''
    this function is important to be able to
    logout 
    '''
    
    return "Logout", 401

@app.route('/sitemap.xml')
def get_sitemap():
    '''
    Function to generate sitemap
    blog posts are generated from mongodb collection,
    other needs to be written to sites list
    do not forget add this to robots.txt
    '''
    base = '' #change to your website home
    sites = [base]
    posts = list(blog.find({'publish':True}))
    if posts:
        sites.extend([base + '/blog/'+item['title'].replace(' ','-')for item in posts])
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for item in sites:
        sitemap += '<url><loc>{}</loc></url>\n'.format(item)
    sitemap += '</urlset>'
    return Response(sitemap, mimetype="text/xml")

@app.route('/robots.txt')
def get_robots():
    '''
    return robots.txt
    '''
    return Response('User-Agent: *\nDisallow:\n\nSitemap: http:<your website>/sitemap.xml', mimetype="text/plain")

@app.errorhandler(404)
def get_page_not_found(e):
    '''
    Webpage not found redirect, can be used for other errors with slightly modification
    '''
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug = True)