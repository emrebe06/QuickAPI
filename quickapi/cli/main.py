import argparse

from quickapi.cli import commands


def main(argv=None):
    parser = argparse.ArgumentParser(prog="quickapi")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a QuickAPI app, e.g. quickapi run main:app --host 0.0.0.0 --port 8000")
    run_parser.add_argument("target")
    run_parser.add_argument("--host", default="0.0.0.0")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.add_argument("--reload", action="store_true")
    run_parser.add_argument("--no-access-log", action="store_true")

    serve_parser = sub.add_parser("serve", help="Alias for run")
    serve_parser.add_argument("target")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--reload", action="store_true")
    serve_parser.add_argument("--no-access-log", action="store_true")

    dev_parser = sub.add_parser("dev")
    dev_parser.add_argument("path")
    dev_parser.add_argument("--host", default="127.0.0.1")
    dev_parser.add_argument("--port", type=int, default=8080)
    dev_parser.add_argument("--no-access-log", action="store_true")

    docs_parser = sub.add_parser("docs")
    docs_parser.add_argument("path", nargs="?", default="examples/basic_api/main.py")
    docs_parser.add_argument("--host", default="127.0.0.1")
    docs_parser.add_argument("--port", type=int, default=8080)
    docs_parser.add_argument("--no-access-log", action="store_true")

    routes_parser = sub.add_parser("routes")
    routes_parser.add_argument("path", nargs="?", default="examples/basic_api/main.py")

    bench_parser = sub.add_parser("bench")
    bench_parser.add_argument("path", nargs="?", default="examples/basic_api/main.py")
    bench_parser.add_argument("--route", default="/ping")
    bench_parser.add_argument("--iterations", type=int, default=1000)

    new_parser = sub.add_parser("new")
    new_parser.add_argument("name")

    args = parser.parse_args(argv)
    if args.command == "run":
        return commands.run(args.target, args.host, args.port, access_log=not args.no_access_log, reload=args.reload)
    if args.command == "serve":
        return commands.serve(args.target, args.host, args.port, access_log=not args.no_access_log, reload=args.reload)
    if args.command == "dev":
        return commands.dev(args.path, args.host, args.port, access_log=not args.no_access_log)
    if args.command == "docs":
        return commands.docs(args.path, args.host, args.port, access_log=not args.no_access_log)
    if args.command == "routes":
        return commands.routes(args.path)
    if args.command == "bench":
        return commands.bench(args.path, args.route, args.iterations)
    if args.command == "new":
        return commands.new(args.name)
    return None


if __name__ == "__main__":
    main()
