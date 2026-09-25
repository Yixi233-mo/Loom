import json
from pathlib import Path

from knowledge.backends.base import make_backend


class FederatedKnowledge:
    def __init__(self, store, sources_path='plugins/knowledge_sources.json'):
        self.store = store
        self.sources_path = Path(sources_path)
        self.sources = []
        self.backends = []
        self._load()

    def _load(self):
        if self.sources_path.exists():
            try:
                self.sources = json.loads(self.sources_path.read_text(encoding='utf-8')) or []
            except Exception:
                self.sources = []
        self._rebuild()

    def _persist(self):
        self.sources_path.parent.mkdir(parents=True, exist_ok=True)
        self.sources_path.write_text(json.dumps(self.sources, ensure_ascii=False, indent=2), encoding='utf-8')
        self._rebuild()

    def _rebuild(self):
        from knowledge.backends.local import LocalBackend
        self.backends = [LocalBackend(id='local', store=self.store)]
        for conf in self.sources:
            if not conf.get('enabled', True):
                continue
            try:
                self.backends.append(make_backend(conf, store=self.store))
            except Exception:
                continue

    def list_sources(self):
        out = []
        for conf in self.sources:
            bid = str(conf.get('id'))
            health = {'ok': False}
            for b in self.backends:
                if b.id == bid:
                    try:
                        health = b.health()
                    except Exception as e:
                        health = {'ok': False, 'error': str(e)}
            out.append({**conf, 'health': health})
        return out

    def add_source(self, conf):
        make_backend(conf, store=self.store)
        self.sources = [s for s in self.sources if s.get('id') != conf.get('id')]
        conf = dict(conf)
        conf.setdefault('enabled', True)
        self.sources.append(conf)
        self._persist()
        return conf

    def remove_source(self, source_id):
        before = len(self.sources)
        self.sources = [s for s in self.sources if s.get('id') != source_id]
        if len(self.sources) != before:
            self._persist()
            return True
        return False

    def search(self, query, limit=8):
        merged = []
        for b in self.backends:
            try:
                merged.extend(b.search(query, limit=max(3, limit)))
            except Exception:
                continue
        merged.sort(key=lambda h: -h.score)
        seen = set()
        uniq = []
        for h in merged:
            key = h.url or h.id
            if key in seen:
                continue
            seen.add(key)
            uniq.append(h)
        return uniq[:limit]

    def answer(self, prompt):
        hits = self.search(prompt, limit=5)
        if not hits:
            return {'summary': '各知识源中都没有找到相关内容。', 'citations': [], 'hits': 0}
        lines = []
        citations = []
        for i, h in enumerate(hits, 1):
            lines.append(str(i) + ']' + ' (' + h.source + ') ' + h.title + '：' + h.snippet)
            citations.append({'id': h.id, 'title': h.title, 'score': h.score, 'snippet': h.snippet, 'source': h.source, 'url': h.url})
        return {'summary': '跨知识源检索结果：\n' + '\n'.join(lines), 'citations': citations, 'hits': len(hits)}
