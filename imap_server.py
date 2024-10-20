# -*- coding: utf-8 -*-
"""Module to handle the IMAP servers"""

import json


class ImapServer:
    """This class hold the information on an imap server"""

    def __init__(self, name: str, host: str, port: int = 993):
        """Initiate class"""
        self._name = name
        self._host = host
        self._port = port

    @property
    def name(self) -> str:
        """Getter for name"""
        return self._name

    @property
    def host(self) -> str:
        """Getter for host"""
        return self._host

    @property
    def port(self) -> int:
        """Getter for port"""
        return self._port

    def __str__(self) -> str:
        """String representation"""
        return f"Server {self.name} [{self.host}:{self.port}]"

    def to_dict(self):
        """Transform the object in a dictionnary"""
        return {"name": self.name, "host": self.host, "port": self.port}

    @classmethod
    def from_dict(cls, dct):
        """Custom deserialization of json to create ImapServer instance"""
        if "name" in dct and "host" in dct:
            if "port" in dct:
                return ImapServer(dct["name"], dct["host"], int(dct["port"]))
            else:
                return ImapServer(dct["name"], dct["host"])
        return dct


class ImapServers:
    """This class hold the information on known imap servers"""

    def __init__(self):
        self._servers = []

    def read_from_json(self, json_file: str):
        """Read the definition of the IMAP servers from the asset file"""
        with open(json_file, "r", encoding="utf-8") as json_fd:
            self._servers = json.load(json_fd, object_hook=ImapServer.from_dict)

    def add_server(self, server: ImapServer):
        """Add a server to the known servers"""
        self._servers.append(server)

    def get_server(self, name: str) -> ImapServer:
        """Retrieve a given server"""
        for server in self._servers:
            if server.name == name:
                return server
        return None

    def get_servers(self) -> list[str]:
        """Retrieve the names of all known servers"""
        servers = []
        for server in self._servers:
            servers.append(server.name)
        return servers

    def remove_server(self, server: ImapServer):
        """Remove a server from the known servers"""
        self._servers.remove(server)

    def remove_server_by_name(self, name: str):
        """Remove a server from the known servers"""
        server = self.get_server(name)
        if server is not None:
            self.remove_server(server)
