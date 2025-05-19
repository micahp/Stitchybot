import tweepy
# import urllib2 # No longer used
import webbrowser
import pickle
import os
import json
from dotenv import load_dotenv # Added for .env file support
import sys # For exiting the script

from ai_content_generator import AIContentGenerator # Import the new class
# Load environment variables from .env file
load_dotenv()

# Attempt to load Together.ai API key (optional at this stage)
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
# The user-facing warning/success about TOGETHER_API_KEY loading will be handled
# during AIContentGenerator instantiation or when the user tries to use the feature.


# Access token file (remains pickle for now, could be refactored later if needed)
ACCESS_TOKEN_FILE = "twitter_auth.pkl" 

class TwitterClient:
    def __init__(self):
        self.api = None
        self.consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
        self.consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")

        if not self.consumer_key or not self.consumer_secret:
            print("Error: TWITTER_CONSUMER_KEY or TWITTER_CONSUMER_SECRET not found in environment variables.")
            print("Please create a .env file in the root directory with the following content:")
            print("\nTWITTER_CONSUMER_KEY=\"YOUR_API_KEY_HERE\"\nTWITTER_CONSUMER_SECRET=\"YOUR_API_SECRET_HERE\"\n")
            # Indicate failure to initialize
            # One way is to set a flag or ensure self.api remains None and check it before use.
            # For a more direct approach, __init__ cannot return a value to stop instantiation,
            # so the check must be done before instantiation or by the caller.
            # Let's make _authenticate return False on failure and check that.
            self.initialization_failed = True 
            return
        
        self.initialization_failed = False
        self._authenticate()


    def _save_tokens(self, access_token, access_token_secret):
        # This uses pickle, which is fine for access tokens as they are not directly in .env
        try:
            with open(ACCESS_TOKEN_FILE, 'wb') as f:
                pickle.dump({'token': access_token, 'secret': access_token_secret}, f, pickle.HIGHEST_PROTOCOL)
            print("Access tokens saved.")
        except Exception as e:
            print(f"Error saving access tokens: {e}")

    def _load_tokens(self):
        if os.path.exists(ACCESS_TOKEN_FILE):
            try:
                with open(ACCESS_TOKEN_FILE, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading access tokens: {e}")
                return None
        return None

    def _authenticate(self):
        # consumer_key and consumer_secret are now instance variables
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        loaded_tokens = self._load_tokens()

        if loaded_tokens:
            auth.set_access_token(loaded_tokens['token'], loaded_tokens['secret'])
            self.api = tweepy.API(auth)
            print("Successfully authenticated using saved tokens.")
            # Verify if tokens are still valid
            try:
                self.api.verify_credentials()
                print("Credentials verified.")
            except tweepy.TweepError as e:
                print("Saved tokens are invalid or expired: {}".format(e))
                self.api = None # Reset api
                # Proceed to browser authentication
        
        if not self.api: # If API not set up either due to no tokens or invalid tokens
            print("Attempting browser authentication...")
            try:
                redirect_url = auth.get_authorization_url()
            except tweepy.TweepError:
                print('Error! Failed to get request token.')
                return

            webbrowser.open(redirect_url)
            verifier = input('Verifier Code: ') # Changed to input for Python 3 compatibility

            try:
                auth.get_access_token(verifier)
                self._save_tokens(auth.access_token, auth.access_token_secret)
                self.api = tweepy.API(auth)
                print("Successfully authenticated via browser and tokens saved.")
            except tweepy.TweepError:
                print('Error! Failed to get access token.')
                return
        
        if not self.api:
            print("Authentication failed.")


    def user_timeline(self, **kwargs):
        if self.api:
            return self.api.user_timeline(**kwargs)
        else:
            print("API not initialized. Cannot fetch timeline.")
            return []


class Category:
	def __init__(self, name, key):
		self.name = name
		self.key = key
		self.individualScore = 0
		self.retweetsTotal = 0
		self.retweetsList = [] # Stores the retweet counts for individual tweets in this category

	def to_dict(self):
		return {
			'name': self.name,
			'key': self.key,
			'individualScore': self.individualScore,
			'retweetsTotal': self.retweetsTotal,
			'retweetsList': self.retweetsList,
		}

	@classmethod
	def from_dict(cls, data_dict):
		category = cls(data_dict['name'], data_dict['key'])
		category.individualScore = data_dict.get('individualScore', 0)
		category.retweetsTotal = data_dict.get('retweetsTotal', 0)
		category.retweetsList = data_dict.get('retweetsList', [])
		return category

	def incrementRetweets(self, num):
		print(f"Adding {num} retweets to category {self.name}")
		self.retweetsTotal += num # Use += for conciseness
		self.retweetsList.append(num)

	def calculateScore(self):
		"""
		Calculates a weighted score for the category based on its retweet counts.
		The scoring gives higher weight to more recent tweets.
		A bonus system is applied based on the number of tweets.
		"""
		num_tweets = len(self.retweetsList)
		
		# Determine the number of tweets that will get a bonus weighting
		# If more than 3 tweets, the top 1/4th (integer division) get bonus, otherwise only 1 tweet gets bonus.
		if num_tweets > 3:
			# Example: 4 tweets -> 1 bonus tweet, 7 tweets -> 1 bonus tweet, 8 tweets -> 2 bonus tweets
			bonus_tweet_count = num_tweets // 4 
		else:
			bonus_tweet_count = 1
		
		initial_bonus_value = 3  # Starting bonus multiplier for the most recent tweet(s)
		current_bonus = float(initial_bonus_value) # Use float for bonus calculation precision
		
		weighted_score_sum = 0
		
		# Iterate through retweets in reverse (most recent first)
		for i, score in enumerate(reversed(self.retweetsList)):
			weighted_score_sum += score * current_bonus
			# Decrease the bonus for subsequent tweets.
			# The rate of decrease is faster if there are fewer "bonus_tweet_count".
			if bonus_tweet_count > 0 : # Avoid division by zero if list was empty (though bonus_tweet_count would be 1)
				# Decrease ensures that bonus is spread out over bonus_tweet_count tweets
				# If bonus_tweet_count is 1, bonus becomes 1 after the first tweet.
				# (current_bonus - 1) is the amount of bonus to distribute/reduce.
				# (current_bonus - 1) / bonus_tweet_count is the reduction step.
				reduction_step = (current_bonus - 1.0) / bonus_tweet_count if i < bonus_tweet_count else (current_bonus -1.0)
				current_bonus -= reduction_step
				if current_bonus < 1.0: # Ensure bonus does not go below 1
					current_bonus = 1.0
			else: # Should not happen if retweetsList is not empty due to bonus_tweet_count logic
				current_bonus = 1.0

		self.individualScore = weighted_score_sum


class Categories:
	def __init__(self):
		self.container = [] # List of Category objects
		self.total = 0      # Total retweets across all categories (seems to be the intent)

	def addCategory(self, c):
		self.container.append(c)

	def getCategory(self, key):
		for category_obj in self.container: # Renamed for clarity
			if category_obj.key == key:
				return category_obj
		return None

	def to_dict(self):
		return {
			'categories': [category.to_dict() for category in self.container],
			'total': self.total, # Preserving 'total' attribute
		}

	@classmethod
	def from_dict(cls, data_dict):
		categories_obj = cls()
		categories_obj.total = data_dict.get('total', 0)
		category_list_data = data_dict.get('categories', [])
		for category_data in category_list_data:
			categories_obj.addCategory(Category.from_dict(category_data))
		return categories_obj

# Removing duplicated save_object and the phantom loadData that was actually a comment
# Utility function to save objects using JSON
def save_json_object(obj, filename):
    """Saves an object to a file using JSON."""
    data_to_save = obj
    if hasattr(obj, 'to_dict'):
        data_to_save = obj.to_dict()
    
    try:
        with open(filename, 'w') as output_file: # Changed to 'w' for text mode
            json.dump(data_to_save, output_file, indent=4)
        print(f"Object successfully saved to {filename}")
    except IOError as e:
        print(f"Error saving object to {filename}: {e}")
    except TypeError as e: # Catches issues if parts of obj are not JSON serializable
        print(f"Error serializing object to JSON for {filename}: {e}")

# Utility function to load objects using JSON
def load_json_object(filename, target_class=None):
    """
    Loads an object from a JSON file.
    If target_class is provided and has a from_dict method, it's used.
    """
    if not os.path.exists(filename):
        print(f"File {filename} not found.")
        return None
    try:
        with open(filename, 'r') as input_file: # Changed to 'r' for text mode
            data_loaded = json.load(input_file)
            if target_class and hasattr(target_class, 'from_dict'):
                return target_class.from_dict(data_loaded)
            return data_loaded # Return raw loaded data if no target_class or from_dict
    except IOError as e:
        print(f"Error loading object from {filename}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {filename}: {e}")
        return None
    except EOFError as e: # Should be less common with JSON text files but good practice
        print(f"EOFError loading object from {filename} (file might be empty or corrupt): {e}")
        return None


class StitchyBot:
    DATA_FILE = "data.json" # Class constant for data file name
    CACHE_FILE = "cache.json" # Class constant for cache file name

    def __init__(self, twitter_client):
        self.twitter_client = twitter_client
        self.categories = Categories() 
        self.cache = [] 
        self._load_data_and_cache()

    def _load_data_and_cache(self):
        """Loads categories data and tweet ID cache from JSON files."""
        loaded_categories = load_json_object(self.DATA_FILE, target_class=Categories)
        if loaded_categories:
            print("Loading previous categories data from JSON...")
            self.categories = loaded_categories
        else:
            print(f"Categories data file ({self.DATA_FILE}) not found or error loading, creating new data...")
            self._initialize_categories_from_file('categories.txt')
            # Save immediately after initializing if data file was missing/corrupt
            save_json_object(self.categories, self.DATA_FILE)


        loaded_cache = load_json_object(self.CACHE_FILE)
        if loaded_cache is not None: 
            print("Cache found, loading from JSON...")
            self.cache = loaded_cache # Cache is a list, loaded directly
        else:
            print(f"Cache file ({self.CACHE_FILE}) not found or error loading, creating new cache...")
            # self.cache is already initialized as [], so just need to save it
            save_json_object(self.cache, self.CACHE_FILE)
            
    def _initialize_categories_from_file(self, filename):
        """Initializes categories from a text file (categories.txt)."""
        # This method now populates the existing self.categories object
        # It's called when DATA_FILE is missing/corrupt, so self.categories is a fresh Categories instance
        try:
            with open(filename, 'r') as f:
                lines = f.read().splitlines()
                if not lines:
                    print(f"Warning: {filename} is empty. No categories loaded.")
                    return

                for line in lines:
                    if line:  # Ensure line is not empty
                        self.categories.addCategory(Category(name=line, key=line[0]))
                print(f"Initialized categories from {filename}")
        except FileNotFoundError:
            print(f"Error: Initialization file {filename} not found. Cannot initialize categories.")
        except IOError as e:
            print(f"Error reading {filename} during initialization: {e}")


    def _save_data_and_cache(self):
        """Saves categories data and tweet ID cache to JSON files."""
        print("Saving cache and categories data to JSON...")
        save_json_object(self.cache, self.CACHE_FILE)
        save_json_object(self.categories, self.DATA_FILE)

    def process_timeline_tweets(self):
        """Fetches tweets from the timeline, processes them, and updates scores."""
        if not self.twitter_client.api:
            print("Twitter API not initialized. Cannot process timeline.")
            return

        print("Incrementing category retweets...")
        tweets = self.twitter_client.user_timeline() 

        if not tweets:
            print("No tweets fetched or timeline is empty.")
            return

        processed_tweets_count = 0
        for tweet in tweets:
            if tweet.id not in self.cache:
                if tweet.text and len(tweet.text) > 0:
                    category_tag = tweet.text[0]
                    current_category = self.categories.getCategory(category_tag)
                    
                    if current_category:
                        current_category.incrementRetweets(tweet.retweet_count)
                        self.categories.total += tweet.retweet_count # Assuming this total is still desired
                        current_category.calculateScore()
                        processed_tweets_count +=1
                    else:
                        print(f"Invalid category tag '{category_tag}' for tweet: \"{tweet.text[:50]}...\", skipping.")
                else:
                    print(f"Tweet ID {tweet.id} has no text or is empty, skipping.")
                self.cache.append(tweet.id)
        
        if processed_tweets_count > 0:
             print(f"Processed {processed_tweets_count} new tweets.")
        else:
            print("No new tweets to process.")
        
        # Note: Score printing and saving data are now handled separately after this method returns.

    def print_scores(self):
        """Prints the calculated scores for each category."""
        print("\n--- Category Scores ---")
        if not self.categories.container:
            print("No categories to display scores for.")
            return
            
        for category in self.categories.container:
            score_to_print = category.individualScore if isinstance(category.individualScore, (int, float)) else 0.0
            print(f"{category.name} Score: {score_to_print:.2f}")
        print("-----------------------\n")

    # _save_data_and_cache is already defined and seems fine.
    # It's called by process_timeline_tweets at the end or can be called separately.
    # For the new menu structure, it's better to call it explicitly in the menu option flow.
    # So, let's remove the automatic call from process_timeline_tweets.

# Modify process_timeline_tweets to not call _save_data_and_cache directly.
# This change is done by simply removing the line from the end of that method.
# Let's apply this change with the previous one.
# No, I need to do it in a separate block.
# The previous block was about StitchyBot. I'll do another one for it.

# Main script execution
if __name__ == "__main__":
    # Initialize Twitter client
    twitter_client = TwitterClient()
    
    # Check if TwitterClient initialization failed due to missing credentials
    if twitter_client.initialization_failed:
        print("Exiting application due to missing Twitter API credentials.")
        sys.exit(1) # Exit with an error code
    
    if not twitter_client.api:
        # This condition might be hit if authentication fails for reasons other than missing initial creds
        print("Twitter API not initialized (authentication may have failed). Exiting application.")
        sys.exit(1) # Exit with an error code
    
    # AI Generator Initialization
    ai_generator = None
    if TOGETHER_API_KEY: 
        try:
            ai_generator = AIContentGenerator(api_key=TOGETHER_API_KEY)
            print("AIContentGenerator initialized successfully with TOGETHER_API_KEY.")
        except ValueError as ve: # Catch error if API key is invalid (e.g., empty) as per AIContentGenerator's init
            print(f"Error initializing AIContentGenerator: {ve}")
            ai_generator = None 
    else:
        print("Warning: TOGETHER_API_KEY not found in .env. AI content generation features will be disabled.")
        # ai_generator remains None

    # Main menu loop
    # StitchyBot instance creation moved inside option '1' to ensure fresh data load each time.
    stitch_bot_instance = None # Can be initialized when needed

    while True:
        print("\nStitchyBot Menu:")
        print("1. Process timeline tweets & Update scores")
        print("2. Get AI tweet suggestion")
        print("3. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            print("\nProcessing timeline tweets...")
            # Create a new StitchyBot instance each time to reflect potential changes in data files
            # or to ensure a fresh start for processing.
            stitch_bot_instance = StitchyBot(twitter_client) 
            stitch_bot_instance.process_timeline_tweets() 
            stitch_bot_instance.print_scores()
            stitch_bot_instance._save_data_and_cache() # Explicitly save after processing and printing
            print("Timeline processing and score update complete.")
        elif choice == '2':
            print("\nGetting AI tweet suggestion...")
            if ai_generator:
                user_input = input("Enter a topic or keywords for your tweet suggestion: ")
                if user_input.strip():
                    print(f"Requesting AI suggestion for: \"{user_input}\"...")
                    suggestion = ai_generator.generate_text(prompt_text=user_input)
                    if suggestion:
                       print(f"\nSuggested tweet:\n--------------------\n{suggestion}\n--------------------")
                    else:
                       # AIContentGenerator's generate_text method already prints detailed error info.
                       print("Sorry, I couldn't generate a suggestion at this time. Please check the console for any API error messages.")
                else:
                    print("No topic provided. Please enter some keywords.")
            else:
                print("AI content generation is not available. Please ensure TOGETHER_API_KEY is correctly set in your .env file.")
        elif choice == '3':
            print("Exiting StitchyBot. Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")
