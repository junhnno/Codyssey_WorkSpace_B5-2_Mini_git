from dataclasses import dataclass, field
from datetime import datetime
from sort_algo import merge_sort
from index import InvertedIndex

import hashlib

@dataclass(frozen=True)
class Commit:
    """하나의 커밋을 표현하는 불변 데이터. 생성 후 필드를 변경할 수 없다."""
    hash: str
    message: str
    author: str
    parents: list[str]
    created_on_branch: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Repository:
    """세션 전체의 저장소 상태. 모든 커밋과 브랜치 포인터를 관리한다."""

    commits: dict[str, Commit] = field(default_factory=dict)
    # hash -> Commit. 세션에서 만들어진 모든 커밋을 브랜치 구분 없이 전부 보관.

    branches: dict[str, str | None] = field(default_factory=dict)
    # branch_name -> 그 브랜치가 가리키는 최신 커밋의 hash. 커밋 없는 브랜치는 None.

    HEAD: str | None = None
    # 현재 브랜치의 "이름" (커밋 hash가 아님). INIT 전에는 None.

    current_user: str | None = None
    # INIT에서 설정된 사용자 이름. 이후 모든 COMMIT의 author로 사용.

    commit_seq: int = 0
    # 커밋 생성마다 1씩 증가. 해시 재료에 섞어 넣어 충돌을 원천 차단.

    index: InvertedIndex = field(default_factory=InvertedIndex)
    # 커밋 메시지 키워드 / author 검색을 위한 역색인.

    def generate_commit_hash(self, message, author, timestamp, parents):
        """커밋 메타데이터와 commit_seq를 조합해 SHA-1 해시를 생성한다.
        앞 7자를 우선 쓰되, 이미 존재하는 hash와 겹치면 길이를 늘려 유일성을 보장한다."""
        raw = f"{message}{author}{timestamp}{','.join(parents)}{self.commit_seq}"
        full_hash = hashlib.sha1(raw.encode()).hexdigest()
        length = 7
        while full_hash[:length] in self.commits:
            length += 1
        return full_hash[:length]

    def init(self, user_name):
        """저장소를 초기화한다. main 브랜치를 만들고 HEAD와 현재 사용자를 설정한다."""
        if self.HEAD is not None:
            return "Already initialized."

        self.current_user = user_name
        self.branches['main'] = None
        self.HEAD = 'main'
        return f"Initialized repository.\nCurrent branch: main\nCurrent user: {user_name}"

    def branch(self, branch_name):
        """현재 HEAD가 가리키는 커밋을 가리키는 새 브랜치를 만든다."""
        if self.HEAD is None:
            return "Repository not initialized."
        if branch_name in self.branches:
            return f"Branch already exists: {branch_name}"

        current_commit = self.branches[self.HEAD]
        self.branches[branch_name] = current_commit
        return f"Created branch: {branch_name}"

    def switch(self, branch_name):
        """HEAD를 지정한 브랜치로 이동시킨다."""
        if branch_name not in self.branches:
            return f"Unknown branch: {branch_name}"

        self.HEAD = branch_name
        return f"Switched to branch: {branch_name}"

    def commit(self, message):
        """현재 HEAD를 부모로 하는 새 커밋을 만들고 저장소에 등록한다."""
        if self.HEAD is None:
            return "Repository not initialized."

        if self.branches[self.HEAD] is None:
            new_parents = []
        else:
            new_parents = [self.branches[self.HEAD]]

        timestamp = datetime.now()
        new_hash = self.generate_commit_hash(message, self.current_user, timestamp, new_parents)
        new_commit = Commit(
            hash=new_hash,
            message=message,
            author=self.current_user,
            parents=new_parents,
            timestamp=timestamp,
            created_on_branch=self.HEAD
        )

        self.commits[new_hash] = new_commit
        self.branches[self.HEAD] = new_hash
        self.index.add_commit(new_commit)
        self.commit_seq += 1
        return f"[{self.HEAD} {new_hash}] {message}"

    def log(self, sort_by=None):
        """부모 커밋이 항상 자식보다 먼저 나오도록 커밋 목록을 출력한다.
        sort_by가 주어지면 그 기준으로 재정렬한다 ('date' 또는 'author')."""
        commit_list = list(self.commits.values())

        if sort_by == 'date':
            commit_list = merge_sort(commit_list, key=lambda c: c.timestamp)
        elif sort_by == 'author':
            commit_list = merge_sort(commit_list, key=lambda c: c.author)

        result = ""
        for c in commit_list:
            ts = c.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            result += f"commit {c.hash} ({c.author}, {ts}) [{c.created_on_branch}]\n{c.message}\n"
        return result

    def ancestors(self, commit_hash):
        """해당 커밋에서 도달 가능한 모든 조상 커밋의 hash를 반환한다.
        부모가 최대 1개이므로 parents를 따라 단순히 위로 거슬러 올라간다."""
        current_commit = self.commits[commit_hash]
        ancestor_hashes = []

        while current_commit.parents:
            parent_hash = current_commit.parents[0]
            ancestor_hashes.append(parent_hash)

            current_commit = self.commits[parent_hash]

        return ancestor_hashes

    def path(self, hash1, hash2):
        """hash1에서 hash2까지 이어지는 경로를 찾는다.
        두 체인이 처음 만나는 지점(LCA)을 기준으로 절반씩 이어붙인다."""
        chain1 = [hash1] + self.ancestors(hash1)
        chain2 = [hash2] + self.ancestors(hash2)

        lca = None
        for node in chain1:
            if node in chain2:
                lca = node
                break

        idx1 = chain1.index(lca)
        idx2 = chain2.index(lca)

        full_path = chain1[:idx1 + 1] + chain2[:idx2][::-1]

        return "Path: " + " -> ".join(full_path)

    def search(self, keyword=None, author=None):
        """키워드 또는 author로 커밋을 검색해 결과를 문자열로 반환한다."""
        if author:
            hashes = self.index.search_author(author)
        elif keyword:
            hashes = self.index.search_keyword(keyword)
        else:
            return "Invalid args."

        if not hashes:
            return "No matching commits."

        result = ""
        for h in hashes:
            c = self.commits[h]
            result += f"commit {c.hash} ({c.author}) [{c.created_on_branch}]\n{c.message}\n"
        return result