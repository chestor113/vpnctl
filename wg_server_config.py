from pathlib import Path
 

def build_server_config(base_config_path, peers_dir):
    base_config = Path(base_config_path).read_text(encoding="utf-8")
    peers_base = Path(peers_dir)
    result = [base_config]

    for peer in sorted(peers_base.iterdir()):
        if not peer.is_dir():
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