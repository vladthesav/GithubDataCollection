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

#because I don't feel like staring at a bunch of try/catch statements
#this is to play nice with Github's rate limit
def do_thing(thing):
    try:
        thing
    except Exception as e:
        print(e)
        time.sleep(100)
        thing
    time.sleep(60)
        
def format_date(date):
    #print(date)
    a = date[:int(date.index('T'))]
    b = date[int(date.index('T'))+1:int(date.index('Z'))]
    return a +' '+b

def get_date(link, auth):
    headers = {'Authorization': 'token %s' % auth}
    resp = requests.get(link,headers=headers)
    if resp.status_code != 200:
        # This means something went wrong.
        print(resp, '\n ok lets pause for a while')
        time.sleep(100)
        resp = requests.get(link)
    out = format_date(resp.json()['commit']['author']['date'])
    #print(out)    
    return out
    
class GitScraper:

    
    def __init__(self, auth, repo_range, event_range):
        self.auth = auth
        self.g = Github(auth)
        self.repo_range = repo_range
        self.event_range=event_range
        self.data_raw = {}

        
    #gets repos that come up in query
    def get_repos(self, query, time_period):
        repos = self.g.search_repositories(query=query)
        stack = list(repos)
        #print(len(stack), " repos found")

        #this is where we hold our data
        data_raw = {}
        while stack:
            repo = stack.pop()
            try:
                if time_in_range(str(repo.created_at),time_period):
                    data_raw[repo.full_name] = {'time-created':str(repo.created_at)}
                    data_raw[repo.full_name]['object'] = repo
                    data_raw[repo.full_name]['url'] = repo.url
                    data_raw[repo.full_name]['events']=[]
                    data_raw[repo.full_name]['id']=repo.id
                    data_raw[repo.full_name]['description']=repo.description
            except Exception as e:
                print(e)
                time.sleep(100)
        return data_raw
    
    def get_repo_data(self, query):
        repo = self.g.get_repo(query)
        #print(repo)
        data_raw = {}
        if time_in_range(str(repo.created_at),self.repo_range):
            data_raw[repo.full_name] = {'time-created':str(repo.created_at)}
            data_raw[repo.full_name]['object'] = repo
            data_raw[repo.full_name]['events']=[]
            data_raw[repo.full_name]['id']=repo.id
            data_raw[repo.full_name]['description']=repo.description
        #print(data_raw)
        return data_raw
    
    def get_forks(self, data_raw, repo):
        forks = list(data_raw[repo]['object'].get_forks())
        n=0
        while forks:
            f=forks.pop()
            if time_in_range(str(f.created_at),self.event_range):
                event = {}
                event['event-type']='ForkEvent'
                event['name']=f.full_name
                event['time-created']=str(f.created_at)
                event['id']=f.id
                event['node-id']=f.node_id
                data_raw[repo]['events'].append(event)
                n+=1
            #print('\t',f.full_name, f.created_at, f.id)
            
        print("\tForks in Time Range: ",n)
        
    def get_commits(self, data_raw, repo):

        #commits
        try:
            commits = list(data_raw[repo]['object'].get_commits())
        except Exception as e:
            print(str(e)+'rgwregwrgwgr')
            commits=[]
            
        #print('\t',len(commits), " commits")
        push = 0
        push_comment = 0
        while commits:
            f=commits.pop()
            time_created = get_date(f.url, self.auth)
            #print(time_created)
            if time_in_range(time_created, self.event_range):
        
                event = {}
                event['event-type']='PushEvent'
                event['author']=str(f.author)
                event['comments']=[]
                event['url']=f.url
                event['time']=time_created
                #event['node-id']=f.node_id
                data_raw[repo]['events'].append(event)
                
                push+=1
                #now to get comments
                comments = list(f.get_comments())
                while comments:
                    c=comments.pop()
                    if time_in_range(str(c.created_at), self.event_range):
                        comment = {'id':c.id,'time':str(c.created_at), 'login':c.user.login, 'comment':c.body}
                        data_raw[repo]['events'][-1]['comments'].append(comment)
                        push_comment +=1
                        
        print("\tPushEvents in Range: ",push)
        print("\tPushEventComments in Range: ",push_comment)
        
    def get_watch(self, data_raw, repo):
        watch_num = 0
        watch = list(data_raw[repo]['object'].get_watchers())
        #print(len(watch), " watchers")
        while watch:
            f=watch.pop()
            if time_in_range(str(f.created_at), self.event_range):
                #print(f.login, f.created_at)
                event = {'event-type':'WatchEvent','login':f.login, 'time':str(f.created_at),'id':f.id}
                data_raw[repo]['events'].append(event)
                watch_num +=1
        print("\tWatch Events in Range : ",watch_num)

    def get_issues(self, data_raw, repo):
        num_issues = 0
        issue_comments = 0
            
        issues = list(data_raw[repo]['object'].get_issues())
        while issues:
            f=issues.pop()
            if time_in_range(str(f.created_at), self.event_range):
                num_issues+=1
                #print('\tissue: ',f.login, f.created_at, f.id)
                event = {'event-type':'IssueEvent','login':f.user.login, 'time':str(f.created_at),'id':f.id,'issue-comments':[]}
                data_raw[repo]['events'].append(event)
      
                #comments related to issue f
                comments = list(f.get_comments())
                while comments:
                    c=comments.pop()
                    if time_in_range(str(c.created_at), self.event_range):
                        issue_comments+=1
                        comment  ={'login':c.user.login, 'id':c.id, 'comment':c.body}
                        data_raw[repo]['events'][-1]['issue-comments'].append(comment)
   
        print("\tIssues in Range: ",num_issues)
        print("\tIssues Comments in Range: ",issue_comments)

    def get_pulls(self, data_raw,repo):
            
        num_pull_reqs = 0
        num_comments=0
        pull_requests = list(data_raw[repo]['object'].get_pulls())
        while pull_requests:
            f=pull_requests.pop()
            if time_in_range(str(f.created_at), self.event_range):
                num_pull_reqs+=1
                #print('\tpull: ',f.login, f.created_at, f.id)
                pull={'event-type':'PullRequestEvent','login':f.user.login, 'time':str(f.created_at),'id':f.id,'pull-request-comments':[]}
                data_raw[repo]['events'].append(pull)
      
                #comments related to pull request
                comments = list(f.get_review_comments())
                while comments:
                  c=comments.pop()
                  if time_in_range(str(c.created_at), self.event_range):
                    num_comments+=1
                    comment= {'login':c.user.login, 'id':c.id, 'comment':c.body}
                    data_raw[repo]['events'][-1]['pull-request-comments'].append(comment)
        print("\tPull Requests in Range: ", num_pull_reqs)
        print("\tPull Request Comments in Range: ", num_comments)



    def get_create_and_delete(self, data_raw, repo):
        stack = list(data_raw[repo]['object'].get_events())
        create=0
        delete=0
        while stack:
            e=stack.pop()
            if time_in_range(str(e.created_at),self.event_range):
                if e.type =='CreateEvent' or e.type=='DeleteEvent':
                    event ={'event-type':e.type, 'login':e.user.login, 'time':str(e.created_at), 'id':e.id,'description':e.description}
                    data_raw[repo]['events'].append(event)
                    if e.type=='CreateEvent':
                        create+=1
                    else:
                        delete+=1
        print("\tCreate Events in Range: ", create)
        print("\tDelete Events in Range", delete)
    
    def get_data_for_repo(self, repo):
        #data_raw = get_repo(repo)
        data_raw = self.get_repo_data(repo)
        #print(data_raw)
        print("Events for ", repo)
        print("\tTime Range for Repos: ",self.repo_range)
        print("\tTime Range for Events: ",self.event_range)
        if not bool(data_raw):
            return None
        do_thing(self.get_forks(data_raw, repo))
        do_thing(self.get_commits(data_raw, repo))
        do_thing(self.get_watch(data_raw, repo))
        do_thing(self.get_issues(data_raw, repo))
        do_thing(self.get_pulls(data_raw, repo))
        do_thing(self.get_create_and_delete(data_raw, repo))
        return data_raw
        #self.data_raw = data_raw

    
    def get_data_for_repos(self, repos):
        data = {}
        while repos:
            repo = repos.pop()
            data_raw = self.get_repo_data(repo)
            #print(data_raw)
            do_thing(self.get_data_for_repo(repo))
            if bool(data_raw):
                data[repo] = data_raw[repo]
        return data

    def clean_data(self, data_raw):
        for repo in data_raw.keys():
            del data_raw[repo]['object']
