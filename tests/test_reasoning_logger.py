import json
import unittest
from pathlib import Path
from reasoning_logger import ReasoningLogger
from config import Config

class TestReasoningLogger(unittest.TestCase):
    def setUp(self):
        self.test_traces_dir = Path("test_traces")
        self.config = Config(
            enable_traces=True,
            traces_dir=self.test_traces_dir
        )
        self.logger = ReasoningLogger(self.config)

    def tearDown(self):
        # Clean up test traces
        if self.test_traces_dir.exists():
            for f in self.test_traces_dir.glob("*.json"):
                f.unlink()
            self.test_traces_dir.rmdir()

    def test_session_creation(self):
        self.logger.start_session(metadata={"test": "data"})
        self.assertIsNotNone(self.logger.session_id)
        self.assertTrue(self.logger.current_trace_file.exists())
        
        with open(self.logger.current_trace_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["session_id"], self.logger.session_id)
            self.assertEqual(data["events"][0]["event"], "session_start")
            self.assertEqual(data["events"][0]["metadata"]["test"], "data")

    def test_log_events(self):
        self.logger.start_session()
        self.logger.log_user_message("Hello")
        self.logger.log_llm_response("Hi there", [{"name": "tool_x", "arguments": {}}], {"total_tokens": 10})
        self.logger.log_tool_result("tool_x", {}, "success")
        
        with open(self.logger.current_trace_file, "r") as f:
            data = json.load(f)
            events = data["events"]
            self.assertEqual(len(events), 4)  # start + user + llm + tool
            self.assertEqual(events[1]["event"], "user_message")
            self.assertEqual(events[1]["content"], "Hello")
            self.assertEqual(events[2]["event"], "llm_response")
            self.assertEqual(events[3]["event"], "tool_result")

if __name__ == "__main__":
    unittest.main()
