"""
shared/base_agent.py

Abstract base class. All agents inherit CLI parsing and the iteration loop.
Configure the LLM model version in .env (OPENAI_MODEL=gpt-3.5-turbo).
"""

import argparse
import os
from abc import ABC, abstractmethod
from itertools import islice

from shared.io_utils import read_jsonl


class BaseAgent(ABC):

    extra_args: list[tuple] = []

    @abstractmethod
    def process_task(self, task_id: str, prompt: str, args: argparse.Namespace) -> None:
        pass

    def build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=self.__class__.__name__)
        parser.add_argument("--prompts_file", required=True)
        parser.add_argument("--model",        default="gpt",
                            help="gpt | llama | bison | claude")
        parser.add_argument("--prompt_style", default="agent")
        parser.add_argument("--temperature",  type=float, default=1.0)
        parser.add_argument("--num_samples",  type=int,   default=1)
        parser.add_argument("--start",        type=int,   default=0)
        parser.add_argument("--end",          type=int,   default=343)
        for a, kw in self.extra_args:
            parser.add_argument(*a, **kw)
        return parser

    def run_cli(self) -> None:
        args = self.build_parser().parse_args()
        print(f"=== {self.__class__.__name__} ===")
        for k, v in vars(args).items():
            print(f"  {k}: {v}")
        print()
        for idx, obj in enumerate(
            islice(read_jsonl(args.prompts_file), args.start, args.end),
            start=args.start,
        ):
            task_id = str(obj.get("task_id", idx))
            prompt  = obj.get("prompt", "").strip()
            if not prompt:
                continue
            print(f"[{self.__class__.__name__}] task {task_id}")
            self.process_task(task_id=task_id, prompt=prompt, args=args)
