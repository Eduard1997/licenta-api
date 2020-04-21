from flask import Flask, jsonify, request
from flask_cors import CORS
from flaskext.mysql import MySQL
from pybliometrics.scopus import AuthorSearch
from pybliometrics.scopus import ScopusSearch
import requests
import simplejson
import scholarly
import json
import xplore
from dblp_pub import dblp

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

        # query = xplore.xploreapi.XPLORE('khvns7n2jca9e6fetnmrepn9')
        # query.abstractText(author_name)
        # data = query.callAPI()
        # print(data)

        authors = dblp.search(['pistol ionut'])
        print(authors[3].publications)
        # print(michael)




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
    try:
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
            for pub in author.publications:
                pub.fill()
                publication_response['publications'][pub.bib['title'].lower().title().replace(".", "")] = pub.bib
                publication_response['publications'][pub.bib['title'].lower().title().replace(".", "")]['url'] = pub.bib.get('url')

            scopus_author_data = requests.get(
                'http://api.elsevier.com/content/search/scopus?query=' + author_name + '&apiKey=acf90e6867d5a1b99ca5ba2f91935664').content
            decode_scopus_author_data = json.loads(scopus_author_data)
            for item in decode_scopus_author_data['search-results']['entry']:
                if item['dc:title'].lower().title().replace(".", "") in publication_response['publications']:
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['scopus_link'] = item['link'][2]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['aggregation_type'] = item['prism:aggregationType']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['subtype_description'] = item['subtypeDescription']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['publication_name'] = item['prism:publicationName']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['cited_by'] = item['citedby-count']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['cited_by_link'] = item['link'][3]['@href']
                else:
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")] = {}
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['title'] = item['dc:title'].lower().title().replace(".", "")
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['url'] = item['link'][2]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['aggregation_type'] = item['prism:aggregationType']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['subtype_description'] = item['subtypeDescription']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['publication_name'] = item['prism:publicationName']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['cited_by'] = item['citedby-count']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['cited_by_link'] = item['link'][3]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['eprint'] = '-'
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['year'] = item['prism:coverDate'].split('-')[0]

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
    except Exception as e:
        return jsonify({'error': str(e.with_traceback())})
    else:
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
