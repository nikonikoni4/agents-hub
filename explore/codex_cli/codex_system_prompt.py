"""Test-only script for validating a temporary Codex profile idea.

This file exists only to verify the feasibility of the following test setup:
1. launch Codex CLI with an isolated CODEX_HOME,
2. keep a minimal multi-turn conversation loop in Python,
3. observe how home-level instructions and project-level AGENTS.md interact.

It is not a production integration example and should not be treated as the
reference design for Codex CLI integration in agents-hub.
"""

import os
import subprocess
import sys


DEFAULT_CODEX_HOME = r"D:\desktop\软件开发\test-codex\role-nico"
DEFAULT_CODEX_COMMAND = r"C:\Users\15535\AppData\Roaming\npm\codex.cmd"


class CodexChatSession:
    def __init__(self, codex_home, codex_command=DEFAULT_CODEX_COMMAND, working_dir=None):
        self.codex_home = codex_home
        self.codex_command = codex_command
        self.working_dir = working_dir or os.getcwd()
        self.history = []

    def send(self, message):
        prompt = self._build_prompt(message)
        env = os.environ.copy()
        env["CODEX_HOME"] = self.codex_home

        result = subprocess.run(
            [self.codex_command, "exec", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=self.working_dir,
            check=False,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            raise RuntimeError(f"codex exec failed: {stderr}")

        reply = (result.stdout or "").strip()
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _build_prompt(self, message):
        if not self.history:
            return f"User: {message}"

        lines = []
        for item in self.history:
            role = item["role"].capitalize()
            lines.append(f"{role}: {item['content']}")
        lines.append(f"User: {message}")
        return "\n".join(lines)


def resolve_codex_home():
    return os.environ.get("CODEX_HOME_OVERRIDE", DEFAULT_CODEX_HOME)


def main():
    codex_home = resolve_codex_home()
    session = CodexChatSession(codex_home=codex_home)
    print(f"Using CODEX_HOME={codex_home}")
    print(f"Using working directory={session.working_dir}")
    print("Enter an empty line to exit.")

    while True:
        try:
            message = input("You> ").strip()
        except EOFError:
            break

        if not message:
            break

        reply = session.send(message)
        print(f"Codex> {reply}")


if __name__ == "__main__":
    main()
