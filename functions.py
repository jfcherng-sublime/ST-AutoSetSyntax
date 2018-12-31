import re


def snakeToCamel(snake, upper_first=False):
    # title-cased words
    words = [word.title() for word in snake.split('_')]

    if words and not upper_first:
        words[0] = words[0].lower()

    return ''.join(words)


def camelToSnake(camel):
    # first upper-cased camel
    camel = camel[0].upper() + camel[1:]

    return '_'.join(re.findall(r'[A-Z][^A-Z]*', camel)).lower()
