import unittest
from unittest.mock import patch

from tests.explore.codex_system_prompt import (
    DEFAULT_CODEX_COMMAND,
    CodexChatSession,
    resolve_codex_home,
)


class CodexChatSessionTests(unittest.TestCase):
    def test_default_codex_command_uses_explicit_windows_launcher(self):
        self.assertEqual(
            DEFAULT_CODEX_COMMAND,
            r"C:\Users\15535\AppData\Roaming\npm\codex.cmd",
        )

    def test_session_defaults_working_directory_to_current_process_directory(self):
        with patch(
            "tests.explore.codex_system_prompt.os.getcwd",
            return_value=r"D:\desktop\软件开发\agents-hub",
        ):
            session = CodexChatSession(codex_home=r"D:\desktop\软件开发\test-codex")

        self.assertEqual(session.working_dir, r"D:\desktop\软件开发\agents-hub")

    def test_resolve_codex_home_falls_back_to_default_test_profile(self):
        with patch.dict("tests.explore.codex_system_prompt.os.environ", {}, clear=False):
            self.assertEqual(resolve_codex_home(), r"D:\desktop\软件开发\test-codex")

    def test_resolve_codex_home_prefers_override_environment_variable(self):
        with patch.dict(
            "tests.explore.codex_system_prompt.os.environ",
            {"CODEX_HOME_OVERRIDE": r"D:\tmp\custom-codex-home"},
            clear=False,
        ):
            self.assertEqual(resolve_codex_home(), r"D:\tmp\custom-codex-home")

    @patch("tests.explore.codex_system_prompt.subprocess.run")
    def test_send_uses_codex_home_and_keeps_multi_turn_history(self, mock_run):
        mock_run.side_effect = [
            type("Result", (), {"stdout": "assistant turn 1", "returncode": 0})(),
            type("Result", (), {"stdout": "assistant turn 2", "returncode": 0})(),
        ]

        session = CodexChatSession(
            codex_home=r"D:\desktop\软件开发\test-codex",
            codex_command=DEFAULT_CODEX_COMMAND,
            working_dir=r"D:\desktop\软件开发\agents-hub",
        )

        first_reply = session.send("你好，你是谁？")
        second_reply = session.send("你的工作是什么？")

        self.assertEqual(first_reply, "assistant turn 1")
        self.assertEqual(second_reply, "assistant turn 2")
        self.assertEqual(len(session.history), 4)
        self.assertEqual(session.history[0]["role"], "user")
        self.assertEqual(session.history[1]["role"], "assistant")
        self.assertEqual(session.history[2]["content"], "你的工作是什么？")

        first_call = mock_run.call_args_list[0]
        second_call = mock_run.call_args_list[1]

        first_env = first_call.kwargs["env"]
        second_env = second_call.kwargs["env"]
        self.assertEqual(first_env["CODEX_HOME"], r"D:\desktop\软件开发\test-codex")
        self.assertEqual(second_env["CODEX_HOME"], r"D:\desktop\软件开发\test-codex")
        self.assertEqual(first_call.kwargs["cwd"], r"D:\desktop\软件开发\agents-hub")
        self.assertEqual(second_call.kwargs["cwd"], r"D:\desktop\软件开发\agents-hub")

        first_prompt = first_call.args[0][-1]
        second_prompt = second_call.args[0][-1]
        self.assertIn("你好，你是谁？", first_prompt)
        self.assertIn("assistant turn 1", second_prompt)
        self.assertIn("你的工作是什么？", second_prompt)


if __name__ == "__main__":
    unittest.main()
