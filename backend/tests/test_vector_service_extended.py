import pytest
from app.services.vector_service import VectorService

@pytest.fixture
def vector_service():
    return VectorService()

def test_vector_service_initialization(vector_service):
    """Verify in-memory initialization and document loading."""
    assert len(vector_service.local_docs) >= 6
    status = vector_service.get_status()
    assert "connected" in status
    assert "backend" in status
    assert "indexed_count" in status
    assert status["indexed_count"] >= 6

def test_tokenize_cleanly(vector_service):
    """Verify tokenizer lowercases and strips punctuation."""
    tokens = vector_service._tokenize("Hello! Where is my Order #12345?")
    assert "hello" in tokens
    assert "where" in tokens
    assert "order" in tokens
    assert "12345" in tokens
    assert "!" not in tokens
    assert "#" not in tokens

def test_compute_in_memory_similarity(vector_service):
    """Verify similarity calculations for exact, partial, and disjoint matches."""
    doc = "AppleSupport iPhone battery rapid drain after iOS update"
    
    # Exact / high overlap
    score_high = vector_service._compute_in_memory_similarity("iPhone battery drain update", doc)
    assert score_high > 0.4
    
    # Disjoint match
    score_zero = vector_service._compute_in_memory_similarity("completely unrelated query xylophone", doc)
    assert score_zero == 0.0

@pytest.mark.asyncio
async def test_search_brand_filter(vector_service):
    """Verify search respects brand filtering."""
    results_apple = await vector_service.search(query="battery", brand="AppleSupport", top_k=5, score_threshold=0.1)
    for r in results_apple:
        assert r.brand.lower() == "applesupport"

    results_amazon = await vector_service.search(query="package", brand="AmazonHelp", top_k=5, score_threshold=0.1)
    for r in results_amazon:
        assert r.brand.lower() == "amazonhelp"

@pytest.mark.asyncio
async def test_search_top_k_limiting(vector_service):
    """Verify top_k bounds result length."""
    results = await vector_service.search(query="support", brand=None, top_k=2, score_threshold=0.01)
    assert len(results) <= 2

@pytest.mark.asyncio
async def test_search_threshold_rejection(vector_service):
    """Verify very high thresholds reject partial matches."""
    results = await vector_service.search(query="random non matching phrase", brand=None, top_k=5, score_threshold=0.99)
    assert len(results) == 0
