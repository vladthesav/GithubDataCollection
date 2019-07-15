from github import Github
from dateutil.parser import parse
import datetime
import requests
import urllib.request, json 
import time

#range should be an array of the form [lower_bound, upper_bound]
def time_in_range(time, time_range):
    #case: no range given - whatever let it through
    if time_range == None:
        return True
    #case: range given
    lower = datetime.datetime.strptime(time_range[0], "%Y-%m-%d %H:%M:%S")
    t = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
    upper = datetime.datetime.strptime(time_range[1], "%Y-%m-%d %H:%M:%S")
    if lower <= t:
        if t <= upper:
            return True
    return False

class GitScraper:
    def __init__(self, auth):
        self.auth = auth
        self.g = Github(auth)
        self.data_raw = {}
    #gets repos that come up in query
    def get_repos(self, query, time_period=None):
        repos = self.g.search_repositories(query=query)
        stack = list(repos)
        print(len(stack), " repos found")

        #this is where we hold our data
        data_raw = {}
        while stack:
            repo = stack.pop()
            try:
                if time_in_range(str(repo.created_at),time_period):
                    data_raw[repo.full_name] = {'time-created':str(repo.created_at)}
                    data_raw[repo.full_name]['object'] = repo
                    data_raw[repo.full_name]['events']=[]
                    data_raw[repo.full_name]['id']=repo.id
                    data_raw[repo.full_name]['description']=repo.description
            except Exception as e:
                print(e)
                time.sleep(100)
        return data_raw
    def get_repo(self, query, time_period=None):
        repo = self.g.get_repo(query)
        data_raw = {}
        if time_in_range(str(repo.created_at),time_period):
            data_raw[repo.full_name] = {'time-created':str(repo.created_at)}
            data_raw[repo.full_name]['object'] = repo
            data_raw[repo.full_name]['events']=[]
            data_raw[repo.full_name]['id']=repo.id
            data_raw[repo.full_name]['description']=repo.description
        return data_raw
    
    def get_forks(self, data_raw, repo):
        
        forks = list(self.data_raw[repo]['object'].get_forks())
        print('\t',repo, ':  ',len(forks), " forks")
        while forks:
            f=forks.pop()
            if time_in_range(str(repo.created_at),time_period):
                data_raw[repo]['events'].append({'event-type':'ForkEvent','name':f.full_name, 'time-created':str(f.created_at),'id':f.id})
            #print('\t',f.full_name, f.created_at, f.id)
            
    def format_date(date):
        a = date[:int(date.index('T'))]
        b = date[int(date.index('T'))+1:int(date.index('Z'))]
        return a +' '+b

    def get_date(self, link):
        headers = {'Authorization': 'token %s' % self.auth}
        resp = requests.get(link,headers=headers)
        if resp.status_code != 200:
            # This means something went wrong.
            print(resp, '\n ok lets pause for a while')
            time.sleep(100)
            resp = requests.get(link)
        out = format_date(resp.json()['commit']['author']['date'])
        #print(out)
        return out

    def get_commits(self, data_raw, repo):

        #commits
        try:
            commits = list(data_raw[repo]['object'].get_commits())
        except Exception as e:
            print(str(e)+'rgwregwrgwgr')
            commits=[]
        print('\t',len(commits), " commits")
        while commits:
            f=commits.pop()
            time_created = get_date(f.url)
            if time_in_range(event_l, time_created, event_h):
                data_raw[repo]['events'].append({'event-type':'PushEvent','author':str(f.author), 'comments':[], 'url':f.url, 'time':time_created})
    
                #now to get comments
                comments = list(f.get_comments())
                while comments:
                    c=comments.pop()
                    if time_in_range(event_l, str(c.created_at), event_h):
                        data_raw[repo]['events'][-1]['comments'].append({'id':c.id,'time':str(c.created_at), 'login':c.user.login, 'comment':c.body})

    


scrappy = GitScraper("f7599bf79f708c5add325d4894184ebdae471f21")
data_raw = scrappy.get_repo("giantpune/android-vts")
#data = scrappy.get_repos("android-vts")
