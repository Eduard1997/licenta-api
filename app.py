from flask import Flask, jsonify, request
from flask_cors import CORS
import scholarly

# instantiate the app
application = Flask(__name__)
application.config.from_object(__name__)

# enable CORS
CORS(application, resources={r'/*': {'origins': '*'}})


@application.route('/', methods=['GET'])
def hello():
    return jsonify('hello')


@application.route('/get-docs-by-author', methods=['POST'])
def get_docs_by_author():
    try:
        author_response = {}
        payload = request.json['author_name']
        search_query = scholarly.search_author(payload)
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
    except:
        return jsonify({'error': 'Author not found or error encountered'})
    else:
        return jsonify(author_response)


@application.route('/get-publications-for-author2', methods=['POST'])
def get_publications_for_author2():
    try:
        author_name = request.json['authorName']
        search_query = scholarly.search_author(author_name)
        author = next(search_query).fill()
        publication_response = {}
        publication_response['publications'] = {}
        for pub in author.publications:
            pub.fill()
            publication_response['publications'][pub.bib['title']] = pub.bib
            publication_response['publications'][pub.bib['title']]['url'] = pub.bib.get('url')
    except:
        return jsonify({'error': 'Author publications not found or error encountered'})
    else:
        return jsonify(publication_response)


@application.route('/get-test', methods=['GET'])
def get_test():
    return jsonify('test')


@application.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Origin,Content-Type,Authorization,X-Requested-With,X-Auth-Token')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'false')
    return response


if __name__ == '__main__':
    # application.debug = True
    application.run(host='0.0.0.0')
