def quick_sort(numbers):
    """Return a new sorted list using the quick sort algorithm."""
    if len(numbers) <= 1:
        return numbers

    pivot = numbers[len(numbers) // 2]
    left = [value for value in numbers if value < pivot]
    middle = [value for value in numbers if value == pivot]
    right = [value for value in numbers if value > pivot]

    return quick_sort(left) + middle + quick_sort(right)


if __name__ == "__main__":
    data = [42, 7, 19, 3, 7, 88, 23, 1, 54]
    sorted_data = quick_sort(data)

    print("Original:", data)
    print("Sorted:  ", sorted_data)
