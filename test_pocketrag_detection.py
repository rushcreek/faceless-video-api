"""Test PocketRAG detection"""

# Test the detection function
def has_pocketrag_mention(text: str) -> bool:
    """Check if text mentions PocketRAG in any form"""
    text_lower = text.lower()
    pocketrag_variations = ['pocketrag', 'pocket rag', 'pocket-rag']
    return any(variation in text_lower for variation in pocketrag_variations)

# Test cases
test_cases = [
    "PocketRAG helps make that clarity stick.",
    "Speed is not hustle.",
    "This mentions pocket rag in the middle",
    "pocket-rag is mentioned here",
    "No mention of the product",
]

for test in test_cases:
    result = has_pocketrag_mention(test)
    print(f"Text: '{test}' -> Detection: {result}")
