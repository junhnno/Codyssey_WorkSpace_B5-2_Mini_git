def merge_sort(items, key):
    """병합정렬. key는 원소 하나를 받아 비교에 쓸 값을 뽑아내는 함수.
    안정 정렬: merge 시 값이 같으면 왼쪽(원래 앞쪽) 원소를 먼저 선택한다."""
    if len(items) <= 1:
        return items

    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)

    return _merge(left, right, key)


def _merge(left, right, key):
    """정렬된 두 리스트 left, right를 하나의 정렬된 리스트로 합친다."""
    result = []
    i, j = 0, 0

    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result