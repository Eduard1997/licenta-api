from flask import Flask, jsonify, request
from flask_cors import CORS
from flaskext.mysql import MySQL
from pybliometrics.scopus import AuthorSearch
from pybliometrics.scopus import ScopusSearch
import requests
import simplejson
import scholarly
import json

# instantiate the app
application = Flask(__name__)
application.config.from_object(__name__)


#mysql connection
mysql = MySQL()
application.config['MYSQL_DATABASE_USER'] = 'root'
application.config['MYSQL_DATABASE_PASSWORD'] = ''
application.config['MYSQL_DATABASE_DB'] = 'flask_db'
application.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(application)

# enable CORS
cors = CORS(application)


@application.route('/', methods=['GET'])
def hello():
    conn = mysql.connect()
    cursor = conn.cursor()

    cursor.execute("SELECT * from authors")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    result = []
    for row in rows:
        row = dict(zip(columns, row))
        result.append(row)

    return 'da'


@application.route('/get-docs-by-author', methods=['POST'])
def get_docs_by_author():
    try:
        conn = mysql.connect()
        cursor = conn.cursor()

        author_response = {}
        author_name = request.json['author_name']

        search_existing_author_query = 'SELECT * from authors where name LIKE %s'
        search_existing_author_values = author_name
        cursor.execute(search_existing_author_query, '%'+search_existing_author_values+'%')
        values = cursor.fetchall()

        if len(values) == 0:
            search_query = scholarly.search_author(author_name)
            author = next(search_query).fill()

            author_response['author_name'] = author.name
            author_response['affiliation'] = author.affiliation
            author_response['cited_by'] = author.citedby
            author_response['cites_per_year'] = author.cites_per_year
            author_response['url_picture'] = author.url_picture
            author_response['email'] = author.email
            author_response['h_index'] = author.hindex
            author_response['h5_index'] = author.hindex5y
            author_response['i10_index'] = author.i10index
            author_response['i10_index5y'] = author.i10index5y
            author_response['interests'] = author.interests
            author_response['coauthors'] = {}
            for coauthor in author.coauthors:
                author_response['coauthors'][coauthor.name] = coauthor.affiliation

            sql = "INSERT into authors(name, author_details_scholar) VALUES(%s, %s)"
            values = (author_response['author_name'], json.dumps(author_response))
            cursor.execute(sql, values)
            conn.commit()
        else:
            result = []
            columns = [desc[0] for desc in cursor.description]
            for row in values:
                row = dict(zip(columns, row))
                result.append(row)
            for details in result:
                author_response['author_name'] = details['name']
                extra_details = json.loads(details['author_details_scholar'])
                author_response['affiliation'] = extra_details['affiliation']
                author_response['cited_by'] = extra_details['cited_by']
                author_response['cites_per_year'] = extra_details['cites_per_year']
                author_response['url_picture'] = extra_details['url_picture']
                author_response['email'] = extra_details['email']
                author_response['h_index'] = extra_details['h_index']
                author_response['h5_index'] = extra_details['h5_index']
                author_response['i10_index'] = extra_details['i10_index']
                author_response['i10_index5y'] = extra_details['i10_index5y']
                author_response['interests'] = extra_details['interests']
                author_response['coauthors'] = extra_details['coauthors']

    except Exception as e:
        return jsonify({'error': str(e)})
    else:
        return jsonify(author_response)


@application.route('/get-publications-for-author', methods=['POST'])
def get_publications_for_author():
    #try:
        conn = mysql.connect()
        cursor = conn.cursor()

        publication_response = {}
        publication_response['publications'] = {}
        author_name = request.json['authorName']


        search_existing_author_query = 'SELECT * from authors WHERE name LIKE %s AND author_publications_scholar IS NOT NULL'
        search_existing_author_values = author_name
        cursor.execute(search_existing_author_query, '%'+search_existing_author_values+'%')
        values = cursor.fetchall()

        if len(values) == 0:
            search_query = scholarly.search_author(author_name)
            author = next(search_query).fill()

            pub = author.publications[0].fill()
            for pub in author.publications:
                print([citation.bib['title'] for citation in pub.get_citedby()])
                publication_response['publications'][pub.bib['title']] = pub.bib
                publication_response['publications'][pub.bib['title']]['url'] = pub.bib.get('url')
            sql = "UPDATE authors SET author_publications_scholar = %s WHERE name LIKE %s"
            values = (json.dumps(publication_response), '%'+author_name+'%')
            cursor.execute(sql, values)
            conn.commit()
        else:
            result = []
            search_existing_author_query = 'SELECT author_publications_scholar FROM authors WHERE name LIKE %s'
            search_existing_author_values = author_name
            cursor.execute(search_existing_author_query, '%'+search_existing_author_values+'%')
            values = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            for row in values:
                row = dict(zip(columns, row))
                result.append(row)
            publications = json.loads(result[0]['author_publications_scholar'])

            for key, value in publications['publications'].items():
                publication_response['publications'][key] = value
                publication_response['publications'][key]['url'] = value['url']
                publication_response['publications'][key]['cited_by'] = value['cited_by']
    #except Exception as e:
        #return jsonify({'error': str(e.with_traceback())})
    #else:
        return jsonify(publication_response)





@application.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Credentials', 'false')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Access-Control-Allow-Origin, Access-Control-Allow-Headers, Origin,Accept, X-Requested-With, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers')
    return response


if __name__ == '__main__':
    application.debug = True
    application.run()
