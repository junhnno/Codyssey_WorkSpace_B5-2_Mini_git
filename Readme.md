# Mini Git

Git의 커밋 그래프, 브랜치, 검색을 CLI로 구현한 미니 버전. 파일 내용 추적/네트워크/영속성은 구현하지 않는다.

## 실행

```
python main.py
```

`mini-git>` 프롬프트에서 명령을 반복 입력한다. 종료는 `exit` 또는 `quit`.

## 명령어

| 명령 | 설명 |
|---|---|
| `INIT <user_name>` | 저장소 초기화, main 브랜치 생성, HEAD 설정 |
| `BRANCH <branch_name>` | 현재 HEAD가 가리키는 커밋에서 새 브랜치 생성 |
| `SWITCH <branch_name>` | HEAD를 지정 브랜치로 이동 |
| `COMMIT <message>` | 현재 HEAD를 부모로 하는 새 커밋 생성 |
| `LOG` | 부모가 항상 자식보다 먼저 나오도록 전체 커밋 출력 |
| `LOG --sort-by=date\|author` | 지정 기준으로 재정렬해 출력 |
| `PATH <hash1> <hash2>` | 두 커밋 사이의 최단 경로 출력 |
| `ANCESTORS <hash>` | 해당 커밋의 모든 조상 출력 |
| `SEARCH <keyword>` | 메시지에 키워드가 포함된 커밋 검색 |
| `SEARCH --author=<name>` | 특정 author의 커밋 검색 |

명령어는 대소문자를 구분하지 않는다. 공백이 포함된 인자(메시지 등)는 따옴표로 감싼다. (예: `COMMIT "Fix login bug"`)

## 사용 예시

```
mini-git> INIT Alice
Initialized repository.
Current branch: main
Current user: Alice

mini-git> COMMIT "Initial commit"
[main a1b2c3d] Initial commit

mini-git> BRANCH feature
Created branch: feature

mini-git> SWITCH feature
Switched to branch: feature

mini-git> COMMIT "Add login feature"
[feature e4f5a6b] Add login feature

mini-git> SEARCH login
commit e4f5a6b (Alice) [feature]
Add login feature

mini-git> LOG --sort-by=author
commit a1b2c3d (Alice, 2026-09-28 12:00:00) [main]
Initial commit
commit e4f5a6b (Alice, 2026-09-28 12:00:05) [feature]
Add login feature

mini-git> PATH a1b2c3d e4f5a6b
Path: a1b2c3d -> e4f5a6b

mini-git> ANCESTORS e4f5a6b
Ancestors: a1b2c3d
```

## 설계 노트

**커밋 해시**
`message + author + timestamp + parents + commit_seq`를 합쳐 SHA-1 해시 후 앞 7자를 사용한다. 같은 세션에서 앞 7자가 겹치면 8자, 9자로 늘려가며 유일성을 보장한다. `commit_seq`(생성 순 카운터)를 섞기 때문에 짧은 시간에 동일한 메시지/작성자로 커밋해도 해시가 겹치지 않는다. 충돌 시 1자씩 늘려 재확인하는 루프는 실제로는 거의 실행되지 않는다 — SHA-1 앞 7자(28비트) 공간에서 같은 세션 내 커밋 수만큼의 충돌 확률은 무시할 수준이라, 평균적으로 O(1)에 가깝다. 타임스탬프 기반이라 실행할 때마다 해시 값 자체는 달라지며, 이는 의도된 동작이다(영속성/재현성이 요구사항이 아님). 다만 이 때문에 테스트 시 해시를 미리 하드코딩할 수 없고, 매 실행에서 출력된 해시를 그대로 다음 명령에 사용해야 한다.

**커밋 그래프가 DAG인 이유**
커밋은 `frozen=True` dataclass로 생성 후 수정이 불가능하고, 생성 시점에 이미 존재하는 부모 해시만 참조할 수 있다(존재하지 않는 커밋을 부모로 지정할 방법이 없음). 따라서 뒤에 생성된 커밋이 앞선 커밋을 가리킬 수만 있고 그 반대는 불가능해, 별도의 사이클 검사 없이도 구조적으로 사이클이 생길 수 없다.

**LOG의 부모-먼저 출력**
파이썬 dict은 3.7+부터 삽입 순서를 보존한다. 커밋은 항상 부모가 먼저 존재해야 생성 가능하므로, 생성 순서대로 `commits` dict에 쌓이는 것 자체가 이미 위상 정렬 순서(부모가 자식보다 먼저)를 만족한다. 따라서 `LOG`는 dict을 순서대로 순회하기만 하면 되고, 별도의 위상 정렬 알고리즘이 필요하지 않다.

**PATH**
커밋-부모 간선을 무방향 간선으로 간주하고, 두 방향(hash1→전체, hash2→전체) BFS로 모든 커밋까지의 거리를 구한 뒤, 두 거리의 합이 최단 거리와 일치하는 노드만 후보로 남겨 한 칸씩 최단 경로를 재구성한다. 최단 경로가 여러 개면 다음 노드 후보 중 사전순으로 가장 작은 해시를 선택해 나가는 방식으로, 전체 경로 문자열이 사전순으로 가장 작은 경로를 고른다. 도달 불가능하면 `No path`를 출력한다.

**ANCESTORS**
커밋은 부모를 0개 이상 가질 수 있으므로(향후 merge 커밋 확장을 고려), 부모 하나만 따라가지 않고 BFS로 모든 부모 쪽 경로를 전부 탐색해 중복 없이 조상 집합을 구한다.

**정렬 (merge_sort)**
`sorted()`/`list.sort()`를 쓰지 않고 병합정렬을 직접 구현했다(`sort_algo.py`). 분할정복 기반으로 모든 경우 시간복잡도 O(n log n), 공간복잡도 O(n)이며, merge 단계에서 동률일 때 왼쪽(원래 순서상 앞) 원소를 먼저 선택해 안정 정렬(stable sort)을 보장한다. `key` 함수를 받아 비교 기준(날짜, author 등)을 자유롭게 바꿀 수 있다.

**역색인 (InvertedIndex)**
`keyword -> [commit_hash]`, `author -> [commit_hash]` 두 개의 dict을 COMMIT 시점마다 갱신한다. SEARCH를 호출할 때마다 전체 커밋을 순회(O(n))하는 대신, 이미 만들어진 인덱스에서 바로 조회(평균 O(1))한다. 커밋 메시지는 소문자로 변환 후 공백 기준으로 분리(split)해 키워드로 저장하며, 검색도 동일하게 소문자로 정규화해 비교한다. 값은 `set`이 아니라 `list`를 써서, 커밋이 만들어진 순서(insertion order)대로 SEARCH 결과가 출력된다.

**확장성 / 성능 한계**
`INIT` ~ `COMMIT`, 인덱스 조회는 O(1) 근처지만, `PATH`/`ANCESTORS`는 호출할 때마다 무방향 인접 리스트를 `self.commits` 전체로부터 다시 만든다(O(V+E)). 커밋 수가 매우 커지면 이 재구성 비용이 누적된다 — 인접 리스트를 캐싱하고 COMMIT 시점에 증분 갱신하도록 바꾸면 개선할 수 있다. `LOG`도 정렬 옵션을 줄 때마다 O(n log n) 병합정렬을 매번 새로 수행한다. 역색인은 단일 dict 구조라 커밋/키워드 수가 매우 많아지면 메모리를 전부 차지하게 되는데, 이 과제 규모(세션 내 메모리 저장)에서는 별도의 분산/샤딩 없이 충분하다고 보고 설계했다.

## 에러 처리

잘못된 입력은 크래시 대신 표준화된 메시지로 처리한다.

- 인자 개수 부족 / 정의되지 않은 명령: `Invalid args.` / `Unknown command: <name>`
- 존재하지 않는 브랜치로 SWITCH: `Unknown branch: <name>`
- 존재하지 않는 커밋 해시(ANCESTORS/PATH): `Unknown commit: <hash>`
- 초기화 전 BRANCH/COMMIT: `Repository not initialized.`
- 이미 초기화된 상태에서 INIT: `Already initialized.` (재초기화를 막고 기존 상태를 그대로 유지한다 — 덮어쓰지 않음)
- 이미 있는 브랜치 이름으로 BRANCH: `Branch already exists: <name>`

`current_user`는 `INIT`에서 `HEAD`와 동시에 설정되고 그 외에는 값을 바꿀 방법이 없으므로, `commit()`에서 `HEAD is None`을 검사하는 것이 곧 `current_user`가 설정됐는지를 검사하는 것과 같다. 따로 `current_user`를 검사하는 코드가 없는 이유다.

## 파일 구성

- `main.py` — 엔트리 포인트
- `cli.py` — REPL, 명령 파싱(`--key=value` 옵션 분리 포함) 및 dispatch
- `graph.py` — `Commit`, `Repository` (커밋/브랜치 상태, 그래프 탐색 로직)
- `sort_algo.py` — 병합정렬 구현
- `index.py` — 역색인 (`InvertedIndex`)

## 알려진 제약

- 세션 메모리 상에서만 동작하며 영속성(파일 저장)은 없음
- 파일 내용 추적, 네트워크 통신 미구현
- 보너스 과제(Diff, Merge, 정렬 알고리즘 성능 비교) 미구현