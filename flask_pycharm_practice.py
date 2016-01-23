import sys
import os
from os import listdir
import re

sys.path.insert(1, os.path.join(os.path.abspath('.'), 'lib'))
dir_path = os.path.dirname(os.path.realpath(__file__))
import method_for_use
import pdf_miner
import file_read_output_docx
import sqlalchemy
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask import session
from flask import g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text
import cPickle as pickle


app = Flask(__name__)
db = SQLAlchemy(app)
# collins_engine = sqlalchemy.create_engine('sqlite:///db/vocabulary.sqlite3')
# coca_engine = sqlalchemy.create_engine('sqlite:///db/AmericanYouDao.sqlite3')

# class Vocabulary(db.Model):
#     rowid = db.Column(db.Integer, primary_key=True)
#     voc = db.Column(db.Text)
#     star = db.Column(db.Integer)
#     not_remember = db.Column(db.Integer)
#     Definition = db.Column(db.Text)
#     phonetic = db.Column(db.Text)
# user_name = 'root'
# password = ''
# database_host_address = 'localhost:3306'
# database_name = 'test'
user_name = 'ch2leo'
password = '21070527'
database_host_address = 'ch2leo.mysql.pythonanywhere-services.com'
database_name = 'ch2leo$test'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqldb://' + user_name + ':' + password + '@' + \
#                                         database_host_address + '/' + database_name
# db.create_all()
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/vocabulary.sqlite3'
app.config['SQLALCHEMY_BINDS'] = {
    'Collins': 'sqlite:///db/vocabulary.sqlite3',
    'Coca': 'sqlite:///db/AmericanYouDao.sqlite3'
}
# CollinsSession = scoped_session(sessionmaker(bind=collins_engine))

UPLOAD_FOLDER = dir_path + '\\upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        for file in request.files.getlist('my_file'):
            if file and method_for_use.allowed_file(file.filename):
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
        for i in request.form:
            os.remove(dir_path + '\\upload\\' + i)
    books_list = listdir(dir_path + '\\upload')
    return render_template('index.html', books_list=books_list)


@app.route('/voc_database/<data>', methods=['POST', 'GET'])
def voc_database(data):
    rem = '1' if data[-1] == 'r' else '0'
    if request.method == 'POST':
        update_wanted_dic(str(int(not int(rem))))
    if re.match('Collins', data):
        table = 'vocabulary'
        datas = db.get_engine(app, bind='Collins').execute(text('SELECT voc,star,Definition,phonetic FROM '
                                                                + table + ' WHERE remember = ' + rem))
    elif re.match('Coca', data):
        table = 'AmericanYouDao'
        datas = db.get_engine(app, bind='Coca').execute(text(
                'SELECT voc,pos,rank,Definition,phonetic FROM ' + table + ' WHERE remember = ' + rem + ' AND rank < 20000 ORDER BY rank'))
    return render_template('data.html', DBdata=data, datas=enumerate(list(datas)))

def update_wanted_dic(remember="1"):
    for i in request.form:
        voc = i
        pos = request.form[i]
        # print voc, pos
        db.get_engine(app, bind='Collins').execute(text('UPDATE vocabulary SET remember = "' +
                                                                remember + '" WHERE lower(voc) = "' +
                                                                voc.lower() + '"'))
        if pos != 'on':
            db.get_engine(app, bind='Coca').execute(
                    text('UPDATE AmericanYouDao SET remember = "' +
                         remember + '" WHERE lower(voc) = "' +
                         voc.lower() + '" AND pos = "' +
                         pos[0] + '"'))
    if remember == '1':
        for book in listdir(dir_path + '\\upload'):
            for value in ['_Collins']:
                with open(book + value + '.pk', 'rb') as input:
                    all_ex = pickle.load(input)
                    wanted_voc = pickle.load(input)

                    for i in request.form:
                        voc = i
                        pos = request.form[i]
                        for v, p in all_ex.keys():
                            if voc.lower() == v.lower() and (pos[0] == p[0] or pos == 'on'):
                                all_ex.pop((v, p))
                                wanted_voc.pop((v, p))
                with open(book + value + '.pk', 'wb') as output:
                    pickle.dump(all_ex, output, -1)
                    pickle.dump(wanted_voc, output, -1)
    else:
        voc_pos_list = list()
        for i in request.form:
            voc_pos_list.append((i, None if request.form[i] == 'on' else request.form[i]))
        for book in listdir(dir_path + '\\upload'):
            file_name = dir_path + '\\upload\\' + book
            content = pdf_miner.convert(file_name)
            for value in ['_Collins']:
                with open(book + value + '.pk', 'rb') as input:
                    all_ex = pickle.load(input)
                    wanted_voc = pickle.load(input)

                    specific_wanted_ex = file_read_output_docx.content_handle(content, db, app, value,
                                                                              voc_pos_list)

                    all_ex.update(specific_wanted_ex[0])
                    wanted_voc.update(specific_wanted_ex[1])

                with open(book + value + '.pk', 'wb') as output:
                    pickle.dump(all_ex, output, -1)
                    pickle.dump(wanted_voc, output, -1)


@app.route('/book_voc/<book>?value=<value>', methods=['POST', 'GET'])
def book_voc(book, value):
    if request.method == 'POST':
        update_wanted_dic()

    try:
        with open(book + value + '.pk', 'rb') as input:
            all_ex = pickle.load(input)
            wanted_voc = pickle.load(input)
    except IOError:
        file_name = dir_path + '\\upload\\' + book
        content = pdf_miner.convert(file_name)
        all_ex, wanted_voc = file_read_output_docx.content_handle(content, db, app, value)
        with open(book + value + '.pk', 'wb') as output:
            pickle.dump(all_ex, output, -1)
            pickle.dump(wanted_voc, output, -1)

    vocs = list()
    for ind, (voc_pros, word_ex_list) in enumerate(all_ex.items()):
        vocs.append(method_for_use.output_html(ind + 1, voc_pros[1], voc_pros[0], ''.join(list(wanted_voc[
                                                                                                   voc_pros][1][0])), word_ex_list))

    return render_template('book_voc.html', vocs=vocs, book=book, value=value)

# @app.before_first_request
# def init():
#     if not os.environ.get('WERKEUG_RUN_MAIN') == 'true':
#         pass

if __name__ == '__main__':
    app.debug = True
    app.run()
