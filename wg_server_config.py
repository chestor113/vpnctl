from pathlib import Path
import db
import logging

logger = logging.getLogger(__name__)

def build_server_config(base_config_path, peers_dir):
    base_config = Path(base_config_path).read_text(encoding="utf-8")
    peers_base = Path(peers_dir)
    result = [base_config]

    active_clients = db.get_uuid_active_clients()

    for peer in sorted(peers_base.iterdir()):
        if not peer.is_dir():
            continue
        parts = peer.name.split("_")

        if len(parts) < 2:
            logger.warning("Invalid peer folder name: %s", peer.name)
            continue

        peer_uuid = parts[-1]

        if peer_uuid not in active_clients:
            continue
        peer_file = peer / "peer.conf"
        if not peer_file.exists():
            continue
        peer_config = peer_file.read_text(encoding="utf-8")
        result.append(peer_config)

    final_config = "\n".join(result)
    return final_config

def save_wg_server_conf(config_text, filename):
    path = Path("wireguard/server_config") / filename
    path.parent.mkdir(exist_ok=True)
    path.write_text(config_text, encoding="utf-8")

    return path
