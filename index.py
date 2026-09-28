class InvertedIndex:
    """커밋 메시지 키워드와 author를 기준으로 커밋 해시를 빠르게 찾기 위한 역색인."""

    def __init__(self):
        self.keyword_index: dict[str, list[str]] = {}
        self.author_index: dict[str, list[str]] = {}

    def add_commit(self, commit):
        """새 커밋 하나를 인덱스에 반영한다."""
        keywords = set(commit.message.lower().split())
        for keyword in keywords:
            self.keyword_index.setdefault(keyword, []).append(commit.hash)

        self.author_index.setdefault(commit.author.lower(), []).append(commit.hash)

    def search_keyword(self, keyword):
        """주어진 키워드를 포함한 커밋 해시 목록을 반환한다."""
        return self.keyword_index.get(keyword.lower(), [])

    def search_author(self, author):
        """주어진 author가 작성한 커밋 해시 목록을 반환한다."""
        return self.author_index.get(author.lower(), [])