class NotionBackend:
    kind = 'notion'
    def __init__(self, **kw):
        self.id = kw.get('id', 'notion')
        self.token = kw.get('token') or kw.get('api_key')
    def search(self, query, limit=5):
        return []
    def health(self):
        return {'id': self.id, 'kind': self.kind, 'ok': bool(self.token)}
