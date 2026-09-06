"""HTTP decoy: fake internal portal with admin login, fake .env and fake
passwords backup file (canary token files). Every request is logged."""

import logging

from flask import Flask, Response, request

from decoys.base_decoy import BaseDecoy

PAGE_HOME = ("<html><head><title>Acme Corp - Internal Portal</title></head><body>"
             "<h1>Acme Corp Internal Portal</h1><p>Authorized employees only.</p>"
             "<ul><li><a href='/admin'>Admin Console</a></li></ul></body></html>")

PAGE_ADMIN_LOGIN = ("<html><head><title>Admin Login</title></head><body>"
                    "<h2>Admin Console</h2>"
                    "<form method='POST' action='/admin'>"
                    "<input name='username' placeholder='Username'><br>"
                    "<input name='password' type='password' placeholder='Password'><br>"
                    "<button>Login</button></form></body></html>")

PAGE_ADMIN_FAIL = ("<html><body><h3>Login failed: invalid credentials</h3>"
                   "<a href='/admin'>Back</a></body></html>")

PAGE_404 = ("<html><head><title>404 Not Found</title></head><body>"
            "<center><h1>404 Not Found</h1><hr>nginx/1.18.0 (Ubuntu)</center>"
            "</body></html>")


class HTTPDecoy(BaseDecoy):
    DECOY_NAME = "http"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = self._build_app()

    def run(self):
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        self.app.run(host=self.host, port=self.port, threaded=True,
                     use_reloader=False)

    def _addr(self):
        return (request.remote_addr or "unknown",
                request.environ.get("REMOTE_PORT", 0))

    def _emit_request(self, event_type, data=None):
        data = dict(data or {})
        data.setdefault("method", request.method)
        data.setdefault("path", request.path)
        data["user_agent"] = request.headers.get("User-Agent", "")
        raw = f"{request.method} {request.full_path} form={dict(request.form)}"
        self.emit(self._addr(), event_type, data, raw)

    def _build_app(self):
        app = Flask("http-decoy")

        @app.after_request
        def fake_server(resp):
            resp.headers["Server"] = "nginx/1.18.0 (Ubuntu)"
            return resp

        @app.route("/")
        def index():
            self._emit_request("http_request")
            return PAGE_HOME

        @app.route("/admin", methods=["GET", "POST"])
        def admin():
            if request.method == "POST":
                u = request.form.get("username", "")
                p = request.form.get("password", "")
                canary = bool(self.canaries and
                              self.canaries.is_canary_credential(u, p))
                self._emit_request("http_login",
                                   {"username": u, "password": p, "canary": canary})
                return PAGE_ADMIN_FAIL
            self._emit_request("http_request")
            return PAGE_ADMIN_LOGIN

        @app.route("/.env")
        def dotenv():
            content = self.canaries.env_file_content() if self.canaries else ""
            self._emit_request("http_request", {"canary_file": True})
            return Response(content, mimetype="text/plain")

        @app.route("/backup/passwords.txt")
        def passwords():
            content = self.canaries.password_file_content() if self.canaries else ""
            self._emit_request("http_request", {"canary_file": True})
            return Response(content, mimetype="text/plain")

        @app.route("/robots.txt")
        def robots():
            self._emit_request("http_request")
            return Response("User-agent: *\nDisallow: /admin\nDisallow: /backup\n",
                            mimetype="text/plain")

        @app.route("/<path:path>", methods=["GET", "POST"])
        def catch_all(path):
            self._emit_request("http_request", {"path": "/" + path})
            return PAGE_404, 404

        return app
