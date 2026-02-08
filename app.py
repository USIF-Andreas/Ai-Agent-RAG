from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from agent import RAGAgent
import config

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Initialize RAG Agent
rag_agent = RAGAgent(
    model_name=config.LLM_MODEL,
    embeddings_model=config.EMBEDDINGS_MODEL,
    base_url=config.OLLAMA_BASE_URL
)

# Routes
@app.route("/")
def index():
    return redirect(url_for('chat'))

@app.route("/chat")
def chat():
    return render_template('chat.html', username='User')

@app.route("/api/query", methods=['POST'])
def query_agent():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid request'}), 400
            
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        print(f"\n🔍 Query: {query}")
        print("⏳ Processing (this may take a minute)...")
        response = rag_agent.query(query)
        print(f"✅ Response: {response[:100]}...\n")
        
        return jsonify({'response': response}), 200
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
