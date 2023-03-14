from elasticsearch import Elasticsearch, helpers
import configparser
import pandas as pd
import spacy
from spacy import displacy
from spacy.tokens import Span
from spacy.matcher import Matcher
import json
config = configparser.ConfigParser()
config.read('search.ini')

es = Elasticsearch(
    cloud_id=config['ELASTIC']['cloud_id'],
    http_auth=(config['ELASTIC']['user'], config['ELASTIC']['password'])
)
print("Deployment Information ", es.info())



'''
Preprocess CSV
'''

path = 'Relevantfiles/'
df = pd.read_csv(path + 'df.csv')
nlp = spacy.load("en_core_web_trf")
def camel_case_split(original_token):
  import re
  matches = re.finditer('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)', original_token)
  return [m.group(0) for m in matches]
def clean_investigation(text):
  text = str(text)
  no_dot_token_list = text.replace("·"," ").replace("/"," / ").replace(")"," ) ").replace("("," ( ").replace(".", ". ").split()
  refined_token_list = []
  for token in no_dot_token_list:
    refined_token_list += camel_case_split(token)

  return " ".join(refined_token_list)

df["Investigation"] = df["Investigation"].apply(lambda text : clean_investigation(text))
caselist = set(df['DR'])
d = {}
print(f"Number of cases {len(caselist)}")
for i in caselist:
	samples = df[df['DR'] == i]
	s = ""
	detective_first = ""
	detective_two = ""
	victim_first = ""
	victim_last = ""
	conjoin = ""
	conjoin1 = ""
	area_of_occurence = ""
	date_of_occurence = ""
	if i not in d:
		d[i] = {}
	for idx, row in samples.iterrows():
		detective_first = row['Detective 1'] if row['Detective 1'] else detective_first
		detective_two  =  row['Detective 2'] if row['Detective 2'] else detective_two

		victim_first = row['Victime First Name'] if row['Victime First Name'] else victim_first
		victim_last  =  row['Victim Last Name'] if row['Victim Last Name'] else victim_last

		area_of_occurence = row['Area of Occurrence'] if row['Area of Occurrence'] else area_of_occurence
		conjoin = " & " if detective_first and detective_two else conjoin
		conjoin1 = " " if victim_first and victim_last else conjoin1
		s += str(row['Investigation']) + "<EOS>"
		date_of_occurence = row['Date of Occurrence 1'] if row['Date of Occurrence 1'] else date_of_occurence

	d[i]['Investigation_Text'] = s
	d[i]['Detective'] = str(detective_first) + conjoin + str(detective_two) 
	d[i]['Victim'] = str(victim_first) + conjoin1 + str(victim_last) 
	d[i]['Area_of_Occurrence'] = area_of_occurence
	d[i]['Date_of_Occurrence'] = str(date_of_occurence) 



'''
Process Suspects, Witness and other involved people
'''
with open(path + "suspect_homicide.json", "rb") as f:
  suspect = json.load(f)

with open(path + "witness_homicide.json", "rb") as f:
  witness = json.load(f)

with open(path + "involvedpeople_homicide.json", "rb") as f:
  involved = json.load(f)


with open(path + "Relation_dump.json", "rb") as f:
	eventrelation = json.load(f)



'''
Process Object Based Entities
'''
with open(path + "Matcher_dump.json", "rb") as f:
	objectcase = json.load(f)
	print(len(objectcase.keys()))


def getobject(caseid,category):
	if caseid in objectcase and category in objectcase[caseid]:
		return " | ".join(objectcase[caseid][category])
	return ""



'''
INGESTING DATA
'''

index_name = "original"

if es.indices.exists(index = index_name):
	print("Found")
	#es.indices.delete(index=index_name)
for k,v in d.items():
	print(eventrelation[k])
	weapon = 'Nan'
	car = 'Nan'
	license = 'Nan'
	es.index(
 index=index_name,
 document={
  'case-id': k,
  'investigation_text': d[k]['Investigation_Text'],
  'victim': d[k]['Victim'],
  'detectives':d[k]['Detective'],
  'area_of_occurrence':d[k]['Area_of_Occurrence'],
  'date_of_occurrence':d[k]['Date_of_Occurrence'],
  'witnesses': " | ".join(witness[k])if witness[k] else "No Witnesses" ,
  'involved': " | ".join(involved[k]) if involved[k] else "No people involved" ,
  'suspects':" | ".join(suspect[k])if suspect[k] else "No Suspects" ,
  'events' : eventrelation[k] if eventrelation[k] else "No Events"  ,
  'weapon' : getobject(k,"weapon"),
  'cars' : getobject(k,"car"),
  'license' : getobject(k,"license")
 })


es.indices.refresh(index=index_name)