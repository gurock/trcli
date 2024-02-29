import re

def extract_last_words(input_string, max_characters=100):
    # Define delimiters for splitting words
    delimiters = [' ', '\t', ';', ':', '>']

    # Replace multiple consecutive delimiters with a single space
    regex_pattern = '|'.join(map(re.escape, delimiters))
    cleaned_string = re.sub(f'[{regex_pattern}]+', ' ', input_string.strip())

    # Split the cleaned string into words
    words = cleaned_string.split()

    # Extract the last words up to the maximum character limit
    extracted_words = []
    current_length = 0
    for word in reversed(words):
        if current_length + len(word) <= max_characters:
            extracted_words.append(word)
            current_length += len(word) + 1  # Add 1 for the space between words
        else:
            break

    # Reverse the extracted words to maintain the original order
    result = ' '.join(reversed(extracted_words))

    return result

# Example usage:
input_string = "This is a sample string; with multiple delimiters\tand characters> exceeding the limit."
result = extract_last_words(input_string, max_characters=2)
print(result)
