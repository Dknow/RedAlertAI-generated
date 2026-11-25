# -*- coding: utf-8 -*-
"""启动入口：可直接运行，也可被 PyInstaller 打包为 exe。"""
import os
import sys
import traceback

os.environ.setdefault("SDL_VIDEO_CENTERED", "1")


def _log_crash():
    try:
        base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else \
            os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "crash.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n===== %s =====\n" % __import__("datetime").datetime.now().isoformat())
            f.write(traceback.format_exc())
        return path
    except Exception:
        return None


def main():
    try:
        from game.app import Game
        Game().run()
    except Exception:
        p = _log_crash()
        if not getattr(sys, "frozen", False):
            traceback.print_exc()
        if p:
            print("崩溃日志已写入:", p)
        raise


if __name__ == "__main__":
    main()
