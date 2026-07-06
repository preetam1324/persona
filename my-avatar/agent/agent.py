"""Custom agent logic (optional).

Override methods here only if you need behavior beyond what config.yaml provides.
For most agents, config.yaml alone is sufficient — no Python needed.
"""

from persona.core.agent import Agent


class MyAgent(Agent):
    def load(self):
        """Called once on startup. Load custom resources here."""
        pass

    # Uncomment to override the default agent loop:
    #
    # async def handle(self, message, context):
    #     \"\"\"Full control over message processing.\"\"\"
    #     # Your custom logic here
    #     ...
