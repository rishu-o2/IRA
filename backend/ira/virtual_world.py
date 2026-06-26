
class VirtualWorld:
    def __init__(self):
        self.state = {
            "mood": "helpful",
            "knowledge_base": ["pasta", "coding", "assistant_logic"],
            "last_interaction": None
        }

    def update_state(self, key, value):
        self.state[key] = value
        return f"Virtual world updated: {key} is now {value}."

    def get_status(self):
        return self.state
