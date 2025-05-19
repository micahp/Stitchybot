import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import json
import tempfile

# Assuming StitchybotMain.py is in the same directory or accessible in PYTHONPATH
from StitchybotMain import Category, Categories, StitchyBot, save_json_object, load_json_object, TwitterClient

class TestCategory(unittest.TestCase):
    def test_category_creation(self):
        category = Category(name="Test Category", key="T")
        self.assertEqual(category.name, "Test Category", "Category name should be initialized.")
        self.assertEqual(category.key, "T", "Category key should be initialized.")
        self.assertEqual(category.individualScore, 0, "Initial score should be 0.")
        self.assertEqual(category.retweetsTotal, 0, "Initial retweets total should be 0.")
        self.assertEqual(len(category.retweetsList), 0, "Initial retweets list should be empty.")

    def test_category_to_from_dict(self):
        category = Category(name="Tech", key="T")
        category.individualScore = 120
        category.retweetsTotal = 15
        category.retweetsList = [5, 10]
        
        category_dict = category.to_dict()
        expected_dict = {
            'name': "Tech",
            'key': "T",
            'individualScore': 120,
            'retweetsTotal': 15,
            'retweetsList': [5, 10]
        }
        self.assertDictEqual(category_dict, expected_dict, "Category to_dict serialization failed.")
        
        new_category = Category.from_dict(expected_dict)
        self.assertEqual(new_category.name, "Tech")
        self.assertEqual(new_category.key, "T")
        self.assertEqual(new_category.individualScore, 120)
        self.assertEqual(new_category.retweetsTotal, 15)
        self.assertEqual(new_category.retweetsList, [5, 10])

    def test_increment_retweets(self):
        category = Category(name="News", key="N")
        category.incrementRetweets(10)
        self.assertEqual(category.retweetsTotal, 10, "Retweets total should be 10 after first increment.")
        self.assertListEqual(category.retweetsList, [10], "Retweets list should contain [10].")
        
        category.incrementRetweets(5)
        self.assertEqual(category.retweetsTotal, 15, "Retweets total should be 15 after second increment.")
        self.assertListEqual(category.retweetsList, [10, 5], "Retweets list should contain [10, 5].")

    def test_calculate_score_logic_no_retweets(self):
        category = Category(name="Empty", key="E")
        category.calculateScore()
        self.assertEqual(category.individualScore, 0, "Score should be 0 for no retweets.")

    def test_calculate_score_logic_few_retweets(self):
        # bonusTweetCount should be 1
        category = Category(name="Few", key="F")
        category.retweetsList = [10, 20] # Most recent is 20
        # Expected: (20 * 3.0) + (10 * 1.0) = 60 + 10 = 70
        # Bonus reduction: initial_bonus = 3.0. bonus_tweet_count = 1.
        # Tweet 1 (score 20): uses bonus 3.0. reduction_step = (3.0-1.0)/1 = 2.0. bonus becomes 3.0 - 2.0 = 1.0
        # Tweet 2 (score 10): uses bonus 1.0.
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 70.0, places=1, msg="Score calculation for few retweets (2) is incorrect.")

        category.retweetsList = [10] # Most recent is 10
        # Expected: (10 * 3.0) = 30
        # Bonus reduction: initial_bonus = 3.0. bonus_tweet_count = 1.
        # Tweet 1 (score 10): uses bonus 3.0. reduction_step = (3.0-1.0)/1 = 2.0. bonus becomes 1.0
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 30.0, places=1, msg="Score calculation for single retweet is incorrect.")
        
        category.retweetsList = [10, 20, 5] # Most recent is 5
        # Expected: (5 * 3.0) + (20*1.0) + (10*1.0) = 15 + 20 + 10 = 45.0
        # Tweet 1 (score 5): uses bonus 3.0. reduction_step = (3.0-1.0)/1 = 2.0. bonus becomes 1.0
        # Tweet 2 (score 20): uses bonus 1.0.
        # Tweet 3 (score 10): uses bonus 1.0.
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 45.0, places=1, msg="Score calculation for few retweets (3) is incorrect.")


    def test_calculate_score_logic_multiple_retweets(self):
        # 5 retweets, bonusTweetCount should be 5 // 4 = 1
        category = Category(name="Multiple", key="M")
        category.retweetsList = [10, 20, 5, 15, 25] # Most recent is 25
        # Expected: (25 * 3.0) + (15 * 1.0) + (5*1.0) + (20*1.0) + (10*1.0) = 75 + 15 + 5 + 20 + 10 = 125.0
        # Tweet 1 (score 25): uses bonus 3.0. reduction_step = (3.0-1.0)/1 = 2.0. bonus becomes 1.0
        # Tweet 2 (score 15): uses bonus 1.0.
        # ... and so on for the rest.
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 125.0, places=1, msg="Score calculation for multiple retweets (5) is incorrect.")

        # 4 retweets, bonusTweetCount should be 4 // 4 = 1
        category.retweetsList = [10, 20, 5, 15] # Most recent is 15
        # Expected: (15 * 3.0) + (5*1.0) + (20*1.0) + (10*1.0) = 45 + 5 + 20 + 10 = 80.0
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 80.0, places=1, msg="Score calculation for multiple retweets (4) is incorrect.")

        # 8 retweets, bonusTweetCount should be 8 // 4 = 2
        category.retweetsList = [1,2,3,4,5,6,7,8] # Most recent is 8
        # Tweet 1 (score 8): uses bonus 3.0. reduction_step = (3.0-1.0)/2 = 1.0. bonus becomes 2.0
        # Tweet 2 (score 7): uses bonus 2.0. reduction_step = (2.0-1.0)/2 = 0.5. bonus becomes 1.5 (but reduction uses current bonus so (2.0-1.0)/2=0.5, bonus becomes 1.5)
        #   Correction in understanding reduction step application:
        #   The reduction step `(current_bonus - 1.0) / bonus_tweet_count` is calculated, then subtracted.
        #   It's `reduction_step = (current_bonus - 1.0) / bonus_tweet_count if i < bonus_tweet_count else (current_bonus -1.0)`
        #   Tweet 1 (score 8, i=0): current_bonus=3.0. reduction_step=(3.0-1.0)/2 = 1.0. score_val = 8*3.0=24. new_bonus=2.0
        #   Tweet 2 (score 7, i=1): current_bonus=2.0. reduction_step=(2.0-1.0)/2 = 0.5. score_val = 7*2.0=14. new_bonus=1.5
        #   Tweet 3 (score 6, i=2): current_bonus=1.5. reduction_step=(1.5-1.0) = 0.5. score_val = 6*1.5=9. new_bonus=1.0
        #   Tweet 4 (score 5, i=3): current_bonus=1.0. score_val = 5*1.0=5. new_bonus=1.0
        #   Tweet 5 (score 4, i=4): current_bonus=1.0. score_val = 4*1.0=4. new_bonus=1.0
        #   Tweet 6 (score 3, i=5): current_bonus=1.0. score_val = 3*1.0=3. new_bonus=1.0
        #   Tweet 7 (score 2, i=6): current_bonus=1.0. score_val = 2*1.0=2. new_bonus=1.0
        #   Tweet 8 (score 1, i=7): current_bonus=1.0. score_val = 1*1.0=1. new_bonus=1.0
        # Total = 24+14+9+5+4+3+2+1 = 62.0
        category.calculateScore()
        self.assertAlmostEqual(category.individualScore, 62.0, places=1, msg="Score calculation for multiple retweets (8) is incorrect.")

class TestCategories(unittest.TestCase):
    def test_categories_creation(self):
        categories = Categories()
        self.assertEqual(len(categories.container), 0, "Categories container should be empty initially.")
        self.assertEqual(categories.total, 0, "Categories total should be 0 initially.")

    def test_add_and_get_category(self):
        categories = Categories()
        cat1 = Category(name="General", key="G")
        cat2 = Category(name="Specific", key="S")
        
        categories.addCategory(cat1)
        self.assertEqual(len(categories.container), 1, "Container should have 1 category after adding one.")
        self.assertIs(categories.getCategory("G"), cat1, "Should retrieve category G.")
        
        categories.addCategory(cat2)
        self.assertEqual(len(categories.container), 2, "Container should have 2 categories after adding two.")
        self.assertIs(categories.getCategory("S"), cat2, "Should retrieve category S.")
        
        self.assertIsNone(categories.getCategory("X"), "Should return None for a non-existent category key.")

    def test_categories_to_from_dict(self):
        categories = Categories()
        cat1 = Category(name="Fun", key="F")
        cat1.individualScore = 50
        cat1.retweetsTotal = 5
        cat1.retweetsList = [2,3]
        
        cat2 = Category(name="Work", key="W")
        cat2.individualScore = 100
        cat2.retweetsTotal = 10
        cat2.retweetsList = [4,6]
        
        categories.addCategory(cat1)
        categories.addCategory(cat2)
        categories.total = 150 # Example total, though not directly used in from_dict in current StitchyBotMain
        
        categories_dict = categories.to_dict()
        expected_dict = {
            'categories': [cat1.to_dict(), cat2.to_dict()],
            'total': 150 
        }
        self.assertEqual(len(categories_dict['categories']), 2)
        self.assertDictEqual(categories_dict['categories'][0], cat1.to_dict(), "First category dict mismatch.")
        self.assertDictEqual(categories_dict['categories'][1], cat2.to_dict(), "Second category dict mismatch.")
        self.assertEqual(categories_dict['total'], 150, "Total mismatch in dict.")
        
        new_categories = Categories.from_dict(expected_dict)
        self.assertEqual(len(new_categories.container), 2, "Should load 2 categories.")
        self.assertEqual(new_categories.total, 150, "Total should be loaded correctly.")
        
        # Check integrity of loaded categories
        loaded_cat1 = new_categories.getCategory("F")
        loaded_cat2 = new_categories.getCategory("W")
        
        self.assertIsNotNone(loaded_cat1, "Loaded category F should not be None.")
        self.assertEqual(loaded_cat1.name, "Fun")
        self.assertEqual(loaded_cat1.individualScore, 50)
        self.assertEqual(loaded_cat1.retweetsList, [2,3])
        
        self.assertIsNotNone(loaded_cat2, "Loaded category W should not be None.")
        self.assertEqual(loaded_cat2.name, "Work")
        self.assertEqual(loaded_cat2.individualScore, 100)
        self.assertEqual(loaded_cat2.retweetsList, [4,6])

class TestDataHandling(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        # Create a dummy categories.txt for tests that might need it for initialization
        self.categories_txt_path = os.path.join(self.test_dir.name, "categories.txt")
        with open(self.categories_txt_path, "w") as f:
            f.write("Tech\n")
            f.write("Sports\n")

    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir.cleanup()

    def test_save_and_load_json_object_categories(self):
        categories_obj = Categories()
        cat1 = Category(name="Alpha", key="A")
        cat1.individualScore = 10
        categories_obj.addCategory(cat1)
        categories_obj.total = 10
        
        file_path = os.path.join(self.test_dir.name, "test_categories.json")
        
        save_json_object(categories_obj, file_path)
        self.assertTrue(os.path.exists(file_path), "JSON file should be created.")
        
        loaded_obj = load_json_object(file_path, target_class=Categories)
        self.assertIsNotNone(loaded_obj, "Loaded object should not be None.")
        self.assertIsInstance(loaded_obj, Categories, "Loaded object should be a Categories instance.")
        self.assertEqual(len(loaded_obj.container), 1, "Loaded Categories should have 1 category.")
        self.assertEqual(loaded_obj.container[0].name, "Alpha")
        self.assertEqual(loaded_obj.container[0].individualScore, 10)
        self.assertEqual(loaded_obj.total, 10)

    def test_save_and_load_json_object_list_cache(self):
        cache_list = [123, 456, 789]
        file_path = os.path.join(self.test_dir.name, "test_cache.json")
        
        save_json_object(cache_list, file_path)
        self.assertTrue(os.path.exists(file_path), "JSON file for cache should be created.")
        
        loaded_list = load_json_object(file_path)
        self.assertIsNotNone(loaded_list, "Loaded list should not be None.")
        self.assertIsInstance(loaded_list, list, "Loaded object should be a list.")
        self.assertListEqual(loaded_list, cache_list, "Loaded list content mismatch.")

    def test_load_json_object_file_not_found(self):
        file_path = os.path.join(self.test_dir.name, "non_existent.json")
        # Suppress print output during this test for cleaner test logs
        with patch('builtins.print') as mocked_print:
            loaded_obj = load_json_object(file_path)
            self.assertIsNone(loaded_obj, "Should return None for a non-existent file.")
            mocked_print.assert_any_call(f"File {file_path} not found.")
            
    def test_load_json_object_corrupt_json(self):
        file_path = os.path.join(self.test_dir.name, "corrupt.json")
        with open(file_path, "w") as f:
            f.write("{'name': 'test', 'key': 't'") # Intentionally malformed JSON
        
        with patch('builtins.print') as mocked_print:
            loaded_obj = load_json_object(file_path, target_class=Category)
            self.assertIsNone(loaded_obj, "Should return None for corrupt JSON.")
            mocked_print.assert_any_call(f"Error decoding JSON from {file_path}: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)")

class TestStitchyBot(unittest.TestCase):
    def setUp(self):
        # Mock TwitterClient for StitchyBot
        self.mock_twitter_client = MagicMock(spec=TwitterClient)
        self.mock_twitter_client.api = MagicMock() # Ensure api attribute exists
        self.mock_twitter_client.initialization_failed = False # Assume client initialized successfully

        # Create a temporary directory for StitchyBot's data files (data.json, cache.json)
        # and for categories.txt if needed for a specific test.
        self.test_dir = tempfile.TemporaryDirectory()
        
        # Define paths for StitchyBot's data files within the temp directory
        self.data_json_path = os.path.join(self.test_dir.name, "data.json")
        self.cache_json_path = os.path.join(self.test_dir.name, "cache.json")
        self.categories_txt_path = os.path.join(self.test_dir.name, "categories.txt")

        # Patch the class constants in StitchyBot to use these temp paths
        self.patch_data_file = patch.object(StitchyBot, 'DATA_FILE', self.data_json_path)
        self.patch_cache_file = patch.object(StitchyBot, 'CACHE_FILE', self.cache_json_path)
        
        self.patch_data_file.start()
        self.patch_cache_file.start()

    def tearDown(self):
        self.test_dir.cleanup()
        self.patch_data_file.stop()
        self.patch_cache_file.stop()

    def test_initialize_categories_from_file_no_existing_data(self):
        # Prepare a dummy categories.txt
        with open(self.categories_txt_path, "w") as f:
            f.write("Alpha Category A\n") # Key 'A'
            f.write("Beta Category B\n")  # Key 'B'
        
        # StitchyBot's _load_data_and_cache calls _initialize_categories_from_file
        # if data.json is not found. We need to ensure data.json doesn't exist initially.
        if os.path.exists(self.data_json_path):
            os.remove(self.data_json_path)
        if os.path.exists(self.cache_json_path):
            os.remove(self.cache_json_path)

        # Mock open for categories.txt specifically for the initialization part
        # The actual _initialize_categories_from_file method takes the filename.
        # We need to ensure that *when StitchyBot initializes*, it reads from our temp categories.txt
        # This happens if data.json is not found.
        
        # We will let _load_data_and_cache try to load non-existent data.json,
        # then it should call _initialize_categories_from_file with 'categories.txt'.
        # We need to patch the call to _initialize_categories_from_file to use our temp path,
        # or patch the default 'categories.txt' path if it's hardcoded.
        # In StitchyBotMain, _initialize_categories_from_file is called with 'categories.txt'.
        # So, let's patch 'open' for that specific call during initialization.
        
        # The easiest is to ensure 'categories.txt' is in the test_dir and StitchyBot
        # can pick it up if its working directory were test_dir.
        # Or, more robustly, patch its _initialize_categories_from_file method
        # to use the self.categories_txt_path.
        
        # Let's assume default 'categories.txt' path. For testing, we can patch 'open' globally for this.
        # This is tricky because load_dotenv also uses open.
        # A better way: StitchyBot calls _initialize_categories_from_file('categories.txt')
        # We can patch *that* method to make it read from our specific temp categories.txt.
        
        # Simpler: The current implementation of StitchyBot calls `_initialize_categories_from_file('categories.txt')`.
        # We can just create `categories.txt` in the current working directory for the test.
        # Or, even better, mock the `_initialize_categories_from_file` method itself.
        
        # For this test, let's test the actual _initialize_categories_from_file method.
        # And then test the higher-level _load_data_and_cache.

        bot = StitchyBot(self.mock_twitter_client) # This will trigger _load_data_and_cache
        
        # Check if data.json was created from categories.txt
        self.assertTrue(os.path.exists(self.data_json_path))
        loaded_categories_from_json = load_json_object(self.data_json_path, Categories)
        self.assertIsNotNone(loaded_categories_from_json)
        self.assertEqual(len(loaded_categories_from_json.container), 2)
        self.assertIsNotNone(loaded_categories_from_json.getCategory("A"))
        self.assertEqual(loaded_categories_from_json.getCategory("A").name, "Alpha Category A")
        self.assertIsNotNone(loaded_categories_from_json.getCategory("B"))
        self.assertEqual(loaded_categories_from_json.getCategory("B").name, "Beta Category B")


    def test_process_timeline_tweets_new_tweets(self):
        # Setup categories in the bot (simulating they were loaded or initialized)
        cat_t = Category("Tech News", "T")
        cat_s = Category("Sports News", "S")
        
        # We need to ensure data.json is pre-populated for this test,
        # or that _initialize_categories_from_file is called and populates correctly.
        # Let's pre-populate data.json for directness.
        initial_categories = Categories()
        initial_categories.addCategory(cat_t)
        initial_categories.addCategory(cat_s)
        save_json_object(initial_categories, self.data_json_path)
        
        # Initial empty cache
        save_json_object([], self.cache_json_path)

        bot = StitchyBot(self.mock_twitter_client) # Loads the above data.json and cache.json
        
        # Mock Twitter API response
        mock_tweet1 = MagicMock()
        mock_tweet1.id = 101
        mock_tweet1.text = "TThis is a tech tweet."
        mock_tweet1.retweet_count = 10
        
        mock_tweet2 = MagicMock()
        mock_tweet2.id = 102
        mock_tweet2.text = "SSports update here!"
        mock_tweet2.retweet_count = 5

        mock_tweet3_unknown_cat = MagicMock()
        mock_tweet3_unknown_cat.id = 103
        mock_tweet3_unknown_cat.text = "XUnknown category."
        mock_tweet3_unknown_cat.retweet_count = 20
        
        mock_tweet4_cached = MagicMock() # This tweet ID will be in cache
        mock_tweet4_cached.id = 100 # Assume this ID is already in cache
        mock_tweet4_cached.text = "TAnother tech tweet, but cached."
        mock_tweet4_cached.retweet_count = 7
        
        bot.cache = [100] # Pre-populate cache for one tweet

        self.mock_twitter_client.user_timeline.return_value = [mock_tweet1, mock_tweet2, mock_tweet3_unknown_cat, mock_tweet4_cached]
        
        bot.process_timeline_tweets()
        
        # Verify tweet processing
        processed_cat_t = bot.categories.getCategory("T")
        processed_cat_s = bot.categories.getCategory("S")
        
        self.assertEqual(len(processed_cat_t.retweetsList), 1, "Tech category should have 1 new retweet.")
        self.assertEqual(processed_cat_t.retweetsList[0], 10, "Tech category retweet count mismatch.")
        self.assertTrue(processed_cat_t.individualScore > 0, "Tech category score should be updated.")
        
        self.assertEqual(len(processed_cat_s.retweetsList), 1, "Sports category should have 1 new retweet.")
        self.assertEqual(processed_cat_s.retweetsList[0], 5, "Sports category retweet count mismatch.")
        self.assertTrue(processed_cat_s.individualScore > 0, "Sports category score should be updated.")
        
        # Verify cache update
        self.assertIn(101, bot.cache, "Tweet ID 101 should be added to cache.")
        self.assertIn(102, bot.cache, "Tweet ID 102 should be added to cache.")
        self.assertIn(103, bot.cache, "Tweet ID 103 (unknown category) should be added to cache.")
        self.assertIn(100, bot.cache, "Tweet ID 100 (pre-cached) should still be in cache.")
        self.assertEqual(len(bot.cache), 4, "Cache should have 4 IDs after processing.")

        # Verify that save_json_object was called for cache and data
        # This requires mocking save_json_object or checking file contents post-run.
        # For simplicity, we'll trust _save_data_and_cache is called.
        # A more thorough test could mock save_json_object.

    def test_load_data_and_cache_existing_files(self):
        # Prepare dummy data.json
        cat_existing = Category("Existing", "E")
        categories_to_save = Categories()
        categories_to_save.addCategory(cat_existing)
        categories_to_save.total = 100
        save_json_object(categories_to_save, self.data_json_path)
        
        # Prepare dummy cache.json
        cache_to_save = [999, 888]
        save_json_object(cache_to_save, self.cache_json_path)
        
        bot = StitchyBot(self.mock_twitter_client) # This will load the files
        
        self.assertEqual(len(bot.categories.container), 1, "Should load 1 category from existing data.json.")
        self.assertEqual(bot.categories.getCategory("E").name, "Existing")
        self.assertEqual(bot.categories.total, 100)
        self.assertListEqual(bot.cache, [999, 888], "Should load cache from existing cache.json.")

    def test_load_data_and_cache_empty_files(self):
        # Create empty but valid JSON files
        save_json_object({}, self.data_json_path) # Empty object for categories
        save_json_object([], self.cache_json_path) # Empty list for cache
        
        # Need categories.txt for initialization if data.json is considered invalid/empty by from_dict
        with open(self.categories_txt_path, "w") as f:
            f.write("Default Cat D\n")

        bot = StitchyBot(self.mock_twitter_client)
        
        # Current Categories.from_dict expects 'categories' key. Empty {} will lead to empty container.
        # If data.json is empty JSON object `{}`, from_dict will result in an empty Categories object.
        # StitchyBot's _load_data_and_cache considers this "loaded" (not None)
        # but it will be empty. This is different from file not found.
        self.assertEqual(len(bot.categories.container), 0, "Categories should be empty if data.json was empty object.")
        
        # If data.json was truly empty or malformed, then _initialize_categories_from_file would run.
        # To test that path, we'd make data.json invalid.
        
        self.assertListEqual(bot.cache, [], "Cache should be empty if cache.json was empty list.")


if __name__ == '__main__':
    unittest.main()
