"""Qt-native asynchronous HTTP transport shared by desktop screens."""

import json
import os
from urllib.parse import urlsplit
from PyQt6.QtCore import QObject, QUrl, QByteArray, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest


class ApiClient(QObject):
    session_expired = pyqtSignal()

    def __init__(self, base_url=None, parent=None):
        super().__init__(parent)
        self.base_url = (base_url or os.getenv("ALERTME_API_URL", "http://127.0.0.1:5000")).rstrip(
            "/"
        )
        url = urlsplit(self.base_url)
        if (
            not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
            or (
                url.scheme != "https"
                and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))
            )
        ):
            raise ValueError(
                "Use HTTPS for a remote API, or HTTP on loopback for local development."
            )
        self.network = QNetworkAccessManager(self)
        self.token = ""
        self.generation = 0
        self.pending = set()

    def set_token(self, token):
        self.token = token
        self.generation += 1

    def clear(self):
        self.token = ""
        self.generation += 1
        for reply in list(self.pending):
            reply.abort()

    def request(self, method, path, payload=None, success=None, failure=None):
        request = QNetworkRequest(QUrl(self.base_url + path))
        request.setTransferTimeout(10000)
        request.setRawHeader(b"Content-Type", b"application/json")
        request.setRawHeader(b"Accept", b"application/json")
        request.setAttribute(
            QNetworkRequest.Attribute.CookieLoadControlAttribute,
            QNetworkRequest.LoadControl.Manual,
        )
        request.setAttribute(
            QNetworkRequest.Attribute.CookieSaveControlAttribute,
            QNetworkRequest.LoadControl.Manual,
        )
        if self.token:
            request.setRawHeader(b"Authorization", ("Bearer " + self.token).encode())
        body = QByteArray(json.dumps(payload).encode() if payload is not None else b"")
        generation = self.generation
        reply = self.network.sendCustomRequest(request, method.encode(), body)
        self.pending.add(reply)

        def finished():
            self.pending.discard(reply)
            status = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
            raw = bytes(reply.readAll())
            reply.deleteLater()
            if generation != self.generation:
                return
            try:
                result = json.loads(raw) if raw else {}
            except (ValueError, UnicodeDecodeError):
                result = {}
            if status and 200 <= status < 300:
                if success:
                    success(result)
            else:
                if status == 401 and self.token:
                    self.clear()
                    self.session_expired.emit()
                if failure:
                    failure(
                        result.get(
                            "message",
                            "Could not reach the API. Check the connection and try again.",
                        )
                    )

        reply.finished.connect(finished)
