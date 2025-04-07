from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. Load your data
documents = SimpleDirectoryReader("./").load_data()

# 2. Use your Ollama model (deepseek-r1:1.5b)
llm = Ollama(
    model="deepseek-r1:1.5b",
    temperature=0.2,
    system_prompt="You are a UC transfer advisor. Only answer based on the IGETC document."
)

# 3. Use local sentence-transformer for embeddings
embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# 4. Register models globally
Settings.llm = llm
Settings.embed_model = embed_model

# 5. Build index and query engine
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()

# 6. CLI chatbot loop
print("📚 TransferAI IGETC Chat (type 'exit' to quit)\n")
while True:
    q = input("You: ")
    if q.lower() in ["exit", "quit"]: break
    response = query_engine.query(q)
    print(f"AI: {response}\n")
