from pathlib import Path


def render_client_config(data):
    result = f"""[Interface]
PrivateKey={data['client_pr_key']}
Address={data['client_ip']}
DNS = {data['dns']}

[Peer]
PublicKey={data['server_pub_key']}
Endpoint={data['endpoint']}
AllowedIPs=0.0.0.0/0
PersistentKeepalive = 25
"""
    return result
    
def save_client_config(config_text, dir_name, filename):
    path = Path("output") / dir_name / filename
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        f.write(config_text)
    return path

def render_server_peer(data):
    result = f"""[Peer]
#{data['telegram']}
PublicKey = {data['client_pub_key']}
AllowedIPs = {data['client_ip']}/32
"""
    return result

def save_peer_config(config_text, dir_name, filename):
    path = Path('wireguard/peers') / dir_name / filename
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", encoding='utf-8') as f:
        f.write(config_text)
    return path