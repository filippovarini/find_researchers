Before starting, you need to setup authentication for ([Scopus API](https://dev.elsevier.com/)):
1. Get API key 
2. Create a .env file copying the .env.example file and paste your API key in the .env file

Instructions:
1. Install the requirements: `pip install -r requirements.txt`
2. Run the application: `python main.py`
3. Send request from your browser at `http://localhost:8000`

Use Cases:
1. Get the list of most cited **papers** for your keywords:
  a. Run the app and navigate to localhost:8000
  b. Run the following GET request: `http://localhost:8000/get_paper_info/?query=TITLE-ABS-KEY((shark+OR+sharks)+AND+(bruv+OR+bruvs))`
    In this case, we look for papers with "shark" or "sharks" and "bruv" or "bruvs" in the title, abstract, or keywords. 
  c. You can also download a CSV of the papers by setting the parameter `spreadsheet=true` in the query.

2. Get list of most cited **authors** and associated papers:
  a. Run the app and navigate to localhost:8000
  b. Run the following GET request: `http://localhost:8000/get_author_info/?query=TITLE-ABS-KEY((shark+OR+sharks)+AND+(bruv+OR+bruvs))&spreadsheet=false`
    In this case, we look for papers with "shark" or "sharks" and "bruv" or "bruvs" in the title, abstract, or keywords. 
  c. You can also download a CSV of the authors by setting the parameter `spreadsheet=true` in the query.
