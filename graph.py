from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
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
        """해당 커밋에서 도달 가능한 모든 조상 커밋의 hash를 빠짐없이 반환한다.
        커밋은 부모를 0개 이상 가질 수 있으므로, 부모 하나만 따라가지 않고
        BFS로 모든 부모 쪽 경로를 전부 탐색한다."""
        visited = set()
        queue = deque(self.commits[commit_hash].parents)
        ancestor_hashes = []

        while queue:
            current_hash = queue.popleft()
            if current_hash in visited:
                continue
            visited.add(current_hash)
            ancestor_hashes.append(current_hash)
            queue.extend(self.commits[current_hash].parents)

        return ancestor_hashes

    def _build_undirected_adjacency(self):
        """커밋-부모 연결을 방향 없는 간선으로 간주한 인접 리스트를 만든다.
        PATH의 최단 경로 탐색에서 쓰인다."""
        adjacency = {h: [] for h in self.commits}
        for c in self.commits.values():
            for parent_hash in c.parents:
                adjacency[c.hash].append(parent_hash)
                adjacency[parent_hash].append(c.hash)
        return adjacency

    def _bfs_distances(self, adjacency, start):
        """start로부터 각 커밋까지의 최단 거리(간선 수)를 BFS로 계산해 반환한다."""
        distances = {start: 0}
        queue = deque([start])

        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in distances:
                    distances[neighbor] = distances[current] + 1
                    queue.append(neighbor)

        return distances

    def path(self, hash1, hash2):
        """hash1과 hash2 사이의 최단 경로를 찾는다.
        커밋-부모 연결을 무방향 간선으로 보고 BFS로 최단 거리를 구하고,
        최단 경로가 여러 개면 사전순으로 가장 작은 경로를 선택한다."""
        adjacency = self._build_undirected_adjacency()
        dist_from_1 = self._bfs_distances(adjacency, hash1)
        dist_from_2 = self._bfs_distances(adjacency, hash2)

        if hash2 not in dist_from_1:
            return "No path"

        total_distance = dist_from_1[hash2]

        path_nodes = [hash1]
        current = hash1

        while current != hash2:
            remaining = total_distance - dist_from_1[current] - 1

            # 최단 경로 위에 있는 다음 후보들을 전부 모은다.
            candidates = []
            for neighbor in adjacency[current]:
                if (dist_from_1.get(neighbor) == dist_from_1[current] + 1
                        and dist_from_2.get(neighbor) == remaining):
                    candidates.append(neighbor)

            # sorted()/list.sort() 없이, 후보 중 사전순으로 가장 작은 것을 직접 고른다.
            next_node = candidates[0]
            for candidate in candidates[1:]:
                if candidate < next_node:
                    next_node = candidate

            path_nodes.append(next_node)
            current = next_node

        return "Path: " + " -> ".join(path_nodes)

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