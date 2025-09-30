load_dotenv()
os.environ["GROQ_API_KEY"] = "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"

# Initialize Groq client
client = groq.Client(api_key=os.environ["GROQ_API_KEY"])

