from datetime import datetime, timedelta, UTC
import db
import subprocess
import ipaddress




def gen_wg_keys():
    private = subprocess.run(["wg", "genkey"], capture_output=True, text=True, check=True).stdout.strip()
    public = subprocess.run(["wg","pubkey"], input=private, capture_output=True, text=True, check=True).stdout.strip()
    psk = subprocess.run(["wg","genpsk"], capture_output=True, text=True, check=True).stdout.strip()
    return {
        "private_key": private,
        "public_key": public,
        "preshared_key": psk
    }

def get_wg_free_ip(network_mask, taken_ips):
    taken = set(ip for ip in taken_ips if ip is not None)
    network = ipaddress.ip_network(network_mask)
    for ip in network.hosts():
        ip_str = str(ip)
        if ip_str == "10.10.0.1":
            continue
        if ip_str not in taken:
            return ip_str
    return None


# def load_server_public_key(path):
#     with open(path, "r", encoding="utf-8") as f:
#         return f.read().strip()
    
