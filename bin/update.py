import requests
from bs4 import BeautifulSoup
from datetime import datetime
from itertools import groupby
from collections import OrderedDict
from tabulate import tabulate
import json
import os

if not os.path.exists("ranks"):
    os.makedirs("ranks")
if not os.path.exists("details"):
    os.makedirs("details")    

gh_link = "https://api.github.com/repos/cmgchess/Titled-Tuesday-Data/git/trees/main?recursive=1"
response = requests.get(gh_link)
data = response.json()
print("started")

file_names = [obj["path"].replace("ranks/", "").replace(".json", "") for obj in data["tree"] if obj["path"].startswith("ranks/")]

base_url = 'https://www.chess.com/tournament/live/'

tt = 'https://www.chess.com/tournament/live/titled-tuesdays'
tourn_links = []
for i in range(1):
  r = requests.get(tt+'?&page='+str(i+1))
  soup = BeautifulSoup(r.content, 'html.parser')
  tourn_list = soup.find('table', class_ = 'table-component table-hover table-clickable tournaments-live-table')
  tourn_table_rows = tourn_list.find_all('tr')
  tourn_table_rows = tourn_table_rows[1:]
  for j in tourn_table_rows:
    tourn_link = j.find('a', class_='tournaments-live-name')['href']
    tourn_links.append(tourn_link)

for url in tourn_links:
  parts = url.split('/')
  tournament_id = parts[-1]
  write_to = f"{tournament_id}.json"
  if tournament_id in file_names:
    print("File already exists: " + tournament_id)
    continue
  r = requests.get(url+'?&players=100')
  soup = BeautifulSoup(r.content, 'html.parser')
  i_p = soup.find('div', class_ = 'index-pagination')
  data_total_pages = 0
  if i_p:
    data_total_pages = int(i_p.find('div')['data-total-pages'])
  print("total pages: " + str(data_total_pages))

  ranks  = []
  rank = 0
  for i in range(data_total_pages):
    print('page: ' + str(i+1))
    r = requests.get(url+'?&players='+str(i+1))
    soup = BeautifulSoup(r.content, 'html.parser')
    table = soup.find('table', class_ = 'table-component tournaments-live-view-results-table tournaments-live-view-extra-borders')
    table_rows = table.find_all('tr')
    table_rows = table_rows[1:]
    for x in table_rows:
      rank +=1
      if rank%100 == 0:
        print("completed: "+str(rank))
      username = x.select_one('.user-tagline-username').get_text(strip=True)
      country = x.select_one('.country-flags-component')['v-tooltip']
      rating = x.select_one('.user-rating').get_text(strip=True).replace('(','').replace(')','')
      if (rating != 'Unrated'):
        rating = int(rating)
      title_element = x.select_one('.post-view-meta-title')
      title = title_element.get_text(strip=True) if title_element is not None else None
      score = float(x.select_one('.tournaments-live-view-total-score').get_text(strip=True))
      tie_break = float(x.select_one('.tournaments-live-view-tie-break').get_text(strip=True))
      wdb = x.find('div', class_='tournaments-live-view-total-score')['v-tooltip'].split(',')
      wins = int(wdb[0].strip().split()[0])
      draws = int(wdb[1].strip().split()[0])
      byes = int(wdb[2].strip().split()[0])
      player = {
      "rank": rank,
      "username": username,
      "country": country,
      "rating": rating,
      "title": title,
      "score": score,
      "tie_break": tie_break,
      "wins": wins,
      "draws": draws,
      "byes": byes
      }
      ranks.append(player)

  with open("ranks/"+write_to, 'w') as json_file:
    json.dump(ranks, json_file, indent=4)
    file_names.append(tournament_id)
  print("written: " + write_to)

current_year = datetime.now().year
last_year = current_year - 1
last_and_current = [filename for filename in file_names if str(current_year) in filename or str(last_year) in filename]



events = []
for i in last_and_current:
  r = requests.get(base_url+i)
  soup = BeautifulSoup(r.content, 'html.parser')
  name_el = soup.find('h1', class_='v5-title-label')
  name = name_el.get_text().strip()
  print("processing: " + name)
  stats_el = soup.find('div', class_='tournaments-live-view-content-stats')
  span_elements = stats_el.find_all('span')
  number_of_players = int(span_elements[1].get_text(strip=True).split()[0])
  date_and_time = span_elements[2].get_text(strip=True)
  parsed_date = datetime.strptime(date_and_time, "%b %d, %Y, %I:%M %p")
  formatted_date = parsed_date.strftime("%d.%m.%Y")
  formatted_time = parsed_date.strftime("%I:%M %p").replace('\u202f', ' ')

  #winners
  winner_section = soup.find('div', class_='v5-section-content tournaments-live-view-players')
  winners_items = winner_section.find_all('div', class_='tournaments-winners-item')
  winners_data = winner_section.find_all('div',class_='post-view-meta-component tournaments-winners-details')
  first_place_winners = []
  for idx,item in enumerate(winners_items):
    place = item.find('div', class_='tournaments-winners-box').get_text(strip=True)
    if place == '1st Place':
        winner = winners_data[idx].find('a', class_='user-username-component').get_text(strip=True)
        first_place_winners.append(winner)
  #assume something wrong with the event
  if len(first_place_winners) > 10:
    first_place_winners = []

  event = {
    "title": name,
    "num_players": number_of_players,
    "date": formatted_date,
    "time": formatted_time,
    "tourney_link": base_url+i,
    "data": f"https://github.com/cmgchess/Titled-Tuesday-Data/blob/main/ranks/{i}.json",
    "winner": first_place_winners
  }
  events.append(event)

events.sort(key=lambda x: (datetime.strptime(x["date"], "%d.%m.%Y"), x["time"]), reverse=True)

grouped_data = {}
for year, items in groupby(events, key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y").year):
    grouped_data[year] = list(items)

custom_headers = {
    "title": "Title",
    "num_players": "Number of Players",
    "date": "Date",
    "time": "Time",
    "winner": "Winner",
    "tourney_link": "Tournament Link",
    "data": "Rank List"
}
headers = ['Title', 'Number of Players', 'Date', 'Time', 'Winner', 'Tournament Link', 'Rank List']

entries = grouped_data[current_year]
file_name = f"{current_year}.md"
entries_with_custom_names = [{custom_headers.get(col, col): value for col, value in entry.items()} for entry in entries]
for entry in entries_with_custom_names:
  if 'Title' in entry:
    entry['Title'] = entry['Title'].replace("|", "\|")
  if 'Tournament Link' in entry:
    entry['Tournament Link'] = f"[Link]({entry['Tournament Link']})"
  if 'Winner' in entry:
    if len(entry['Winner']) == 0:
      entry['Winner'] = 'Cancelled'
    else:
      entry['Winner'] = ", ".join(entry['Winner'])
  if 'Rank List' in entry:
    entry['Rank List'] = f"[Link]({entry['Rank List']})"
entries_with_custom_names = [OrderedDict((key, item[key]) for key in headers) for item in entries_with_custom_names]
table = tabulate(entries_with_custom_names,headers="keys", tablefmt="github")
with open("details/"+file_name, "w") as file:
    file.write(table)
