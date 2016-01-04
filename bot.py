import praw
import time
from requests.exceptions import HTTPError

# Number of seconds to sleep between each check
SLEEP_TIME = 60

class NotifierBot:
  def __init__(self, user_name, password, complaints_uname):
    self.user_name = user_name
    self.complaints_uname = complaints_uname
    self.password = password

    self.reddit = praw.Reddit(user_agent="lolfanart notifier bot")
    self.reddit.login(self.user_name, self.password)

    self.subr = self.reddit.get_subreddit('lolfanart')
    self.subscriptions = {}

    # this is purely for optimization
    self.users = []

    # need to keep track of posts so we don't double notify
    self.notified = []
   
    self.log_file = open('log_file.txt', 'a')    

  def notify_user(self, user, post):
    message_text = '''
Hi %s,

A new post matches your notification queries! Check it out [here](%s).
\n_____\n
|[Private Message](http://www.reddit.com/message/compose/?to=%s&subject=Notify Me)|[Source](http://github.com/shikib/reddit-notifier-bot)|[Feedback](http://www.reddit.com/message/compose/?to=%s&subject=Feedback)
    ''' % (user.name, post.permalink, self.user_name, self.complaints_uname)

    user.send_message(self.reddit, message=message_text)

  # get list of users we need to notify
  def get_users_to_notify(self, title):
    user_pos_list = []
    for subscription, users in self.subscriptions.items():
      if subscription in title.lower():
        user_pos_list += users       

    users = [ self.users[pos] for pos in list(set(user_pos_list)) ]
    return users

  def process_new_post(self, post):
    users = self.get_users_to_notify(post.title)
    for user in users:
      if user != post.author:
        self.notify_user(user, post)
    
  # check new posts and send out alerts accordingly
  def process_new_posts(self):
    for post in self.subr.get_new():
      if post.id not in self.notified:
        self.process_new_post(post)
        self.notified.append(post)

  # get the appropriate pos (used as id here) for a user
  def get_user_pos(self, user):
    if user not in self.users:
      self.users.append(user)
      user_pos = len(self.users) - 1
    else:
      user_pos = self.users.index(user)
    
    return user_pos

  # given the text and the user, subscribe the user to posts that have the text in them
  def add_subscription(self, text, user):
    if not text:
      return    
 
    user_pos = self.get_user_pos(user)

    if text in self.subscriptions and user_pos not in self.subscriptions[text]:
      self.subscriptions[text].append(user_pos)
    else:
      self.subscriptions[text] = [user_pos]

  # given the text and the user, unsubscribe the user to posts that have the text in them
  def remove_subscription(self, text, user):
    if not text:
      return    
 
    user_pos = self.get_user_pos(user)

    if text in self.subscriptions and user_pos in self.subscriptions[text]:
      self.subscriptions[text].remove(user_pos)

  # given relevant line in message, log it just in case of program failure
  def log_line(self, author, line):
     self.log_file.write("%s: %s\n" % (author.name, line)) 
     print("%s: %s" % (author.name, line)) 

  # given author and body of comment, subscribe author to everything they asked for
  def process_subscriptions(self, author, body):
    for line in body.split("\n"):
      if line[:9] == "!notifyme":
        for text in line[9:].split(","):
          self.log_line(author, text.strip())
          self.add_subscription(text.strip(), author)
 
  # given author and body of comment, unsubscribe author to everything they ask for
  def process_unsubscriptions(self, author, body):
    for line in body.split("\n"):
      if line[:9] == "!unnotifyme":
        for text in line[:9].split(","):
          self.log_line(author, text)
          self.remove_subscription(text.strip(), author)
                 

  # check comments for new subscriptions
  def process_new_comments(self):
    for c in self.subr.get_comments():
      if '!notifyme' in c.body.lower():
        self.process_subscriptions(c.author, c.body.lower())
      if '!unnotifyme' in c.body.lower():
        self.process_unsubscriptions(c.author, c.body.lower())

  # check comments for new subscriptions
  def process_new_messages(self):
    for m in self.reddit.get_unread():
      if '!notifyme' in m.body.lower():
        self.process_subscriptions(m.author, m.body.lower()) 
      if '!unnotifyme' in m.body.lower():
        self.process_unsubscriptions(m.author, m.body.lower())
      m.mark_as_read()

  # clear notified list
  def clear_notified_list(self):
    if len(self.notified) >= 50:
      self.notified = self.notified[-50:]

  def parse_automod(self, file_name):
    f = open(file_name, 'r')
    alltext = f.read()
    sections = alltext.split("---")  
    for section in sections:
      text = section.split('"')[1].lower()
      users = []
      for word in section.split():
        if word[:3] == "/u/":
          self.add_subscription(text, self.reddit.get_redditor(word[3:]))
          self.log_line(self.reddit.get_redditor(word[3:]), "!notifyme %s" % text)
    print("DONE")

  def parse_log_file(self):
    alltext = self.log_file.readlines()
    for line in alltext:
      username, text = line.split(":")
      if "!notifyme" in text.lower():
        notify_text = text[text.index("!notifyme") + len("!notifyme"):]
        self.add_subscription(notify_text, self.reddit.get_redditor(username))
        print(line)
          
     
# First arg: bot user name
# Second arg: bot password
# Third arg: user name for complaints account 
nb = NotifierBot('', '', '') 

nb.parse_logfile()
nb.parse_automod('automod.txt')

while True:
  try:
    nb.process_new_comments()
    nb.process_new_messages()
    #nb.process_new_posts()
    nb.clear_notified_list()
  except HTTPError:
    continue
  time.sleep(SLEEP_TIME)
  
