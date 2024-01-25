from flask import Flask, Response, jsonify, request
from dotenv import load_dotenv
import requests
import csv
import io
import os

load_dotenv()

API_KEY = os.environ.get('API_KEY')

app = Flask(__name__)

COUNT = 20

def get_paper(query):
  """
  Parameters
  ----------
  Query follows the same style of Scopus API query. For example, 
  to get all the papers that have "shark" and "bruv" in the title, abstract or 
  list of keywords, the query is:
  TITLE-ABS-KEY(shark+AND+bruv)
  If we also want to get the plural, the query becomes:
  TITLE-ABS-KEY((shark+OR+sharks)+AND+(bruv+OR+bruvs))
  """
  url = f"https://api.elsevier.com/content/search/scopus?query={query}&apiKey={API_KEY}&count={COUNT}&sort=citedby-count"

  response = requests.get(url)

  headers = {
    'X-RateLimit-Limit': response.headers.get('X-RateLimit-Limit'),
    'X-RateLimit-Remaining': response.headers.get('X-RateLimit-Remaining'),
    'X-RateLimit-Reset': response.headers.get('X-RateLimit-Reset')
  }

  return response.json(), headers


def get_paper_and_authors(query):
  papers, headers = get_paper(query)

  results = []
  for entry in papers['search-results']['entry']:
    citedby_count = entry.get('citedby-count')
    title = entry.get('dc:title')
    link = next((obj['@href'] for obj in entry['link'] if obj['@ref'] == 'author-affiliation'), None)

    author_link = link + '&apiKey=' + API_KEY
    headers = {
      'Accept': 'application/json'
    }
    print(author_link)
    authors = requests.get(author_link, headers=headers)

    result = {
      'citedby_count': citedby_count,
      'title': title,
      'authors_link': link,
      'authors': extract_author_info(authors.json())
    }
    results.append(result)
  
  return results, headers


def extract_author_info(authors):
  extracted_authors = []
  affiliations = authors['abstracts-retrieval-response'].get('affiliation', [])
  if not isinstance(affiliations, list):
    affiliations = [affiliations]
  
  author_list = authors['abstracts-retrieval-response']['authors']['author']
  
  
  for author in author_list:
    given_name = author.get('ce:given-name', author.get('ce:indexed-name'))
    surname = author.get('ce:surname', '')

    author_affiliations = author.get('affiliation', [])
    # If single affiliation, return an object, instead than a list of objects
    if not isinstance(author_affiliations, list):
      author_affiliations = [author_affiliations]
    
    affiliation_names = [aff['affilname'] for aff in author_affiliations]
    print(affiliation_names)
    
    extracted_authors.append({'given_name': given_name, 'surname': surname, 'affiliations': list(set(affiliation_names))})
  
  return extracted_authors


def write_spreadsheet(data, data_type):
    si = io.StringIO()
    cw = csv.writer(si)

    if data_type == 'papers':
        # Write the header row for papers
        cw.writerow(['Title', 'Citations'])

        # Iterate over the paper results and write to the CSV
        for item in data:
            cw.writerow([item['title'], item['citedby_count']])

    elif data_type == 'papers_authors':
        # Write the header row for papers
        cw.writerow(['Title', 'Citations', 'Authors'])

        # Iterate over the paper results and write to the CSV
        for item in data:
            authors = '; '.join([f"{author['given_name']} {author['surname']} ({', '.join(author['affiliations'])})" 
                                 for author in item['authors']])
            cw.writerow([item['title'], item['citedby_count'], authors])

    elif data_type == 'authors':
        # Write the header row for authors
        cw.writerow(['Author', 'Total Citations', 'Affiliations', 'Papers'])

        # Iterate over the author results and write to the CSV
        for item in data:
            papers = '; '.join(item['papers'])
            affiliations = ', '.join(item['affiliations'])
            cw.writerow([item['name'], item['citedby_count'], affiliations, papers])

    si.seek(0)
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers["Content-Disposition"] = "attachment; filename=data.csv"
    return output


@app.route('/papers/', methods=['GET'])
def get_papers():
  """
  Gets only information about paper
  Args:
    query: string - follows the same style of Scopus API query. For example, 
      to get all the papers that have "shark" and "bruv" in the title, 
      abstract or list of keywords, the query is:
      TITLE-ABS-KEY(shark+AND+bruv)
      If we also want to get the plural, the query becomes:
      TITLE-ABS-KEY((shark+OR+sharks)+AND+(bruv+OR+bruvs))
    spreadsheet: boolean - if True, returns the spreadsheet of the papers
  """
  query = request.args.get('query')
  
  results, headers = get_paper(query)

  spreadsheet = request.args.get('spreadsheet')
  if spreadsheet == 'true':
    return write_spreadsheet(results, data_type='papers')
  else:
    response = {
      'results': results,
      'headers': headers
    }

    return jsonify(response)
  

@app.route('/get_paper_info/', methods=['GET'])
def get_paper_info():
  """
  Args:
    query: string - follows the same style of Scopus API query. For example, 
      to get all the papers that have "shark" and "bruv" in the title, 
      abstract or list of keywords, the query is:
      TITLE-ABS-KEY(shark+AND+bruv)
      If we also want to get the plural, the query becomes:
      TITLE-ABS-KEY((shark+OR+sharks)+AND+(bruv+OR+bruvs))
    authors: boolean - if True, returns the authors of each paper
    spreadsheet: boolean - if True, returns the spreadsheet of the papers
  """
  query = request.args.get('query')
  
  results, headers = get_paper_and_authors(query)

  spreadsheet = request.args.get('spreadsheet')
  if spreadsheet == 'true':
    return write_spreadsheet(results, data_type='papers_authors')
  else:
    response = {
      'results': results,
      'headers': headers
    }

    return jsonify(response)
  
"""
add another route, that returns the most prominent authors in the field you are interested. The algorithm should be the following:

1. get the papers and associated authors using the above method. 
2. then iterate through the papers, and construct a priority list of the authors, which can appear in multiple papers. The priority should be based on the sum of citation of the papers they have contributed to
"""
@app.route('/get_author_info/', methods=['GET'])
def get_authors_info():
  query = request.args.get('query')
  paper_authors, headers = get_paper_and_authors(query)

  authors = {}

  for paper in paper_authors:
    for author in paper['authors']:
      author_name = f"{author['given_name']} {author['surname']}"
      if author_name not in authors:
        authors[author_name] = {'affiliations': author['affiliations'], 'citedby_count': 0, 'papers': []}
      authors[author_name]['citedby_count'] += int(paper['citedby_count'])
      authors[author_name]['papers'].append(paper['title'])

  sorted_authors = sorted(authors.items(), key=lambda x: x[1]['citedby_count'], reverse=True)

  # convert into a list of dicts
  sorted_authors = [{'name': author[0], 'citedby_count': author[1]['citedby_count'], 'affiliations': author[1]['affiliations'], 'papers': author[1]['papers']} for author in sorted_authors]

  spreadsheet = request.args.get('spreadsheet')

  if spreadsheet == 'true':
    return write_spreadsheet(sorted_authors, data_type='authors')
  else:
    response = {
      'results': sorted_authors,
      'headers': headers
    }

    return jsonify(response)





if __name__ == '__main__':
    app.run(port=8000)