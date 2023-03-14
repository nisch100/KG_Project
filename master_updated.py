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



def handle_investigation(category,search_term):
	match = {'match':{category:search_term}}
	fuzzy = {'fuzzy':{category:search_term}}
	result_match = es.search(index='original',query=match)
	match_lst = result_match['hits']['hits']
	if len(match_lst) == 10:
		return match_lst
	fuzzy_match = es.search(index='original',query=fuzzy)
	match_lst = fuzzy_match['hits']['hits']
	match_lst.extend(fuzzy_lst)
	idx  =max(10, len(match_lst))
	return match_lst[:idx]



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

		elif category in set(['victim','area_of_occurrence']):
			info_dict[i['_source']['case-id']][category] = i['_source'][category]	

		else:
			info_dict[i['_source']['case-id']][category] = i['_source'][category]

	return flagger,info_dict





neo4jdict = {"Case-ID":"CaseID","Detectives" :"detective","Area":"Area","witnesses":"Witness","suspects":"Suspect","involved":"Involved"}
category = input("Enter Category : ")
search_term = str(input("Enter Search term ?"))
search_term = search_term.lower().strip()
if category == "Investigation_Text":
	result_list = handle_investigation(category,search_term)
else:
	result_list = handle_rest(category,search_term)

flagger,info_dict = print_hits(result_list,category,search_term)

if category == "case-id":
	if search_term in info_dict:
		print(info_dict[search_term])
	else:
		neodriver.case(search_term)


elif category in set(["detectives","suspects","witnesses","involved"]):
	getlist = neodriver.person_builder(search_term)
	if len(getlist[category]) != 0:
		print(getlist)
	else:
		for k, v in info_dict.items():
			for v1,v2 in v.items():
				print(v1," : ",v2)

elif category in set(["weapon","car","license"]):
	getlist = neodriver.objectSearch(search_term,category)
	if len(getlist) == -1:
		print(getlist)
	else:
		print("Info dict ",info_dict)
		for k, v in info_dict.items():
			for v1,v2 in v.items():
				print(v1," : ",v2)

