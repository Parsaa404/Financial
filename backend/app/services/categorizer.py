"""AI Categorization service — 3-layer approach."""
import json
import logging
import re

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Layer 1: Rule-based merchant → category mapping
CATEGORY_RULES: dict[str, list[str]] = {
    "Food & Dining": ["starbucks", "mcdonalds", "restaurant", "cafe", "grocery", "supermarket", "pizza", "burger", "sushi", "bakery", "doordash", "ubereats", "grubhub"],
    "Transportation": ["uber", "lyft", "gas", "parking", "transit", "metro", "fuel", "shell", "chevron", "bp"],
    "Shopping": ["amazon", "ebay", "shop", "mall", "store", "zara", "h&m", "walmart", "target", "costco"],
    "Entertainment": ["netflix", "spotify", "cinema", "game", "steam", "youtube", "hulu", "disney", "hbo"],
    "Healthcare": ["pharmacy", "doctor", "hospital", "clinic", "dental", "cvs", "walgreens", "medical"],
    "Bills & Utilities": ["electric", "water", "internet", "phone", "insurance", "rent", "mortgage", "verizon", "comcast", "at&t"],
    "Income": ["salary", "payroll", "freelance", "deposit", "transfer in", "direct dep"],
    "Travel": ["hotel", "airbnb", "flight", "airline", "booking", "expedia", "marriott"],
    "Education": ["course", "udemy", "school", "university", "book", "coursera", "tuition"],
    "Personal Care": ["salon", "gym", "spa", "beauty", "haircut", "fitness"],
}

NECESSITY_SCORES: dict[str, int] = {
    "Bills & Utilities": 9,
    "Healthcare": 8,
    "Food & Dining": 6,
    "Transportation": 6,
    "Education": 6,
    "Travel": 4,
    "Shopping": 3,
    "Personal Care": 3,
    "Entertainment": 2,
    "Income": 10,
}

CATEGORIZE_PROMPT = """Categorize this transaction.
Merchant: {merchant}
Amount: {amount}
Time: {time}
Categories: {categories}
Return ONLY JSON: {{"category": "...", "subcategory": "...", "necessity_score": 0-10}}"""


class CategorizationService:
    """3-layer transaction categorization: rules → personal → AI."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def categorize_by_rules(self, merchant: str) -> tuple[str | None, float]:
        """Layer 1: Rule-based categorization. Returns (category, confidence)."""
        if not merchant:
            return None, 0.0

        merchant_lower = merchant.lower().strip()
        for category, keywords in CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword in merchant_lower:
                    return category, 0.9
        return None, 0.0

    def categorize_by_personal_rules(
        self, merchant: str, user_rules: dict[str, str]
    ) -> tuple[str | None, float]:
        """Layer 2: User's personal merchant→category mapping."""
        if not merchant or not user_rules:
            return None, 0.0

        merchant_lower = merchant.lower().strip()
        for rule_merchant, category in user_rules.items():
            if rule_merchant in merchant_lower or merchant_lower in rule_merchant:
                return category, 0.95
        return None, 0.0

    async def categorize_by_ai(
        self, merchant: str, amount_cents: int, transacted_at: str
    ) -> tuple[str | None, str | None, int | None]:
        """Layer 3: Groq API categorization. Returns (category, subcategory, necessity_score)."""
        if not self.settings.groq_api_key:
            logger.warning("Groq API key not configured, skipping AI categorization")
            return None, None, None

        categories = ", ".join(CATEGORY_RULES.keys())
        amount = amount_cents / 100.0
        prompt = CATEGORIZE_PROMPT.format(
            merchant=merchant,
            amount=f"${amount:.2f}",
            time=transacted_at,
            categories=categories,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gemma2-9b-it",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 60,
                        "temperature": 0.1,
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Parse JSON response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return (
                        result.get("category"),
                        result.get("subcategory"),
                        result.get("necessity_score"),
                    )
        except Exception as e:
            logger.error("Groq categorization failed: %s", e)

        return None, None, None

    async def categorize(
        self,
        merchant: str,
        amount_cents: int,
        transacted_at: str,
        user_rules: dict[str, str] | None = None,
    ) -> dict:
        """Full 3-layer categorization pipeline."""
        # Layer 1: Rule-based
        category, confidence = self.categorize_by_rules(merchant)
        if category and confidence >= 0.85:
            return {
                "category": category,
                "subcategory": None,
                "necessity_score": NECESSITY_SCORES.get(category, 5),
                "category_source": "rule",
                "confidence": confidence,
            }

        # Layer 2: Personal rules
        if user_rules:
            category, confidence = self.categorize_by_personal_rules(merchant, user_rules)
            if category and confidence >= 0.85:
                return {
                    "category": category,
                    "subcategory": None,
                    "necessity_score": NECESSITY_SCORES.get(category, 5),
                    "category_source": "user",
                    "confidence": confidence,
                }

        # Layer 3: AI (Groq)
        ai_cat, ai_subcat, ai_score = await self.categorize_by_ai(
            merchant, amount_cents, transacted_at
        )
        if ai_cat:
            return {
                "category": ai_cat,
                "subcategory": ai_subcat,
                "necessity_score": ai_score or NECESSITY_SCORES.get(ai_cat, 5),
                "category_source": "ai",
                "confidence": 0.7,
            }

        # Fallback
        return {
            "category": "Uncategorized",
            "subcategory": None,
            "necessity_score": 5,
            "category_source": "rule",
            "confidence": 0.0,
        }

    @staticmethod
    def clean_merchant_name(merchant: str) -> str:
        """Normalize merchant name for matching."""
        if not merchant:
            return ""
        cleaned = re.sub(r'[#\d]+$', '', merchant)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned.title()
