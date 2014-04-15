#import tweepy
import urllib2
import webbrowser
import pickle


# auth = tweepy.OAuthHandler("EO9AktQBJXsxbYIV1tIt2Ss1K", "2Zjoqkbj6mQGlHGuIsydn3NFthUnubMiBxTwM26ZG4pTdBtIil")


# try:
#     redirect_url = auth.get_authorization_url()
# except tweepy.TweepError:
#     print 'Error! Failed to get request token.'

# webbrowser.open(redirect_url)

# verifier = raw_input('Verifier Code:')

# try:
#     auth.get_access_token(verifier)
# except tweepy.TweepError:
#     print 'Error! Failed to get access token.'

# api = tweepy.API(auth)

class Category:
	def __init__(self, name, key):
		self.name = name
		self.key = key
		self.score = 0
		self.retweets = 0

	def incrementRetweets(self):
		self.retweets = self.retweets + 1

def save_object(obj, filename):
    with open(filename, 'wb') as output:
        pickle.dump(obj, output, pickle.HIGHEST_PROTOCOL)


with open('temp.pkl', 'rb') as input:
	temp = pickle.load(input)
	print temp.name
	print temp.retweets

# temp = Category("temp", "t")
# temp.incrementRetweets()
# temp.incrementRetweets()
save_object(temp, r'temp.pkl')
print(temp.retweets)
