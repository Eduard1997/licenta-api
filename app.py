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
from unidecode import unidecode
import re
import urllib3
import certifi

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


def replace_romanian_letters(word):
    if u"ă" in word:
        word = word.replace(u"ă", unidecode(u"a"))
    if u"Ă" in word:
        word = word.replace(u"Ă", unidecode(u"A"))
    if u"â" in word:
        word = word.replace(u"â", unidecode(u"a"))
    if u"Â" in word:
        word = word.replace(u"Â", unidecode(u"A"))
    if u"î" in word:
        word = word.replace(u"î", unidecode(u"i"))
    if u"Î" in word:
        word = word.replace(u"Î", unidecode(u"I"))
    if u"ş" in word:
        word = word.replace(u"ş", unidecode(u"s"))
    if u"Ş" in word:
        word = word.replace(u"Ş", unidecode(u"S"))
    if u"ţ" in word:
        word = word.replace(u"ţ", unidecode(u"t"))
    if u"Ţ" in word:
        word = word.replace(u"Ţ", unidecode(u"T"))
    return word


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
    # try:

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
        scholar_url = 'https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q=' + request.json['author_name']
        scholar_page = BeautifulSoup(requests.get(scholar_url).content, 'html.parser')
        author_details = scholar_page.find("td", {"valign": "top"})
        # author_details = None
        if author_details is not None:
            author_details_link = 'https://scholar.google.com' + author_details.findChildren("a")[0]['href']
            author_details_page = BeautifulSoup(requests.get(author_details_link).content, 'html.parser')
            author_name = author_details_page.find("div", {"id": "gsc_prf_in"}).get_text()
            author_picture = author_details_page.find("img", {"id": "gsc_prf_pup-img"})["src"]
            if author_picture[0] == '/':
                author_picture_url = 'https://scholar.google.com' + author_picture
            else:
                author_picture_url = author_picture
            author_affiliation_div = author_details_page.find("div", {"class": "gsc_prf_il"})
            author_affiliation_link = author_affiliation_div.findChildren("a")
            if len(author_affiliation_link):
                author_affiliation = author_affiliation_link[0].get_text()
            else:
                author_affiliation = author_affiliation_div.get_text()
            author_cites_per_year = []
            author_cites_years = author_details_page.find_all("span", {"class": "gsc_g_t"})
            author_cites_years_links = author_details_page.find_all("a", {"class": "gsc_g_a"})
            index_links_citations = 0
            links_index = 0
            step = False
            links_index = 0
            if len(author_cites_years) != len(author_cites_years_links):
                for i in range(0, len(author_cites_years)):
                    if index_links_citations == 0:
                        author_cites_per_year.append(
                            {author_cites_years[i].get_text(): author_cites_years_links[links_index].get_text()})
                        index_links_citations = int(author_cites_years_links[links_index]["style"].split('z-index:')[1])
                        links_index = links_index + 1
                    elif index_links_citations != 0 and int(
                            author_cites_years_links[links_index]["style"].split('z-index:')[
                                1]) + 1 != index_links_citations and step == False:
                        author_cites_per_year.append({author_cites_years[i].get_text(): 0})
                        step = True
                    elif step == True:
                        author_cites_per_year.append(
                            {author_cites_years[i].get_text(): author_cites_years_links[links_index].get_text()})
                        links_index = links_index + 1
            else:
                for i in range(0, len(author_cites_years)):
                    author_cites_per_year.append(
                        {author_cites_years[i].get_text(): author_cites_years_links[i].get_text()})

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

            if len(author_coauthors_arr) == 0:
                coauthors_reloaded = []
                author_first_name_request = request.json['author_name'].split(' ')[0]
                author_last_name_request = request.json['author_name'].split(' ')[1]
                author_first_name_initial_request = author_first_name_request[0]
                author_last_name_initial_request = author_last_name_request[0]

                author_first_name = author_name.split(' ')[0]
                author_last_name = author_name.split(' ')[1]
                author_first_name_initial = author_first_name[0]
                author_last_name_initial = author_last_name[0]
                coauthors_container = author_details_page.find_all("td", {"class": "gsc_a_t"})
                for couauthor in coauthors_container:
                    coauthors_arr = couauthor.find("div").get_text().split(',')
                    for item in coauthors_arr:
                        if author_first_name_initial_request + ' ' + author_first_name in item:
                            coauthors_arr.remove(item)
                        elif author_first_name_initial_request + ' ' + author_last_name in item:
                            coauthors_arr.remove(item)
                        elif author_last_name_initial_request + ' ' + author_first_name in item:
                            coauthors_arr.remove(item)
                        elif author_last_name_initial_request + ' ' + author_last_name in item:
                            coauthors_arr.remove(item)
                        elif author_first_name_initial + ' ' + author_first_name_request in item:
                            coauthors_arr.remove(item)
                        elif author_first_name_initial + ' ' + author_last_name_request in item:
                            coauthors_arr.remove(item)
                        elif author_last_name_initial + ' ' + author_first_name_request in item:
                            coauthors_arr.remove(item)
                        elif author_last_name_initial + ' ' + author_last_name_request in item:
                            coauthors_arr.remove(item)
                        elif "..." in item:
                            coauthors_arr.remove(item)
                        elif author_first_name == "Pistol" and "IC" in item:
                            coauthors_arr.remove(item)
                    coauthors_reloaded.append(coauthors_arr)
                final_coauthor_list = []
                for author in coauthors_reloaded:
                    for author2 in author:
                        final_coauthor_list.append(replace_romanian_letters(author2))
                final_coauthor_list = list(set(final_coauthor_list))
                for item in final_coauthor_list:
                    author_coauthors_arr.append({item: ""})

            author_response['author_name'] = author_name
            author_response['affiliation'] = author_affiliation
            author_response['cited_by'] = author_total_cites
            author_response['cites_per_year'] = author_cites_per_year
            author_response['url_picture'] = author_picture_url
            author_response['h_index'] = author_hindex
            author_response['h5_index'] = author_h5index
            author_response['i10_index'] = author_h10index
            author_response['i10_index5y'] = author_h10index_i5
            author_response['interests'] = author_interests_arr
            author_response['coauthors'] = author_coauthors_arr
        else:
            semantic_initial_url = 'https://www.semanticscholar.org/api/1/search'
            semantic_initial_payload = {
                "authors": [],
                "coAuthors": [],
                "externalContentTypes": [],
                "page": 1,
                "pageSize": 10,
                "performTitleMatch": True,
                "publicationTypes": [],
                "queryString": author_name,
                "requireViewablePdf": False,
                "sort": "relevance",
                "useRankerService": True,
                "venues": [],
                "yearFilter": None
            }
            headers = {"Content-Type": "application/json"}
            semantic_page_data = json.loads(
                requests.post(semantic_initial_url, data=json.dumps(semantic_initial_payload), headers=headers).content)
            semantic_author_extra_data = semantic_page_data["stats"]
            semantic_author_id = semantic_page_data["results"][0]["authors"][0][0]['ids'][0]
            semantic_author_slug = semantic_page_data["results"][0]["authors"][0][0]['slug']
            semantic_author_details_link = "https://www.semanticscholar.org/api/1/author/" + semantic_author_id + "?slug=" + semantic_author_slug + "&requireSlug=true&isClaimEnabled=true"
            semantic_author_data = json.loads(requests.get(semantic_author_details_link).content)
            author_response['author_name'] = semantic_author_data['author']['name']
            author_response['affiliation'] = semantic_author_data['author']['affiliations']
            author_response['cited_by'] = semantic_author_data['author']['statistics']['totalCitationCount']
            author_response['cites_per_year'] = [{value["startKey"]: value["count"]} for value in
                                                 semantic_author_data['author']['statistics']['citedByYearHistogram']]
            author_response['url_picture'] = ""
            author_response['h_index'] = semantic_author_data['author']['statistics']['hIndex']
            author_response['h5_index'] = ""
            author_response['i10_index'] = ""
            author_response['i10_index5y'] = ""
            author_response['interests'] = ""
            author_response['coauthors'] = semantic_author_extra_data["coAuthors"]
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

    # except Exception as e:
    # return jsonify({'error': str(e)})
    # else:
    return jsonify(author_response)


@application.route('/get-publications-for-author', methods=['POST'])
def get_publications_for_author():
    # try:
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
        scholar_url = 'https://scholar.google.com/scholar?hl=en&as_sdt=0%2C5&q=' + request.json['authorName']
        scholar_page = BeautifulSoup(requests.get(scholar_url).content, 'html.parser')
        #author_publications = scholar_page.find("div", {"id": "gs_res_ccl"})
        author_publications = None
        if author_publications is not None:
            author_publications = scholar_page.find("div", {"id": "gs_res_ccl"}).findChildren("div",{"class": "gs_scl"})
            for pub in author_publications:
                title = pub.findChildren("h3", {"class": "gs_rt"})[0].findChildren("a")[0].get_text()
                publication_response['publications'][title.lower().title().replace(".", "")] = {}
                publication_response['publications'][title.lower().title().replace(".", "")][
                    'title'] = title.lower().title().replace(".", "")
                publication_response['publications'][title.lower().title().replace(".", "")]['url'] = \
                pub.findChildren("h3", {"class": "gs_rt"})[0].findChildren("a")[0]["href"]
                publication_response['publications'][title.lower().title().replace(".", "")]['cited_by_scholar'] = \
                pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("div", {"class": "gs_fl"})[0].findChildren("a")[
                    2].get_text().split(" ")[2]
                publication_response['publications'][title.lower().title().replace(".", "")][
                    'cited_by_link_scholar'] = 'https://scholar.google.com' + \
                                               pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("div", {
                                                   "class": "gs_fl"})[0].findChildren("a")[2]["href"]
                # publication_response['publications'][title.lower().title().replace(".", "")][
                #     'publication_citation'] = publication_cites(
                #     publication_response['publications'][title.lower().title().replace(".", "")]['cited_by_link_scholar'])
                if len(pub.findChildren("div", {"class": "gs_or_ggsm"})):
                    publication_response['publications'][title.lower().title().replace(".", "")]['eprint'] = \
                    pub.findChildren("div", {"class": "gs_or_ggsm"})[0].findChildren("a")[0]["href"]
                else:
                    publication_response['publications'][title.lower().title().replace(".", "")]['eprint'] = ""
                publication_response['publications'][title.lower().title().replace(".", "")]['year'] = \
                re.findall(r"\d+", pub.findChildren("div", {"class": "gs_a"})[0].get_text())[
                    len(re.findall(r"\d+", pub.findChildren("div", {"class": "gs_a"})[0].get_text())) - 1]
        else:
            print('scholar publications null')
        scopus_author_data = requests.get(
            'http://api.elsevier.com/content/search/scopus?query=' + author_name + '&apiKey=acf90e6867d5a1b99ca5ba2f91935664').content
        decode_scopus_author_data = json.loads(scopus_author_data)
        for item in decode_scopus_author_data['search-results']['entry']:
            if item['dc:title'].lower().title().replace(".", "") in publication_response['publications']:
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'scopus_link'] = item['link'][2]['@href']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'scopus_aggregation_type'] = item['prism:aggregationType']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'scopus_subtype_description'] = item['subtypeDescription']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'publication_name'] = item['prism:publicationName']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'cited_by_scopus'] = item['citedby-count']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'cited_by_link_scopus'] = item['link'][3]['@href']

            else:
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")] = {}
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['title'] = \
                    item['dc:title'].lower().title().replace(".", "")
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")]['url'] = \
                    item['link'][2]['@href']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'aggregation_type_scopus'] = item['prism:aggregationType']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'subtype_description_scopus'] = item['subtypeDescription']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'publication_name'] = item['prism:publicationName']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'cited_by_scopus'] = item['citedby-count']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'cited_by_link_scopus'] = item['link'][3]['@href']
                publication_response['publications'][item['dc:title'].lower().title().replace(".", "")][
                    'eprint_scopus'] = '-'
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
                publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                    'title'] = \
                    item['info']['title'].lower().title().replace(".", "")
                publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                    'url'] = \
                    item['info']['url']
                publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                    'dblp_type'] = item['info']['type']
                if 'venue' in item['info']:
                    publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                        'dblp_venue'] = item['info']['venue']
                publication_response['publications'][item['info']['title'].lower().title().replace(".", "")][
                    'year'] = \
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

    # except Exception as e:
    # return jsonify({'error': str(err)})
    # else:
    return jsonify(publication_response)

@application.route('/get-citations-for-publication', methods=['POST'])
def get_citations_for_publications():
    author_name = request.json['authorName']
    publication_name = request.json['publicationName']
    article_semantic_link = ''
    response =  ''
    semantic_initial_url = 'https://www.semanticscholar.org/api/1/search'
    semantic_initial_payload = {
        "authors": [],
        "coAuthors": [],
        "externalContentTypes": [],
        "page": 1,
        "pageSize": 10,
        "performTitleMatch": True,
        "publicationTypes": [],
        "queryString": author_name,
        "requireViewablePdf": False,
        "sort": "relevance",
        "useRankerService": True,
        "venues": [],
        "yearFilter": None
    }
    headers = {"Content-Type": "application/json"}
    semantic_page_data = json.loads(
        requests.post(semantic_initial_url, data=json.dumps(semantic_initial_payload), headers=headers).content)
    semantic_author_id = semantic_page_data["results"][0]["authors"][0][0]['ids'][0]
    semantic_author_slug = semantic_page_data["results"][0]["authors"][0][0]['slug']
    semantic_author_details_url = "https://www.semanticscholar.org/author/" + semantic_author_slug + "/" + semantic_author_id
    semantic_author_page_data = BeautifulSoup(requests.get(semantic_author_details_url).content, 'html.parser')
    pages = semantic_author_page_data.find("ul", {"class": "pagination"}).findChildren("a")
    pages_arr = []
    for page in pages:
        if page.get_text().isdigit():
            pages_arr.append(int(page.get_text()))

    counter = 0
    while counter < len(pages_arr)-1:
        semantic_author_details_url = "https://www.semanticscholar.org/author/" + semantic_author_slug + "/" + semantic_author_id + "?page=" + str(pages_arr[counter])
        semantic_publications_data = BeautifulSoup(requests.get(semantic_author_details_url).content, 'html.parser')
        publications_containers = semantic_publications_data.find_all("article", {"class": "search-result"})
        for article in publications_containers:
            if article.find("a").find("span").find("span").get_text() == publication_name:
                article_semantic_link = "https://www.semanticscholar.org" + article.find("a")['href']
                counter = len(pages_arr)-1
                break
        if len(article_semantic_link) == 0:
            counter = counter + 1
    if len(article_semantic_link) == 0:
        return jsonify({"message": "Article not found on Semantic Scholar"})
    else:
        citations_pages = []
        citations_counter = 0
        citation_response = {}
        semantic_publications_data = BeautifulSoup(requests.get(article_semantic_link).content, 'html.parser')
        cites_number = int(semantic_publications_data.find("span", {"class": "scorecard_stat__headline__dark"}).get_text().split(" ")[0])
        if cites_number > 0:
            citations_pages_container = semantic_publications_data.find("div", {"class": "citation-pagination"}).findChildren("a")
            for page in citations_pages_container:
                if page.get_text().isdigit():
                    citations_pages.append(int(page.get_text()))
            while citations_counter < len(citations_pages)-1:
                paper_citation = semantic_publications_data.findChildren("div", {"class": "paper-citation"})
                for citation in paper_citation:
                    title = citation.find("div", {"class": "citation__body"}).find("a").find("span").find("span").get_text()
                    citation_response[title] = {}
                    citation_response[title]['title'] = title
                    citation_response[title]['link'] = "https://www.semanticscholar.org" + citation.find("div", {"class": "citation__body"}).find("a")["href"]
                citations_counter = citations_counter + 1

            return jsonify(citation_response)
        else:
            return jsonify({"message": "This article doesn't have citations on Semantic Scholar"})




def publication_cites(scholar_url):
    scholar_page = BeautifulSoup(requests.get(scholar_url).content, 'html.parser')
    author_publications = scholar_page.find("div", {"id": "gs_res_ccl"}).findChildren("div", {"class": "gs_scl"})
    publication_response = {}
    publication_response['publications'] = {}
    for pub in author_publications:
        title = \
        pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("h3", {"class": "gs_rt"})[0].findChildren("a")[
            0].get_text()
        publication_response['publications'][title.lower().title().replace(".", "")] = {}
        publication_response['publications'][title.lower().title().replace(".", "")][
            'title'] = title.lower().title().replace(".", "")
        publication_response['publications'][title.lower().title().replace(".", "")]['url'] = \
            pub.findChildren("h3", {"class": "gs_rt"})[0].findChildren("a")[0]["href"]
        print(title)
        print(pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("div", {"class": "gs_fl"})[0].findChildren("a")[2].get_text().split(" ")[2])
        publication_response['publications'][title.lower().title().replace(".", "")]['cited_by_scholar'] = pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("div", {"class": "gs_fl"})[0].findChildren("a")[2].get_text().split(" ")[2]
        publication_response['publications'][title.lower().title().replace(".", "")][
            'cited_by_link_scholar'] = 'https://scholar.google.com' + pub.findChildren("div", {"class": "gs_ri"})[0].findChildren("div",{"class": "gs_fl"})[0].findChildren("a")[2]["href"]
        if len(pub.findChildren("div", {"class": "gs_or_ggsm"})):
            publication_response['publications'][title.lower().title().replace(".", "")]['eprint'] = \
                pub.findChildren("div", {"class": "gs_or_ggsm"})[0].findChildren("a")[0]["href"]
        else:
            publication_response['publications'][title.lower().title().replace(".", "")]['eprint'] = ""
        publication_response['publications'][title.lower().title().replace(".", "")]['year'] = \
            re.findall(r"\d+", pub.findChildren("div", {"class": "gs_a"})[0].get_text())[
                len(re.findall(r"\d+", pub.findChildren("div", {"class": "gs_a"})[0].get_text())) - 1]

    return publication_response


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
