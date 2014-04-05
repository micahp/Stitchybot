import tweepy
import urllib2
import webbrowser


auth = tweepy.OAuthHandler("EO9AktQBJXsxbYIV1tIt2Ss1K", "2Zjoqkbj6mQGlHGuIsydn3NFthUnubMiBxTwM26ZG4pTdBtIil")


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

api = tweepy.API(auth)

statuses = api.home_timeline()
for status in statuses:
	print (status.text)
