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
		self.individualScore = 0
		self.retweetsTotal = 0
		self.retweetsList = []

	def incrementRetweets(self, num):
		print("Adding " + str(num) + " retweets to category " + self.name)
		self.retweetsTotal = self.retweetsTotal + num
		self.retweetsList.append(num)

	def calculateScore(self):
		if len(self.retweetsList) > 3:
			bonusTweetCount = len(self.retweetsList) / 4
		else:
			bonusTweetCount = 1
		bonus = 3
		temp = 0
		for score in reversed(self.retweetsList):
			temp += score*bonus
			bonus -= (bonus - 1)/bonusTweetCount
		self.individualScore = temp


class Categories:
	def __init__(self):
		self.container = []
		self.total = 0

	def addCategory(self, c):
		self.container.append(c)

	def getCategory(self, key):
		for category in self.container:
			if(category.key == key):
				return category
		return None

def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


def loadData():
#load previous data if available, else create a new data file
	global categories
	try:
		with open('data.pkl', 'rb') as input:
			print "Loading previous data..."
			categories = pickle.load(input)
	except:
		print("Creating new data...")
		categories = Categories()
		f = open('categories.txt', 'r')
		lines = open('categories.txt').read().splitlines()
		for line in lines:
			categories.addCategory(Category(line, line[0]))
		save_object(categories, r'data.pkl')

	global cache	
	try:
		with open('cache.pkl', 'rb') as input:
			print("Cache found, loading...")
			cache = pickle.load(input)
	except:
		print("Creating new cache...")
		cache = []
		save_object(cache, r'cache.pkl')


twitterAuth()
loadData()

print("Incremeting category retweets...")
tweets = api.user_timeline()
for tweet in tweets:
	if tweet.id not in cache:
	    categoryTag = tweet.text[0]
	    currentCategory = categories.getCategory(categoryTag)
	    if currentCategory != None:
	    	currentCategory.incrementRetweets(tweet.retweet_count)
	    	categories.total += tweet.retweet_count
	    	currentCategory.calculateScore()
	    else:
	    	print("Invalid category, skipping tweet")
	    cache.append(tweet.id)

for category in categories.container:
	print(category.name + " Score: " + str(category.individualScore))


save_object(cache, r'cache.pkl')
save_object(categories, r'data.pkl')
