import tweepy
import urllib2
import webbrowser
import pickle

def twitterAuth():
	auth = tweepy.OAuthHandler("i2LqyscLlAnNvqhRCjihg", "CmhqszB3h29c0r2ERZM7gDGozDnMKo2tLOUiQaEIok")

	try:
	    redirect_url = auth.get_authorization_url()    
	except tweepy.TweepError:
	    print 'Error! Failed to get request token.'

	webbrowser.open(redirect_url)

	verifier = raw_input('Verifier Code:')

	try:
	    auth.get_access_token(verifier)
	except tweepy.TweepError:
	    print 'Error! Failed to get access token.'
	global api
	api = tweepy.API(auth)

class Category:
	def __init__(self, name, key):
		self.name = name
		self.key = key
		self.score = 0
		self.retweets = 0

	def incrementRetweets(self, num):
		print("Adding " + str(num) + " retweets to category " + self.name)
		self.retweets = self.retweets + num

class Categories:
	def __init__(self):
		self.container = []

	def addCategory(self, c):
		self.container.append(c)

	def listOfKeys(self):
		result = []
		for category in self.container:
			result.append(category.key)
		return result

	def getCategory(self, key):
		for category in self.container:
			if(category.key == key):
				return category

def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)

twitterAuth()

#load previous data if available, else create a new data file
try:
	with open('data.pkl', 'rb') as input:
		print "Loading previous file..."
		categories = pickle.load(input)
except:
	print("Creating new file...")
	categories = Categories()
	f = open('categories.txt', 'r')
	lines = open('categories.txt').read().splitlines()
	for line in lines:
		c = Category(line, line[0])
		categories.addCategory(c)
	save_object(categories, r'data.pkl')

try:
	with open('cache.pkl', 'rb') as input:
		print("Cache found, loading...")
		cache = pickle.load(input)
except:
	print("Creating new cache...")
	cache = []
	save_object(cache, r'cache.pkl')


tweets = api.user_timeline()
for tweet in tweets:
	if tweet.id not in cache:
	    categoryTag = tweet.text[0]
	    if categoryTag not in categories.listOfKeys():
	    	print("Invalid category, skipping tweet")
	    else:
	    	categories.getCategory(categoryTag).incrementRetweets(tweet.retweet_count)
	    cache.append(tweet.id)
save_object(cache, r'cache.pkl')
save_object(categories, r'data.pkl')
