EMBED_MODEL = "BAAI/bge-large-en"

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

TOP_K_TABLES = 3
TOP_K_COLUMNS = 5

# Ollama settings
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gpt-oss:120b-cloud"  # change to any model you have pulled, e.g. "mistral", "codellama"

# Oracle DB connection settings — fill these in before running
DB_HOST     = "3.6.209.141"
DB_PORT     = 1521
DB_SERVICE  = "XE"          # or SID, e.g. "xe"
DB_USER     = "SOUTHINDIANBANK"
DB_PASSWORD = "southindianbank1123"
DB_MAX_ROWS = 100              # max rows to fetch per query

# Sarvam AI — Speech-to-Text + Translation
# Get your key at: https://dashboard.sarvam.ai
SARVAM_API_KEY ="sk_dan14ij9_Nq6ivwxYVv5tsmVCRRYS5MoE"