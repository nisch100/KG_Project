import builtins
from flask import Flask, render_template, request
from elasticsearch import Elasticsearch, helpers
import configparser
from neo4j import GraphDatabase
from collections import defaultdict
import nltk
import neodriver


uri = "neo4j://localhost:7687"
connect = GraphDatabase.driver(uri, auth=("neo4j", "password"))
session = connect.session()

config = configparser.ConfigParser()
config.read('search.ini')
es = Elasticsearch(
    cloud_id=config['ELASTIC']['cloud_id'],
    http_auth=(config['ELASTIC']['user'], config['ELASTIC']['password'])
)
es.info()


app = Flask(__name__)

# define the options for the dropdown menu
options = ["victim", "involved", "area_of_occurrence", "investigation_text", "detectives","witnesses","case-id","cars","license","weapon", "suspects"]
neo4jdict = {"Case-ID":"CaseID","Detectives" :"detective","Area":"Area","witnesses":"Witness"\
,"suspects":"Suspect","involved":"Involved","cars":"Vehicle"}



def handle_investigation(category,search_term):
    match = {'match':{category:search_term}}
    fuzzy = {'fuzzy':{category:search_term}}
    result_match = es.search(index='original',query=match)
    match_lst = result_match['hits']['hits']
    if len(match_lst) == 10:
        return result_match
    result_match = es.search(index='original',query=fuzzy)
    match_lst = result_match['hits']['hits']
    idx  =max(15, len(match_lst))
    return result_match



def fetch_results(keypair):
    result = es.search(
 index='original',
  query=keypair
 )
    return result


def handle_rest(category,search_term):

    keypair = {'match':{category:search_term}}
    matches = fetch_results(keypair)
    if len(matches['hits']['hits']) == 0:
        print("Fuzzy search run")
        keypair = {'fuzzy':{category:search_term}}
        matches = fetch_results(keypair)
    return matches



def is_dict(value):
    return isinstance(value, dict)


def is_set(value):
    return isinstance(value, set)


def category_list(category,lst):
    s = set()
    for i in lst:
        if category not in i['_source']:
            continue
        if type(i['_source'][category]) == list: 
            s |= set([x.lower() for x in i['_source'][category]])
        else:
            s.add(i['_source'][category])
    return s




def print_hits(result,category,search_term):
    lst = result['hits']['hits']
    info_dict = {}
    lstcheck = category_list(category,lst)
    flagger = True if search_term.lower() in lstcheck else False
    for i in lst:
        if i['_source']['case-id'] not in info_dict:
            info_dict[i['_source']['case-id']] = {}
            info_dict[i['_source']['case-id']]['case-id'] = i['_source']['case-id']
            info_dict[i['_source']['case-id']]['detectives'] = i['_source']['detectives']

        if category == "case-id":
            if search_term.lower() == i['_source'][category]:
                    for k,v in i['_source'].items():
                        info_dict[i['_source']['case-id']][k] = v
            else:
                    info_dict[i['_source']['case-id']][category] = i['_source'][category]  

        elif category == "investigation_text": 
            for k,v in i['_source'].items():
                search_term = search_term.lower()
                get_text = i['_source'][category].replace("<EOS>","").lower()
                ind  = get_text.find(search_term)
                mini = max (0, ind - 400)
                maxi = min(ind + 400, len(get_text))
                info_dict[i['_source']['case-id']][category] = "......" + str(get_text[mini:maxi]) + "......."

        else:
            info_dict[i['_source']['case-id']][category] = i['_source'][category]

    return flagger,info_dict





@app.route('/', methods=['GET', 'POST'])
def index():
    new_lst = []
    if request.method == 'POST':
        category = request.form['dropdown']
        search_term = request.form['text']
        search_term = search_term.lower().strip()
        if category == "investigation_text":
            result_list = handle_investigation(category,search_term)
            print("Keys of result ", result_list.keys())
        else:
            result_list = handle_rest(category,search_term)
        flagger,info_dict = print_hits(result_list,category,search_term)

        if category == "case-id":
            if search_term in info_dict:
                new_lst.append(info_dict[search_term])
            else:
                neodriver.case(search_term)

        elif category == "investigation_text":        
            for k, v in info_dict.items():
                new_lst.append(v)
        elif category in set(["detectives","suspects","witnesses","involved","victim"]):
            getlist = neodriver.person_builder(search_term)
            print("Ran Neo search",getlist)
            if len(getlist[category]) != 0:
                new_lst.append(getlist)
            else:
                for k, v in info_dict.items():
                    new_lst.append(v)
        elif category in set(["weapon","cars","license"]):
            print("Info dict ",info_dict)
            getlist = neodriver.objectSearch(search_term,category)
            if len(getlist[search_term]) != 0:
                new_lst.append(getlist)
            else:
                print("Info dict ",info_dict)
                for k, v in info_dict.items():
                    new_lst.append(v)
        else:
            getlist = neodriver.area(search_term,category)
            if len(getlist) != 0:
                new_lst.append(getlist)
            else:
                for k, v in info_dict.items():
                    new_lst.append(v)

    print("List right before being rendered ",type(new_lst),new_lst)
    return render_template('index.html', options=options, new_lst=new_lst)


if __name__ == '__main__':
    app.run(debug=True)
