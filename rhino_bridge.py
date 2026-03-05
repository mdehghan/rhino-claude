# Rhino IronPython 2.7 localhost bridge to run trusted local script files by name
#
# POST http://127.0.0.1:5123/op
# Body:
# {
#   "op": "run_script",
#   "args": { "script": "make_ball.py", "params": {"x":0,"y":0,"z":0,"r":8} }
# }

import os
import json
import threading

import Rhino
import scriptcontext as sc
import System

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from SocketServer import ThreadingMixIn

# ----------------------------
# Config
# ----------------------------
HOST = "127.0.0.1"
PORT = 5123

_server = None
_server_thread = None


def _is_safe_script_name(name):
    # Only allow simple filenames like "foo.py"
    if not name or not name.endswith(".py"):
        return False
    if "/" in name or "\\" in name:
        return False
    if ".." in name:
        return False
    if ":" in name:
        return False
    return True

def _run_on_ui_thread(fn, timeout_seconds=60.0):
    """
    Execute fn() on Rhino's UI thread and return (result, error_string_or_None).
    """
    done = threading.Event()
    out = {"result": None, "error": None}

    def _wrapped():
        try:
            out["result"] = fn()
        except Exception as e:
            out["error"] = "{}: {}".format(type(e).__name__, e)
        finally:
            done.set()

    Rhino.RhinoApp.InvokeOnUiThread(System.Action(_wrapped))

    if not done.wait(timeout_seconds):
        return None, "Timeout waiting for UI thread"
    return out["result"], out["error"]

def _load_script_namespace(code):
    """
    Loads a python code into an isolated namespace and returns it.
    Script must define main(doc, params).
    """

    ns = {}
    compiled = compile(code, "test.py", "exec")
    exec(compiled, ns, ns)

    main = ns.get("main", None)
    if not callable(main):
        raise Exception("Script must define callable main(doc, params)")
    return ns

def _op_run_script(args):
    py_code_script = args.get("script", "")
    params = args.get("params", {}) or {}

    # Load the script off the request thread (no Rhino doc edits here)
    ns = _load_script_namespace(py_code_script)
    main = ns["main"]

    # Run main(doc, params) on Rhino UI thread
    def _do():
        result = main(sc.doc, params)
        try:
            sc.doc.Views.Redraw()
        except:
            pass
        return result

    result, err = _run_on_ui_thread(_do, timeout_seconds=120.0)
    if err:
        return {"ok": False, "error": err}
    return {"ok": True, "result": result}

OPS = {
    "run_script": _op_run_script,
}


# ----------------------------
# HTTP server
# ----------------------------
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class BridgeHandler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload)
        try:
            body_bytes = body.encode("utf-8")
        except:
            body_bytes = body

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def do_POST(self):
        if self.path != "/run_script":
            return self._send(404, {"ok": False, "error": "Not found"})

        try:
            length = int(self.headers.getheader("Content-Length") or "0")
            raw = self.rfile.read(length)
            try:
                raw = raw.decode("utf-8")
            except:
                pass
            req = json.loads(raw)
            args = req.get("args", {}) or {}
        except Exception as e:
            return self._send(400, {"ok": False, "error": "Bad JSON: {}".format(e)})


        try:
            result = _op_run_script(args)
            return self._send(200, result)
        except Exception as e:
            return self._send(500, {"ok": False, "error": e})

    def log_message(self, fmt, *args):
        pass


def start_bridge(port=PORT):
    global _server, _server_thread
    if _server is not None:
        print("Bridge already running.")
        return

    _server = ThreadingHTTPServer((HOST, port), BridgeHandler)

    def _serve():
        try:
            _server.serve_forever()
        except Exception as e:
            print("Bridge stopped: {}".format(e))

    _server_thread = threading.Thread(target=_serve)
    _server_thread.setDaemon(True)
    _server_thread.start()

    print("Rhino IronPython bridge running:")
    print("  URL: http://{}:{}/op".format(HOST, port))
    print("  Op: run_script")


def stop_bridge():
    global _server, _server_thread
    if _server is None:
        print("Bridge not running.")
        return
    try:
        _server.shutdown()
    except:
        pass
    try:
        _server.server_close()
    except:
        pass
    _server = None
    _server_thread = None
    print("Bridge stopped.")


# Auto-start
start_bridge()
