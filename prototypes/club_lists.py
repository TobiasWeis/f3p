import requests
import json

pagesize=40
pages = 2

for p in range(pages):
    offset = p * pagesize
    print("---- page",p,", offset",offset)
    url = f"https://www.fitnessfirst.de/api/v1/node/club_page?include=field_features,field_opening_times,field_label_logo.image&filter[status][value]=1&page[limit]={pagesize}&page[offset]={offset}&sort=title"


    response = requests.get(url)

    if response.status_code == 200:
        res = json.loads(response.content.decode('utf-8'))
        data = res['data']

        for datum in data:
            attribs = datum['attributes']
            print(attribs['field_easy_solution_club_id'],attribs['field_club_cms_identifier'])
