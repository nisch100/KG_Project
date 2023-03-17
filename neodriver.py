from neo4j import GraphDatabase
from collections import defaultdict
uri = "neo4j://localhost:7687"

''''''

connect = GraphDatabase.driver(uri, auth=("neo4j", "password"))

session = connect.session()


neo4jdict = {"Case-ID":"CaseID","detectives" :"Detective","Area":"Area","witnesses":"Witness","suspects":"Suspect","involved":"Involved",\
"cars":"Vehicle","weapon":"Weapon","license":"License","victim":"Victim"}

def area(name,category):
	lst = {}
	lst[name] = set()
	query = f"""MATCH (n:AreaOfOccurrence)-[r]-(p) where tolower(n.name) = "{name}" return n,r,p"""
	matchall = session.run(query)
	for i in matchall:
		relation_type  = i['r'].type
		caseFound = relation_type == 'caseFound'
		if caseFound:
			lst[name].add(i['p']['UID'])
	return lst



def objectSearch(name,category):
	name = name.lower()
	lst = {}
	lst[name]  =set()
	query = query = f"""
	MATCH (n:{neo4jdict[category]}{{Name:"{name}"}})-[r:{neo4jdict[category]}]->(p:CaseID) 
	RETURN n, r, p"""
	matchall = session.run(query)
	for i in matchall:
		relation_type  = i['r'].type
		caseFound = relation_type == str(neo4jdict[category])
		if caseFound:
			lst[name].add(i['p']['UID'])
	return lst




def persons(name,category):
	name = name.lower()
	lst = set()
	query = query = f"""
	MATCH (n:Person{{Name:"{name}"}})-[r:Associated{{type:"{neo4jdict[category]}"}}]->(p:CaseID) 
	RETURN n, r, p"""
	matchall = session.run(query)
	for i in matchall:
		relation_type  = i['r'].type
		caseFound = relation_type == 'Associated'
		if caseFound:
			lst.add(i['p']['UID'])
	return lst

def person(name, category):
	lst = set()
	if category == "detectives":
		query = f"""
	MATCH (n:Detective)-[r:DetectiveFor]->(p:CaseID) where toLower(n.Det_name) = toLower("{name}")  return n,r,p
	"""
	else:
		print("Ran victim search")
		query = f"""
	MATCH (n:Victim)-[r:caseHasVictim]->(p:CaseID) where toLower(n.Name) = toLower("{name}")  return n,r,p
	"""
	matchall = session.run(query)
	for i in matchall:
		print(i)
		relation_type  = i['r'].type
		caseCheck = relation_type == 'DetectiveFor' or relation_type == 'caseHasVictim'
		if caseCheck:
			lst.add(i['p']['UID'])
	return lst


def person_builder(name):
	persondict = {"detectives":"Detective","witnesses":"Witness","suspects":"Suspect","involved":"Involved","victim":"Victim"}
	associated_cases = defaultdict(list)
	for k,v in persondict.items():
		if k not in  set(["detectives","victim"]):
			print("K ",k)
			lst = persons(name,k)
			associated_cases[k]  = lst if lst else []
		else:
			lst = person(name,k)
			associated_cases[k]  = lst if lst else []

	return associated_cases

	

def case(caseID):
	query = f"""
	MATCH (n:CaseID{{UID:"{caseID}"}})-[r]-(p) return n,r,p
	"""
	build_dict = defaultdict(set)
	matchall = session.run(query)
	for i in matchall:
		#print(i['p'],i['r'].type)
		relation_type  = i['r'].type
		caseHasDetective = relation_type == 'caseHasDetective'
		SimilarCase = relation_type == 'SimilarCase'
		if SimilarCase:
			build_dict[relation_type].add(i['p']['UID'])
		elif caseHasDetective:
			build_dict[relation_type].add(i['p']['Det_name'])
		elif relation_type == 'hasChronoEntry':
			continue
		else:
				build_dict[relation_type].add(i['p']['Name'])

		'''
		if 'Victim_Last_Name' in i['p'] or 'Victim_First_Name' in i['p'] :
			lastname = '' if 'Victim_Last_Name' not in i['p'] else i['p']['Victim_Last_Name']
			firstname = '' if 'Victim_First_Name' not in i['p'] else i['p']['Victim_First_Name']
			name = lastname + '|' + firstname
			print("Victim_Name ",name)

		'''
	print(build_dict,len(build_dict['SimilarCase']))


'''	

caseID = '00-0330058'
case(caseID)

print("-*" * 30)

name = 'ChaVeZ'
person("Detective", name)

print("-*" * 30)

name = 'harbor'
area(name)

'''

'''
query = "MATCH (n:CaseID{UID:'00-0330058'})-[r]-(p) return n,p"
matchall = session.run(query)
for i in matchall:
	print(i)
	continue
	if 'Det_name' in i['p']:
		print("Detective_Name ",i['p']['Det_name'])
	if 'Victim_Last_Name' in i['p'] or 'Victim_First_Name' in i['p'] :
		lastname = '' if 'Victim_Last_Name' not in i['p'] else i['p']['Victim_Last_Name']
		firstname = '' if 'Victim_First_Name' not in i['p'] else i['p']['Victim_First_Name']
		name = lastname + '|' + firstname
		print("Victim_Name ",name)
	
'''