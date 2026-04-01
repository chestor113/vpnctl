from datetime import datetime, timedelta, UTC
import logging
import db
import uuid
import wg
import wg_config
import wg_server_config


logger = logging.getLogger(__name__)

def handle_create(args):
    try:
        user_uuid = uuid.uuid4()
        wg_keys = wg.gen_wg_keys()
        wg_ip = wg.get_wg_free_ip('10.10.0.0/24', db.get_ip_addresses())

        if wg_ip is None:
            logger.error("No free WireGuard IP available")
            return None

        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(days=args.days)

        server_pub = wg.load_server_public_key("secrets/wg_server_public.key")

        payload = {
            'uuid': str(user_uuid),
            'username': args.username,
            'telegram': args.telegram,
            'created_at': created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'expires_at': expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            'is_enabled': 1,
            'access_tag':args.tag,
            'wg_public_key': wg_keys['public_key'],
            'wg_private_key': wg_keys['private_key'],
            'wg_preshared_key': wg_keys['preshared_key'],
            'wg_assigned_ip': wg_ip
        }
        
        row_id = db.insert_grant(payload)
        if row_id is None:
            logging.error("Failed to insert grant into DB")
            return None

        wg_data = {
            'client_pub_key': wg_keys['public_key'],
            'client_pr_key': wg_keys['private_key'],
            'preshared_key': wg_keys['preshared_key'],
            'client_ip': f'{wg_ip}',
            'server_pub_key': server_pub,
            'endpoint': '109.107.175.116:54321',
            'username': args.username,
            'dns': '8.8.8.8'
        }

        dir_name = f'{args.username.replace(" ", "_")}_{user_uuid}'

        client_config = wg_config.render_client_config(wg_data)
        config_path = wg_config.save_client_config(client_config, dir_name, 'wg.conf')

        peer_config = wg_config.render_server_peer(wg_data)
        peer_path_config = wg_config.save_peer_config(peer_config, dir_name, 'peer.conf')

        server_config = wg_server_config.build_server_config('wireguard/server_base.conf','wireguard/peers')
        server_path_config = wg_server_config.save_wg_server_conf(server_config, 'wg0.conf')

        logger.info('Created user: uuid: %s, usename: %s, tg: %s, expires_at: %s, wg_ip: %s', str(user_uuid) , args.username, args.telegram, expires_at.strftime("%Y-%m-%d %H:%M:%S"),  wg_ip)

        return {
        "id": row_id,
        "uuid": str(user_uuid),
        "username": args.username,
        "telegram": args.telegram,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "wg_ip": wg_ip,
        "config_path": str(config_path),
        "peer_path_config": str(peer_path_config),
        "srv_path_config": str(server_path_config)
    }
    except Exception:
        logger.exception('Handle create crashed: username=%s tg: %s', args.username, args.telegram)
        return None

def handle_renew(args):
    try:
        if not args.username and not args.telegram:
            logger.error("There is no usernamd and telegram, Renew failed")
            return None
        row = None
        if args.telegram:
            row = db.find_by_telegram(args.telegram)

        if row is None and args.username:
            row = db.find_by_username(args.username)
        
        if row is None:
            logger.warning('Username: %s Tg %s is not found', args.username, args.telegram)
            return None
        
        renew_result = db.renew_by_uuid(row['uuid'], args.days)
        if renew_result is None:
                logger.error("Renew failed in DB: uuid=%s, username=%s",row["uuid"],row["username"])
                return None

        logger.info('Username: %s, Tg: %s, Days to expires_at: %s', row['username'], row['telegram'], args.days)
        return renew_result
    except Exception:
        logger.exception('Handle renew crashed: username=%s tg: %s', args.username, args.telegram)
        return None

def map_db_to_config():
    return [
        {"id": row["uuid"], "email": row["telegram"] or row["uuid"]}
        for row in db.get_active_clients()
    ]
