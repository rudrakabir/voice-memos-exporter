import unittest

from voice_memos_exporter import sanitize_filename


class SanitizeFilenameTests(unittest.TestCase):
    def test_replaces_path_separator(self):
        self.assertEqual(sanitize_filename("Work / personal"), "Work - personal")

    def test_replaces_colons_and_control_characters(self):
        self.assertEqual(sanitize_filename("Meeting: notes\npart 2"), "Meeting- notes-part 2")

    def test_normalizes_whitespace_and_trailing_dots(self):
        self.assertEqual(sanitize_filename("  Weekly   update...  "), "Weekly update")

    def test_uses_fallback_for_empty_titles(self):
        self.assertEqual(sanitize_filename(" / : "), "Untitled Recording")

    def test_preserves_valid_titles(self):
        self.assertEqual(sanitize_filename("Project kickoff"), "Project kickoff")


if __name__ == "__main__":
    unittest.main()
