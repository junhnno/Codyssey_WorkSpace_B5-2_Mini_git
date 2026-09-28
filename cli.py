import shlex
from graph import Repository

REQUIRED_POSITIONAL = {
    'INIT': 1,
    'BRANCH': 1,
    'SWITCH': 1,
    'COMMIT': 1,
    'LOG': 0,
    'PATH': 2,
    'ANCESTORS': 1,
    'SEARCH': 0,
}


def parse_options(args):
    """--key=value 형태의 옵션들을 분리해서 dict로 반환하고,
    옵션이 아닌 일반 인자들은 리스트로 따로 반환한다."""
    options = {}
    positional = []
    for arg in args:
        if arg.startswith('--') and '=' in arg:
            key, value = arg[2:].split('=', 1)
            options[key] = value
        else:
            positional.append(arg)
    return positional, options


def run():
    """REPL 루프. 사용자 입력을 받아 명령을 파싱하고 Repository에 위임한다."""
    repo = Repository()

    while True:
        try:
            raw = input("mini-git> ").strip()
        except EOFError:
            break

        if not raw:
            continue

        tokens = shlex.split(raw)
        command = tokens[0].upper()
        args = tokens[1:]

        if command in ('EXIT', 'QUIT'):
            break

        if command not in REQUIRED_POSITIONAL:
            print(f"Unknown command: {command}")
            continue

        positional, options = parse_options(args)

        # SEARCH는 키워드(positional) 또는 --author 둘 중 하나는 있어야 한다.
        if command == 'SEARCH':
            if not positional and 'author' not in options:
                print("Invalid args.")
                continue
        elif len(positional) < REQUIRED_POSITIONAL[command]:
            print("Invalid args.")
            continue

        try:
            if command == 'INIT':
                print(repo.init(positional[0]))
            elif command == 'BRANCH':
                print(repo.branch(positional[0]))
            elif command == 'SWITCH':
                print(repo.switch(positional[0]))
            elif command == 'COMMIT':
                print(repo.commit(positional[0]))
            elif command == 'LOG':
                print(repo.log(sort_by=options.get('sort-by')))
            elif command == 'PATH':
                print(repo.path(positional[0], positional[1]))
            elif command == 'ANCESTORS':
                ancestor_hashes = repo.ancestors(positional[0])
                print("Ancestors: " + " -> ".join(ancestor_hashes))
            elif command == 'SEARCH':
                if 'author' in options:
                    print(repo.search(author=options['author']))
                else:
                    print(repo.search(keyword=positional[0]))
        except KeyError as e:
            print(f"Unknown commit: {e.args[0]}")