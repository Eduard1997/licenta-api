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
from bs4 import BeautifulSoup, SoupStrainer

# instantiate the app
application = Flask(__name__)
application.config.from_object(__name__)

# mysql connection
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
        cursor.execute(search_existing_author_query, '%' + search_existing_author_values + '%')
        values = cursor.fetchall()

        # query = xplore.xploreapi.XPLORE('khvns7n2jca9e6fetnmrepn9')
        # query.abstractText(author_name)
        # data = query.callAPI()
        # print(data)

        if len(values) == 0:
            scholar_url = 'https://scholar.google.com/scholar?hl=ro&as_sdt=0%2C5&q=' + request.json['author_name']

            scholar_page = BeautifulSoup(requests.get(scholar_url).content, 'html.parser')
            author_details = scholar_page.find("td", {"valign": "top"})
            author_details_link = 'https://scholar.google.com' + author_details.findChildren("a")[0]['href']

            author_details_page = BeautifulSoup(requests.get(author_details_link).content, 'html.parser')
            author_name = author_details_page.find("div", {"id": "gsc_prf_in"}).get_text()
            author_picture = 'https://scholar.google.com' + \
                             author_details_page.find("div", {"id": "gsc_prf_pua"}).findChildren("img")[0]["src"]
            author_affiliation = author_details_page.find("a", {"class": "gsc_prf_ila"}).get_text()
            author_cites_per_year = []
            author_cites_years = author_details_page.find_all("span", {"class": "gsc_g_t"})
            author_cites_number_per_year = author_details_page.find_all("span", {"class": "gsc_g_al"})
            for i in range(0, len(author_cites_years)):
                author_cites_per_year.append(
                    {author_cites_years[i].get_text(): author_cites_number_per_year[i].get_text()})
            author_total_cites = author_details_page.find("td", {"class": "gsc_rsb_std"}).get_text()
            author_hindex = author_details_page.find_all("td", {"class": "gsc_rsb_std"})[2].get_text()
            author_h5index = author_details_page.find_all("td", {"class": "gsc_rsb_std"})[3].get_text()
            author_h10index = author_details_page.find_all("td", {"class": "gsc_rsb_std"})[4].get_text()
            author_h10index_i5 = author_details_page.find_all("td", {"class": "gsc_rsb_std"})[5].get_text()
            author_interests = author_details_page.find_all("a", {"class": "gsc_prf_inta"})
            author_interests_arr = []
            for interests in author_interests:
                author_interests_arr.append(interests.get_text())
            author_coauthors = author_details_page.find_all("span", {"class": "gsc_rsb_a_desc"})
            author_coauthors_arr = []
            for coauthors in author_coauthors:
                coauthor_name = coauthors.findChildren("a")[0].get_text()
                coauthor_affiliation = coauthors.findChildren("span", {"class": "gsc_rsb_a_ext"})[0].get_text()
                author_coauthors_arr.append({coauthor_name: coauthor_affiliation})

            author_response['author_name'] = author_name
            author_response['affiliation'] = author_affiliation
            author_response['cited_by'] = author_total_cites
            author_response['cites_per_year'] = author_cites_per_year
            author_response['url_picture'] = author_picture
            author_response['h_index'] = author_hindex
            author_response['h5_index'] = author_h5index
            author_response['i10_index'] = author_h10index
            author_response['i10_index5y'] = author_h10index_i5
            author_response['interests'] = author_interests_arr
            author_response['coauthors'] = author_coauthors_arr

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
        cursor.execute(search_existing_author_query, '%' + search_existing_author_values + '%')
        values = cursor.fetchall()

        if len(values) == 0:
            search_query = scholarly.search_author(author_name)
            author = next(search_query).fill()
            for pub in author.publications:
                pub.fill()
                publication_response['publications'][pub.bib['title'].lower().title().replace(".", "")] = pub.bib
                publication_response['publications'][pub.bib['title'].lower().title().replace(".", "")][
                    'url'] = pub.bib.get('url')

            scopus_author_data = requests.get(
                'http://api.elsevier.com/content/search/scopus?query=' + author_name + '&apiKey=acf90e6867d5a1b99ca5ba2f91935664').content
            decode_scopus_author_data = json.loads(scopus_author_data)
            for item in decode_scopus_author_data['search-results']['entry']:
                if item['dc:title'].lower().title().replace(".", "") in publication_response['publications']:
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'scopus_link'] = item['link'][2]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'aggregation_type'] = item['prism:aggregationType']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'subtype_description'] = item['subtypeDescription']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'publication_name'] = item['prism:publicationName']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'cited_by'] = item['citedby-count']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'cited_by_link'] = item['link'][3]['@href']
                else:
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")] = {}
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['title'] = \
                        item['dc:title'].lower().title().replace(".", "")
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['url'] = \
                        item['link'][2]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'aggregation_type'] = item['prism:aggregationType']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'subtype_description'] = item['subtypeDescription']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'publication_name'] = item['prism:publicationName']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'cited_by'] = item['citedby-count']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'cited_by_link'] = item['link'][3]['@href']
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                        'eprint'] = '-'
                    publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['year'] = \
                        item['prism:coverDate'].split('-')[0]

            authors_dblp = requests.get('http://dblp.org/search/publ/api?q=' + author_name + '&format=json').content
            authors_dblp_decoded = json.loads(authors_dblp)
            for item in authors_dblp_decoded['result']['hits']['hit']:
                if item['info']['title'].lower().title().replace(".", "") in publication_response['publications']:
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                        'dblp_link'] = item['info']['url']
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                        'dblp_type'] = item['info']['type']
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                        'dblp_venue'] = item['info']['venue']
                else:
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")] = {}
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")]['title'] = \
                        item['info']['title'].lower().title().replace(".", "")
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")]['url'] = \
                        item['info']['url']
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                        'dblp_type'] = item['info']['type']
                    if 'venue' in item['info']:
                        publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                            'dblp_venue'] = item['info']['venue']
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")]['year'] = \
                        item['info']['year']

            sql = "UPDATE authors SET author_publications_scholar = %s WHERE name LIKE %s"
            values = (json.dumps(publication_response), '%' + author_name + '%')
            cursor.execute(sql, values)
            conn.commit()

        else:
            result = []
            search_existing_author_query = 'SELECT author_publications_scholar FROM authors WHERE name LIKE %s'
            search_existing_author_values = author_name
            cursor.execute(search_existing_author_query, '%' + search_existing_author_values + '%')
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
        return jsonify({'error': str(e)})
    else:
        return jsonify(publication_response)


@application.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Credentials', 'false')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Headers',
                         'Access-Control-Allow-Origin, Access-Control-Allow-Headers, Origin,Accept, X-Requested-With, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers')
    return response


if __name__ == '__main__':
    application.debug = True
    application.run()
