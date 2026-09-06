from decoys.ssh_decoy import SSHDecoy
from decoys.http_decoy import HTTPDecoy
from decoys.ftp_decoy import FTPDecoy
from decoys.telnet_decoy import TelnetDecoy
from decoys.mysql_decoy import MySQLDecoy

DECOY_REGISTRY = {"ssh": SSHDecoy, "http": HTTPDecoy, "ftp": FTPDecoy,
                  "telnet": TelnetDecoy, "mysql": MySQLDecoy}


def build_decoys(config, event_bus, canaries=None):
    host = config.get("engine", {}).get("host", "0.0.0.0")
    decoys = []
    for name, cfg in config.get("decoys", {}).items():
        cls = DECOY_REGISTRY.get(name)
        if cls is None or not cfg.get("enabled", True):
            continue
        needs_canaries = name in ("ssh", "telnet", "http")
        kwargs = {"canaries": canaries} if needs_canaries else {}
        decoys.append(cls(host, cfg.get("port"), event_bus, cfg, **kwargs))
    return decoys
