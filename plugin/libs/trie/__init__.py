from typing import Dict, Generator, Iterable


class TrieNode:
    """
    A Trie/Prefix Tree is a kind of search tree used to provide quick lookup
    of words/patterns in a set of words. A basic Trie however has O(n^2) space complexity
    making it impractical in practice. It however provides O(max(search_string, length of
    longest word)) lookup time making it an optimal approach when space is not an issue.

    This file has been modified by @jfcherng to fit his own use.
    """

    def __init__(self) -> None:
        self.nodes: Dict[str, TrieNode] = dict()  # Mapping from char to TrieNode
        self.is_leaf = False

    def insert_many(self, words: Iterable[str]) -> None:
        """
        Inserts a list of words into the Trie
        :param words: list of string words
        :return: None
        """
        for word in words:
            self.insert(word)

    def insert(self, word: str) -> None:
        """
        Inserts a word into the Trie
        :param word: word to be inserted
        :return: None
        """
        curr = self
        for char in word:
            if char not in curr.nodes:
                curr.nodes[char] = TrieNode()
            curr = curr.nodes[char]
        curr.is_leaf = True

    def find(self, word: str) -> bool:
        """
        Tries to find word in a Trie
        :param word: word to look for
        :return: Returns True if word is found, False otherwise
        """
        curr = self
        for char in word:
            if char not in curr.nodes:
                return False
            curr = curr.nodes[char]
        return curr.is_leaf

    def find_prefixes(self, word: str) -> Generator[str, None, None]:
        """
        Tries to find word in a Trie
        :param word: word to look for
        :return: Returns True if word is found, False otherwise
        """
        prefix = ""
        curr = self
        for char in word:
            if char not in curr.nodes:
                break
            prefix += char
            curr = curr.nodes[char]
            if curr.is_leaf:
                yield prefix

    def delete(self, word: str) -> None:
        """
        Deletes a word in a Trie
        :param word: word to delete
        :return: None
        """

        def _delete(curr: TrieNode, word: str, index: int) -> bool:
            if index == len(word):
                # If word does not exist
                if not curr.is_leaf:
                    return False
                curr.is_leaf = False
                return len(curr.nodes) == 0
            char = word[index]
            char_node = curr.nodes.get(char)
            # If char not in current trie node
            if not char_node:
                return False
            # Flag to check if node can be deleted
            delete_curr = _delete(char_node, word, index + 1)
            if delete_curr:
                del curr.nodes[char]
                return len(curr.nodes) == 0
            return delete_curr

        _delete(self, word, 0)
