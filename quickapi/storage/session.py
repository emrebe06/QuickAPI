class SessionStore:
    def __init__(self):
        self._sessions = {}

    def get(self, session_id):
        return self._sessions.get(session_id)

    def set(self, session_id, data):
        self._sessions[session_id] = data
        return data
