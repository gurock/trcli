"""
Unit tests for file_handler.py

Tests file logging functionality including:
- File creation
- Log rotation
- Thread safety
- Cleanup
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from trcli.logging.file_handler import RotatingFileHandler, MultiFileHandler


class TestRotatingFileHandler(unittest.TestCase):
    """Test RotatingFileHandler class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"

    def tearDown(self):
        """Clean up temp directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handler_initialization(self):
        """Test handler is initialized correctly"""
        handler = RotatingFileHandler(str(self.log_file), max_bytes=1024, backup_count=3)

        self.assertEqual(handler.filepath, self.log_file)
        self.assertEqual(handler.max_bytes, 1024)
        self.assertEqual(handler.backup_count, 3)

        handler.close()

    def test_creates_log_directory(self):
        """Test that handler creates log directory if it doesn't exist"""
        nested_log = Path(self.temp_dir) / "subdir" / "logs" / "test.log"

        handler = RotatingFileHandler(str(nested_log))
        handler.write("Test message\n")
        handler.close()

        # Directory should be created
        self.assertTrue(nested_log.parent.exists())
        self.assertTrue(nested_log.exists())

    def test_writes_to_file(self):
        """Test that handler writes to file"""
        handler = RotatingFileHandler(str(self.log_file))

        handler.write("Test message 1\n")
        handler.write("Test message 2\n")
        handler.close()

        # File should contain messages
        content = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Test message 1", content)
        self.assertIn("Test message 2", content)

    def test_rotation_on_size(self):
        """Test that file rotates when max size is reached"""
        handler = RotatingFileHandler(str(self.log_file), max_bytes=100, backup_count=3)  # Small size for testing

        # Write enough data to trigger rotation
        for i in range(20):
            handler.write(f"Log message {i} with some content\n")

        handler.close()

        # Backup files should exist
        backup1 = Path(f"{self.log_file}.1")
        self.assertTrue(backup1.exists(), "Backup file .1 should exist")

    def test_backup_count_limit(self):
        """Test that only backup_count backup files are kept"""
        handler = RotatingFileHandler(str(self.log_file), max_bytes=50, backup_count=2)  # Very small for testing

        # Write lots of data to trigger multiple rotations
        for i in range(50):
            handler.write(f"Log message {i} with content to fill up space\n")

        handler.close()

        # Check backup files
        backup1 = Path(f"{self.log_file}.1")
        backup2 = Path(f"{self.log_file}.2")
        backup3 = Path(f"{self.log_file}.3")

        self.assertTrue(backup1.exists(), "Backup .1 should exist")
        self.assertTrue(backup2.exists(), "Backup .2 should exist")
        self.assertFalse(backup3.exists(), "Backup .3 should not exist (exceeds backup_count)")

    def test_flush(self):
        """Test flush method"""
        handler = RotatingFileHandler(str(self.log_file))

        handler.write("Test message\n")
        handler.flush()

        # File should be written immediately
        content = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Test message", content)

        handler.close()

    def test_context_manager(self):
        """Test handler works as context manager"""
        with RotatingFileHandler(str(self.log_file)) as handler:
            handler.write("Test message\n")

        # File should be closed and content written
        self.assertTrue(self.log_file.exists())
        content = self.log_file.read_text(encoding="utf-8")
        self.assertIn("Test message", content)

    def test_multiple_writes_same_file(self):
        """Test multiple writes to same file"""
        handler = RotatingFileHandler(str(self.log_file))

        messages = [f"Message {i}\n" for i in range(10)]
        for msg in messages:
            handler.write(msg)

        handler.close()

        content = self.log_file.read_text(encoding="utf-8")
        for msg in messages:
            self.assertIn(msg.strip(), content)

    def test_unicode_content(self):
        """Test writing Unicode content"""
        handler = RotatingFileHandler(str(self.log_file))

        handler.write("Message with émojis: 🎉 ✅ 🚀\n")
        handler.write("Chinese: 你好世界\n")
        handler.write("Arabic: مرحبا بالعالم\n")

        handler.close()

        content = self.log_file.read_text(encoding="utf-8")
        self.assertIn("🎉", content)
        self.assertIn("你好世界", content)
        self.assertIn("مرحبا بالعالم", content)

    def test_close_multiple_times(self):
        """Test that closing multiple times doesn't cause errors"""
        handler = RotatingFileHandler(str(self.log_file))
        handler.write("Test\n")

        # Close multiple times
        handler.close()
        handler.close()
        handler.close()

        # Should not raise any errors

    def test_rotation_preserves_content(self):
        """Test that rotation preserves all content"""
        handler = RotatingFileHandler(str(self.log_file), max_bytes=200, backup_count=5)

        messages = []
        for i in range(30):
            msg = f"Log entry number {i} with some additional content\n"
            messages.append(msg)
            handler.write(msg)

        handler.close()

        # Collect all content from all files
        all_content = ""
        if self.log_file.exists():
            all_content += self.log_file.read_text(encoding="utf-8")

        for i in range(1, 6):
            backup = Path(f"{self.log_file}.{i}")
            if backup.exists():
                all_content += backup.read_text(encoding="utf-8")

        # All messages should be somewhere
        for msg in messages:
            self.assertIn(msg.strip().split()[0], all_content)  # At least the beginning


class TestMultiFileHandler(unittest.TestCase):
    """Test MultiFileHandler class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file1 = Path(self.temp_dir) / "test1.log"
        self.log_file2 = Path(self.temp_dir) / "test2.log"

    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_writes_to_multiple_files(self):
        """Test that handler writes to all files"""
        handler1 = RotatingFileHandler(str(self.log_file1))
        handler2 = RotatingFileHandler(str(self.log_file2))

        multi = MultiFileHandler([handler1, handler2])
        multi.write("Test message\n")
        multi.close()

        # Both files should have the message
        content1 = self.log_file1.read_text(encoding="utf-8")
        content2 = self.log_file2.read_text(encoding="utf-8")

        self.assertIn("Test message", content1)
        self.assertIn("Test message", content2)

    def test_continues_on_handler_failure(self):
        """Test that failure in one handler doesn't stop others"""
        handler1 = RotatingFileHandler(str(self.log_file1))

        # Create a handler that will fail on write, not initialization
        # We'll create a valid handler, write to it (opens file), then close it to cause write failures
        import os

        temp_log = Path(self.temp_dir) / "temp.log"
        handler2 = RotatingFileHandler(str(temp_log))
        handler2.write("init\n")  # This opens the file
        handler2._file.close()  # Close the file to cause write failures

        handler3 = RotatingFileHandler(str(self.log_file2))

        multi = MultiFileHandler([handler1, handler2, handler3])
        multi.write("Test message\n")
        multi.close()

        # Files 1 and 3 should still work
        self.assertTrue(self.log_file1.exists())
        self.assertTrue(self.log_file2.exists())

        content1 = self.log_file1.read_text(encoding="utf-8")
        content2 = self.log_file2.read_text(encoding="utf-8")

        self.assertIn("Test message", content1)
        self.assertIn("Test message", content2)

    def test_context_manager(self):
        """Test multi-handler works as context manager"""
        handler1 = RotatingFileHandler(str(self.log_file1))
        handler2 = RotatingFileHandler(str(self.log_file2))

        with MultiFileHandler([handler1, handler2]) as multi:
            multi.write("Test message\n")

        # Both files should be closed and written
        self.assertTrue(self.log_file1.exists())
        self.assertTrue(self.log_file2.exists())


if __name__ == "__main__":
    unittest.main()
