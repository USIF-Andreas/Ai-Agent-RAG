#!/bin/bash
# Quick accuracy test for RAG system
# Tests both Ollama and OpenRouter providers

BASE_URL="http://localhost:8000"
TIMEOUT=120

echo "============================================================"
echo "RAG System Quick Accuracy Test"
echo "============================================================"
echo ""

# Test cases as "query|expected_keyword|provider"
declare -a TESTS=(
    "What is the best football player name?|Aiden|ollama"
    "What is the best football player name?|Aiden|openrouter"
    "Summarize the document in one sentence|football|ollama"
    "Summarize the document in one sentence|football|openrouter"
    "What are the key achievements mentioned?|ball control|ollama"
    "What are the key achievements mentioned?|ball control|openrouter"
)

TOTAL=0
PASSED=0

for TEST in "${TESTS[@]}"; do
    IFS='|' read -r QUERY KEYWORD PROVIDER <<< "$TEST"
    ((TOTAL++))
    
    echo "Test $TOTAL: Provider=$PROVIDER"
    echo "  Query: $QUERY"
    echo -n "  Expected keyword: '$KEYWORD' ... "
    
    # Send query
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/query" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$QUERY\", \"provider\": \"$PROVIDER\"}" \
        --max-time $TIMEOUT)
    
    # Check if keyword is in response
    ANSWER=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('answer',''))" 2>/dev/null)
    
    if echo "$ANSWER" | grep -qi "$KEYWORD"; then
        echo "✅ PASS"
        ((PASSED++))
    else
        echo "❌ FAIL"
        echo "  Answer: ${ANSWER:0:100}..."
    fi
    echo ""
done

echo "============================================================"
echo "Results: $PASSED/$TOTAL passed ($(($PASSED * 100 / $TOTAL))%)"
echo "============================================================"

if [ $PASSED -eq $TOTAL ]; then
    exit 0
else
    exit 1
fi
