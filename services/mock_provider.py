class MockProvider:
    def generate_text(self, prompt: str) -> str:
        return (
            "Acesta este un răspuns de test. AI-ul real nu este apelat. "
            "Dacă vezi acest mesaj, înseamnă că flow-ul aplicației funcționează."
        )