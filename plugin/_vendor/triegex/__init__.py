import collections

__all__ = ('Triegex',)

OR = r'|'

# regex below matches nothing https://stackoverflow.com/a/940840/2183102. We
# use '~' to ensure it comes last when lexicographically sorted:
# max(string.printable) is '~'
NOTHING = r'~^(?#match nothing)'
GROUP = r'(?:{0})'
WORD_BOUNDARY = r'\b'


class TriegexNode:

    def __init__(self, char: str, end: bool, *childrens):
        self.char = char if char is not None else ''
        self.end = end
        self.childrens = {children.char: children for children in childrens}

    def __iter__(self):
        return iter(sorted(self.childrens.values(), key=lambda x: x.char))

    def __len__(self):
        return len(self.childrens)

    def __repr__(self):
        return f'<TriegexNode: \'{self.char}\' end={self.end}>'

    def __contains__(self, key):
        return key in self.childrens

    def __getitem__(self, key):
        return self.childrens[key]

    def __delitem__(self, key):
        del self.childrens[key]

    def to_regex(self):
        stack = [self]
        ready = []
        waiting = []

        while stack:
            waiting.append(stack.pop())
            stack.extend(waiting[-1])

        while waiting:
            node = waiting.pop()
            result = node.char

            if node.end:
                result += WORD_BOUNDARY

            # if there is only one children, we can safely concatenate chars
            # withoug nesting
            elif len(node) == 1:
                result += ready.pop()

            elif len(node) > 1:
                result += GROUP.format(OR.join(reversed(
                    [ready.pop() for _ in node]
                )))

            ready.append(result)
        return ready[-1]


class Triegex(collections.MutableSet):

    _root = None

    def __init__(self, *words):
        """
        Trigex constructor.
        """

        # make sure we match nothing when no words are added
        self._root = TriegexNode(None, False, TriegexNode(NOTHING, False))

        for word in words:
            self.add(word)

    def add(self, word: str):
        current = self._root
        for letter in word[:-1]:
            current = current.childrens.setdefault(letter,
                                                   TriegexNode(letter, False))
        # this will ensure that we correctly match the word boundary
        current.childrens[word[-1]] = TriegexNode(word[-1], True)

    def to_regex(self):
        r"""
            Produce regular expression that will match each word in the
        internal trie.

        >>> t = Triegex('foo', 'bar', 'baz')
        >>> t.to_regex()
        '(?:ba(?:r\\b|z\\b)|foo\\b|~^(?#match nothing))'
        """
        return self._root.to_regex()

    def _traverse(self):
        stack = [self._root]
        current = self._root
        while stack:
            yield current
            current = stack.pop()
            stack.extend(current.childrens.values())

    def __iter__(self):
        paths = {self._root.char: []}
        for node in self._traverse():
            for children in node:
                paths[children.char] = [node.char] + paths[node.char]
                if children.end:
                    char = children.char
                    yield ''.join(reversed([char] + paths[char]))

    def __len__(self):
        return sum(1 for _ in self.__iter__())

    def __contains__(self, word):
        current = self._root
        for char in word:
            if char not in current:
                return False
            current = current[char]
        return True and current.end  # word has to end with the last char

    def discard(self, word):
        to_delete = [self._root]
        current = self._root
        for char in word:
            if char not in current:
                return
            current = current[char]
            to_delete.append(current)
        if not to_delete[-1].end:
            return
        while len(to_delete) > 1:
            node = to_delete.pop()
            if len(node) == 0:
                del to_delete[-1][node.char]
            return
