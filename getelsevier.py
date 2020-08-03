#pip install fuzzywuzzy
    
# importing library 
import requests 
import pandas as pd
from fuzzywuzzy import fuzz
import os
import math
def getelsevier(doi):

    #URL generator: Incase the key exhausts the limit, go to https://dev.elsevier.com/index.html to generate a new one
    def scopus_search(query):

        # Example of DOI input: '10.1016/j.jesp.2018.04.001'

        doi = query.replace('/','%2F')  # For generating the URL correctly
        url = 'https://api.elsevier.com/content/search/scopus?query=' + doi + '&apiKey=7f59af901d2d86f78a1fd60c1bf9426a'
        return url

    def serial_title(query):

        # Example of ISSN input: '00221031'

        issn = query
        url = 'https://api.elsevier.com/content/serial/title/issn/' + issn + '?apiKey=e696bf014b5d2a4f223cf9eac5ff364d'
        return url

    #Function to return result as row

    def return_scopus(r,query):
        status = r.status_code
        query = str(query)

        #Checking the status code: success_code = 200. Otherwise, return empty row
        if status!=200:
            #print('Error_status')
            row = {'prism:doi':query, 'prism:issn':'0', 'source-id':'0'}
            empty= pd.DataFrame(data = row, index = [0])
            return empty
        
        # Interpretating the Json response to give a dataframe
        data = r.json()
        search_results = data['search-results']
        df_search = pd.json_normalize(search_results)
        df = df_search['entry']
        df = df.tolist()
        entry = pd.json_normalize(df[0])
        doi_entry = entry['prism:doi']
        # To avoid overlapping columns
        entry = entry.rename(columns = {'prism:url':'article_url','openaccess':'openaccess_article', 'dc:title':'dc:title_article', 'prism:aggregationType':'prism:aggregationType_article'})
        # Selecting only necessary features
        entry = pd.DataFrame(data = entry.loc[:,['prism:issn', 'prism:doi','source-id','citedby-count', 'openaccessFlag']])

        # Getting the entry which matches the title of the required paper otherwsie return empty row
        for i in range(len(entry)):
            doi_check = str(doi_entry[i])
            if doi_check.lower()==query.lower():
                row = entry.iloc[i,:]
                row = pd.DataFrame(row)
                row = row.transpose()
                return row
        #print('Error:', query)
        row = {'prism:doi':query, 'prism:issn':'0', 'source-id':'0'}
        empty= pd.DataFrame(data = row, index = [0])
        return empty
    
    def return_row(r,query):
            status = r.status_code

            #Checking the status code: success_code = 200. Otherwise, return empty row
            if status!=200:
                #print('Error_status')
                #print(status)
                empty = {'source-id':'0'}
                empty= pd.DataFrame(empty, index = [0])
                return empty
            else:
                # Interpretating the Json response to give a dataframe
                data = r.json()
                search_results = data['serial-metadata-response']
                df = search_results['entry']
                entry = pd.json_normalize(df[0])
                # To avoid overlapping columns
                entry = entry.rename(columns = {'prism:issn': 'issn', 'prism:eIssn': 'eIssn'})
                # Selecting only necessary features
                data_entry = entry.loc[:,['source-id','SJRList.SJR','SNIPList.SNIP','citeScoreYearInfoList.citeScoreCurrentMetric', 'citeScoreYearInfoList.citeScoreCurrentMetricYear','citeScoreYearInfoList.citeScoreTracker','citeScoreYearInfoList.citeScoreTrackerYear','subject-area']]
                entry = pd.DataFrame(data_entry)

                # Subject-area json response to columns(only subject is chosen as feature)
                sub = entry['subject-area']
                list = sub[0]
                subject_row = pd.DataFrame()
                for i in range(len(list)):
                    subject= pd.json_normalize(list[i])
                    col1 = "@_fa_Subject_"+str(i)
                    col2 = "@code_subject_"+str(i)
                    col3 = "@abbrev_"+str(i)
                    col4 = "Subject_"+str(i)
                    subject = subject.rename(columns={"@_fa":col1, "@code": col2,"@abbrev":col3, "$":col4})
                    subject = subject.drop([col1, col2, col3],axis = 1)
                    subject_row = pd.concat([subject_row,subject], axis = 1)    

                # SJR and SNIP indicator json responses to columns
                SJR = entry['SJRList.SJR']
                SNIP = entry['SNIPList.SNIP']
                SJR = pd.json_normalize(SJR[0])
                SJR = SJR.rename(columns={"@year": "@year_SJR", "$":"SJR"})
                SJR = SJR.drop(["@_fa"],axis = 1)
                SNIP = pd.json_normalize(SNIP[0])
                SNIP = SNIP.rename(columns={"@year": "@year_SNIP", "$":"SNIP"})
                SNIP = SNIP.drop(["@_fa"],axis = 1)
                entry = entry.drop(['subject-area', 'SJRList.SJR', 'SNIPList.SNIP'], axis = 1)
                row = pd.concat([entry,SNIP, SJR, subject_row],ignore_index=False, axis =1)
                return row

    # Scopus search api
    output = pd.DataFrame()
    
    query =doi
    temp = query
    try:
        if math.isnan(temp)==True:
            #print('Error_no_input')
            row = {'prism:doi':query, 'prism:issn':'0', 'source-id':'0'}
            output= pd.DataFrame(data = row, index = [0]) 
    except :
        # api-endpoint: 
        URL = scopus_search(query)
        # sending get request and saving the response as response object 
        r = requests.get(URL)
        #response = return_scopus(r,query)
        output = return_scopus(r,query)
        
           

    # Add 0's in the beginning of output from Scopus Search API
    issn = output['prism:issn']
    issn = str(issn.iloc[0])
    l = len(issn)
    if l!=8:
        issn=issn.ljust(8, '0')

    # Serial Title API
    output2 = pd.DataFrame()
    query =issn
    # api-endpoint: 
    URL = serial_title(query)
    # sending get request and saving the response as response object 
    r = requests.get(URL)
    response = return_row(r,query)
    output2 = output2.append(response, ignore_index=True)

    # Merging the output of the two apis to return Dataframe with required columns 
    final = pd.merge(output, output2,on='source-id', how = 'outer')
    return final

os.chdir('D:/Grad/Work/Score/Elsevier/')
data = pd.read_csv('output.csv')
# List of dois 
dois = data['DOI_CR']
for i in range(len(dois)):
    doi = dois.iloc[i]
    final = getelsevier(doi)
    print(final)
