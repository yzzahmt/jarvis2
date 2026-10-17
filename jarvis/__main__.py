"""python -m jarvis [text|serve|voice|status]"""
import sys


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "text"
    if mode == "serve":
        import uvicorn
        from . import config
        from .controller.app import create_app
        api = config.load("settings").get("api", {})
        uvicorn.run(create_app(), host=api.get("host", "127.0.0.1"), port=api.get("port", 8765))
        return
    if mode == "voice":
        from .voice.loop import main as voice_main
        return voice_main()
    from .core import Jarvis
    j = Jarvis()
    if mode == "status":
        print(j.do_status(None))
        return
    print("JARVIS metin modu. Çıkmak için 'çık'.")
    while True:
        try:
            line = input("sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("çık", "cik", "exit", "quit"):
            break
        if line:
            print("jarvis>", j.handle(line, say=lambda m: print("jarvis>", m)))


if __name__ == "__main__":
    main()
