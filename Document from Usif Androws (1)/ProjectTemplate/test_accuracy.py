#!/usr/bin/env python3
"""
RAG System Accuracy Evaluation Framework
Tests the accuracy of the RAG system with different LLM providers
"""
import json
import time
import requests
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TestCase:
    """A test case for evaluating RAG accuracy"""
    query: str
    expected_keywords: List[str]
    provider: str
    description: str


@dataclass
class TestResult:
    """Result of a single test case"""
    test_case: TestCase
    response: str
    success: bool
    latency_ms: float
    error: str = ""


class RAGAccuracyTester:
    """Test accuracy of RAG system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[TestResult] = []
    
    def query_rag(self, query: str, provider: str, timeout: int = 120) -> Dict[str, Any]:
        """Send query to RAG system"""
        start = time.perf_counter()
        try:
            response = requests.post(
                f"{self.base_url}/api/query",
                json={"query": query, "provider": provider},
                timeout=timeout
            )
            latency_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "answer": data.get("answer", ""),
                    "model": data.get("model", ""),
                    "generation_mode": data.get("generation_mode", ""),
                    "retrieved_count": data.get("retrieved_count", 0),
                    "latency_ms": latency_ms,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "answer": "",
                    "model": "",
                    "generation_mode": "",
                    "retrieved_count": 0,
                    "latency_ms": latency_ms,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "answer": "",
                "model": "",
                "generation_mode": "",
                "retrieved_count": 0,
                "latency_ms": latency_ms,
                "error": str(e)
            }
    
    def check_keywords(self, text: str, keywords: List[str]) -> float:
        """Check what percentage of keywords appear in the text"""
        if not keywords:
            return 1.0
        
        text_lower = text.lower()
        found = sum(1 for kw in keywords if kw.lower() in text_lower)
        return found / len(keywords)
    
    def run_test_case(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        print(f"\n📝 Test: {test_case.description}")
        print(f"   Query: {test_case.query}")
        print(f"   Provider: {test_case.provider}")
        
        result = self.query_rag(test_case.query, test_case.provider)
        
        if not result["success"]:
            print(f"   ❌ Error: {result['error']}")
            return TestResult(
                test_case=test_case,
                response="",
                success=False,
                latency_ms=result["latency_ms"],
                error=result["error"]
            )
        
        # Check accuracy
        accuracy = self.check_keywords(result["answer"], test_case.expected_keywords)
        success = accuracy >= 0.5  # At least 50% keywords found
        
        print(f"   ✅ Answer: {result['answer'][:100]}...")
        print(f"   📊 Accuracy: {accuracy*100:.1f}% ({'✅' if success else '⚠️'})")
        print(f"   ⏱️  Latency: {result['latency_ms']:.0f}ms")
        print(f"   🤖 Model: {result['model']}")
        
        return TestResult(
            test_case=test_case,
            response=result["answer"],
            success=success,
            latency_ms=result["latency_ms"]
        )
    
    def run_test_suite(self, test_cases: List[TestCase]) -> Dict[str, Any]:
        """Run all test cases and return summary"""
        print("=" * 60)
        print("🚀 RAG Accuracy Test Suite")
        print("=" * 60)
        
        provider_stats = {}
        
        for test_case in test_cases:
            result = self.run_test_case(test_case)
            self.results.append(result)
            
            # Track stats by provider
            provider = test_case.provider
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "total": 0,
                    "success": 0,
                    "latency_sum": 0.0
                }
            
            provider_stats[provider]["total"] += 1
            if result.success:
                provider_stats[provider]["success"] += 1
            provider_stats[provider]["latency_sum"] += result.latency_ms
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        for provider, stats in provider_stats.items():
            total = stats["total"]
            success = stats["success"]
            avg_latency = stats["latency_sum"] / total if total > 0 else 0
            
            print(f"\n🔧 Provider: {provider.upper()}")
            print(f"   Tests: {total}")
            print(f"   Success: {success}/{total} ({success/total*100:.1f}%)")
            print(f"   Avg Latency: {avg_latency:.0f}ms")
        
        # Overall stats
        total_tests = len(self.results)
        total_success = sum(1 for r in self.results if r.success)
        
        print(f"\n🎯 OVERALL")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Success: {total_success}/{total_tests} ({total_success/total_tests*100:.1f}%)")
        
        return {
            "total_tests": total_tests,
            "total_success": total_success,
            "success_rate": total_success / total_tests if total_tests > 0 else 0,
            "provider_stats": provider_stats,
            "results": self.results
        }
    
    def save_results(self, filename: str = "accuracy_results.json"):
        """Save results to JSON file"""
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(self.results),
            "results": [
                {
                    "query": r.test_case.query,
                    "provider": r.test_case.provider,
                    "description": r.test_case.description,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "response": r.response[:500],
                    "error": r.error
                }
                for r in self.results
            ]
        }
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Results saved to {filename}")


def get_test_cases() -> List[TestCase]:
    """Define test cases for accuracy evaluation"""
    return [
        # Basic document questions
        TestCase(
            query="What is the name of the best football player?",
            expected_keywords=["Aiden", "Kareem", "TR"],
            provider="ollama",
            description="Ollama: Basic entity extraction"
        ),
        TestCase(
            query="What is the name of the best football player?",
            expected_keywords=["Aiden", "Kareem", "TR"],
            provider="openrouter",
            description="OpenRouter: Basic entity extraction"
        ),
        
        # Summary questions
        TestCase(
            query="Summarize what this document is about",
            expected_keywords=["football", "player", "Aiden", "Kareem"],
            provider="ollama",
            description="Ollama: Document summarization"
        ),
        TestCase(
            query="Summarize what this document is about",
            expected_keywords=["football", "player", "Aiden", "Kareem"],
            provider="openrouter",
            description="OpenRouter: Document summarization"
        ),
        
        # Specific details
        TestCase(
            query="What are Aiden Kareem's key achievements?",
            expected_keywords=["ball control", "dribbling", "tactical", "leadership"],
            provider="ollama",
            description="Ollama: Detail extraction"
        ),
        TestCase(
            query="What are Aiden Kareem's key achievements?",
            expected_keywords=["ball control", "dribbling", "tactical", "leadership"],
            provider="openrouter",
            description="OpenRouter: Detail extraction"
        ),
        
        # Edge cases
        TestCase(
            query="What is machine learning?",
            expected_keywords=["not", "found", "document", "context"],
            provider="ollama",
            description="Ollama: Out-of-context question"
        ),
        TestCase(
            query="What is machine learning?",
            expected_keywords=["not", "found", "document", "context"],
            provider="openrouter",
            description="OpenRouter: Out-of-context question"
        ),
    ]


if __name__ == "__main__":
    print("🚀 Starting RAG Accuracy Evaluation")
    print("Make sure the RAG system is running on http://localhost:8000")
    print("Press Enter to continue or Ctrl+C to cancel...")
    input()
    
    tester = RAGAccuracyTester(base_url="http://localhost:8000")
    test_cases = get_test_cases()
    
    results = tester.run_test_suite(test_cases)
    tester.save_results("accuracy_results.json")
    
    print("\n✅ Accuracy evaluation complete!")
