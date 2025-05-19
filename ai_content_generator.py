import openai
import os

class AIContentGenerator:
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key for AIContentGenerator cannot be None or empty.")
        self.api_key = api_key
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.together.xyz/v1"
        )

    def generate_text(self, prompt_text, model_name="meta-llama/Llama-3-8b-chat-hf", max_tokens_suggestion=70, temperature=0.7):
        """
        Generates text using the Together.ai API via the OpenAI client.

        Args:
            prompt_text (str): The input prompt for the AI.
            model_name (str): The name of the model to use.
            max_tokens_suggestion (int): Suggested maximum number of tokens for the generated content.
            temperature (float): The sampling temperature.

        Returns:
            str: The generated text, or None if an error occurred.
        """
        messages = [
            {"role": "system", "content": "You are a helpful assistant that generates concise and engaging content based on the provided topic or keywords. Aim for content suitable for a tweet."},
            {"role": "user", "content": prompt_text}
        ]

        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens_suggestion,
                temperature=temperature,
                n=1,  # Number of completions to generate
                stop=None # Optional: sequences where the API will stop generating further tokens
            )
            
            if response.choices and len(response.choices) > 0:
                generated_text = response.choices[0].message.content.strip()
                return generated_text
            else:
                print("Error: No content generated. The response did not contain expected choices.")
                return None

        except openai.APIConnectionError as e:
            print(f"Network error connecting to Together.ai API: {e}")
            print("Please check your network connection and API endpoint.")
            return None
        except openai.RateLimitError as e:
            print(f"Rate limit exceeded for Together.ai API: {e}")
            print("Please check your API plan and usage limits.")
            return None
        except openai.APIStatusError as e:
            print(f"Together.ai API returned an error status: {e}")
            print(f"Status Code: {e.status_code}, Response: {e.response}")
            return None
        except openai.APIError as e:
            print(f"An unexpected error occurred with the Together.ai API: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during text generation: {e}")
            return None

if __name__ == '__main__':
    # This is a basic test block that will only run when the script is executed directly.
    # It requires the TOGETHER_API_KEY to be set in the environment.
    print("Attempting basic test of AIContentGenerator...")
    api_key_from_env = os.getenv("TOGETHER_API_KEY")
    
    if not api_key_from_env:
        print("TOGETHER_API_KEY not found in environment variables. Skipping direct test of AIContentGenerator.")
    else:
        print(f"TOGETHER_API_KEY found. Initializing AIContentGenerator with key: {api_key_from_env[:5]}... (truncated)")
        try:
            generator = AIContentGenerator(api_key=api_key_from_env)
            prompt = "Generate a short, engaging tweet about the future of renewable energy."
            print(f"Sending prompt: \"{prompt}\"")
            generated_content = generator.generate_text(prompt)
            
            if generated_content:
                print(f"\nGenerated Content:\n--------------------\n{generated_content}\n--------------------")
            else:
                print("\nFailed to generate content from the direct test.")
        
        except ValueError as ve:
            print(f"ValueError during AIContentGenerator instantiation: {ve}")
        except Exception as ex:
            print(f"An unexpected error occurred during the direct test: {ex}")

    print("\nBasic test finished. If no output above, TOGETHER_API_KEY might be missing or other issues occurred.")
