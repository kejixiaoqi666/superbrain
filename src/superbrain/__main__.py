"""超脑 SuperBrain 命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys


def main() -> None:
    ap = argparse.ArgumentParser(prog="superbrain", description="超脑 SuperBrain 自主智能体")
    ap.add_argument("message", nargs="?", help="单条消息（缺省进入交互模式）")
    ap.add_argument("--state", action="store_true", help="查看内在状态（需求/情绪/记忆）")
    ap.add_argument("--remember", metavar="内容", help="写入一条记忆")
    ap.add_argument("--recall", metavar="查询", help="检索记忆")
    ap.add_argument("--db", metavar="路径", help="记忆库路径")
    args = ap.parse_args()

    from superbrain import SuperBrainAgent, from_env

    try:
        llm = from_env()
    except RuntimeError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        print("   请设置 SUPERBRAIN_LLM_KEY 或 DPDNS_DEEPSEEK_API_KEY", file=sys.stderr)
        sys.exit(1)

    agent = SuperBrainAgent(llm)

    if args.state:
        print(json.dumps(agent.state_snapshot(), ensure_ascii=False, indent=2))
        return

    if args.remember:
        node = agent.remember(args.remember)
        print(f"✅ 已记忆：{node.content[:60]}")
        return

    if args.recall:
        hits = agent.recall(args.recall)
        if not hits:
            print("（无命中）")
        for node, score, why in hits:
            print(f"  [{why}] {node.content[:100]}  (置信 {node.confidence:.2f})")
        return

    if args.message:
        print(agent.chat(args.message))
        return

    # 交互模式
    print("🧠 超脑 SuperBrain 已启动（输入 exit 退出，state 看内在状态）")
    while True:
        try:
            line = input("\n你> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        if line.lower() == "state":
            print(json.dumps(agent.state_snapshot(), ensure_ascii=False, indent=2))
            continue
        print(f"\n超脑> {agent.chat(line)}")
    agent.close()


if __name__ == "__main__":
    main()
