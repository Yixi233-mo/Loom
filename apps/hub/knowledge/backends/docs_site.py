class DocsSiteBackend:
    kind = 'docs'
    def __init__(self, **kw):
        self.id = kw.get('id', 'docs')
        self.entry = kw.get('entry') or kw.get('base_url') or ''
        self.pages = []
    def crawl(self):
        return 0
    def search(self, query, limit=5):
        return []
    def health(self):
        return {'id': self.id, 'kind': self.kind, 'ok': bool(self.entry), 'pages': len(self.pages)}
