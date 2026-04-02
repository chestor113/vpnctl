from datetime import datetime, timedelta, UTC
import logging
import db
import uuid
import wg
import wg_config
import wg_server_config
import os
from result import Result
import config

logger = logging.getLogger(__name__)


def map_db_to_config():
    return [
        {"id": row["uuid"], "email": row["telegram"] or row["uuid"]}
        for row in db.get_active_clients()
    ]


def handle_create(args):
    try:
        user_uuid = uuid.uuid4()
        wg_keys = wg.gen_wg_keys()
        wg_ip = wg.get_wg_free_ip('10.10.0.0/24', db.get_ip_addresses())

        wg_server_pub = config.get_server_public_key

        wg_endpoint = config.get_endpoint

        if wg_ip is None:
            logger.error("Create failed: no free WireGuard IP available")
            return Result(False, error="Create failed: no free WireGuard IP available")

        created_at = datetime.now(UTC)
        expires_at = created_at + timedelta(days=args.days)

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
            logger.error("Create failed: failed to insert grant into DB")
            return Result(False, error="Create failed: failed to insert grant into DB")

        wg_data = {
            'client_pub_key': wg_keys['public_key'],
            'client_pr_key': wg_keys['private_key'],
            'preshared_key': wg_keys['preshared_key'],
            'client_ip': wg_ip,
            'server_pub_key': wg_server_pub,
            'endpoint': wg_endpoint,
            'telegram': args.telegram,
            'dns': '8.8.8.8'
        }

        dir_name = f'{args.telegram.replace(" ", "_")}_{user_uuid}'

        client_config = wg_config.render_client_config(wg_data)
        config_path = wg_config.save_client_config(client_config, dir_name, 'wg.conf')

        peer_config = wg_config.render_server_peer(wg_data)
        peer_path_config = wg_config.save_peer_config(peer_config, dir_name, 'peer.conf')

        server_config = wg_server_config.build_server_config('wireguard/server_base.conf','wireguard/peers')
        server_path_config = wg_server_config.save_wg_server_conf(server_config, 'wg0.conf')

        logger.info(
            "Create success: uuid=%s, username=%s, telegram=%s, expires_at=%s, wg_ip=%s",
            str(user_uuid), args.username, args.telegram,
            expires_at.strftime("%Y-%m-%d %H:%M:%S"), wg_ip
        )

        return Result(
        True,
        data={
        "id": row_id,
        "uuid": str(user_uuid),
        "username": args.username,
        "telegram": args.telegram,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "wg_ip": wg_ip,
        "config_path": config_path.as_posix(),
        "peer_path_config": peer_path_config.as_posix(),
        "srv_path_config": server_path_config.as_posix()
        }
        )
    except Exception:
        logger.exception('Handle create crashed: username=%s tg: %s',
        args.username, args.telegram)
        return Result(False,
        error=f"Handle create crashed: username={args.username}, telegram={args.telegram}"
        )

def handle_renew(args):
    try:
        if not args.username and not args.telegram:
            logger.error("Renew failed: no username or telegram provided")
            return Result(False, error="Renew failed: no username or telegram provided")
        row = None
        if args.telegram:
            row = db.find_by_telegram(args.telegram)

        if row is None and args.username:
            row = db.find_by_username(args.username)
        
        if row is None:
            logger.warning(
                "User not found: username=%s, telegram=%s",
                args.username, args.telegram
            )
            return Result(
                False,
                error=f"User not found: username={args.username}, telegram={args.telegram}"
            )
            
        renew_result = db.renew_by_uuid(row['uuid'], args.days)
        if not renew_result:
                logger.error("Renew failed in DB: uuid=%s, username=%s",
                row["uuid"],row["username"])
                return Result(False,
                    error=f"Renew failed in DB: uuid={row['uuid']}, username={row['username']}"
                )

        logger.info(
            "Renew success: username=%s, telegram=%s, days=%s",
            row["username"], row["telegram"], args.days
        )

        return Result(True,data={
        "uuid": row["uuid"],
        "username": row["username"],
        "telegram": row["telegram"],
        "days": args.days
    }
    )
    except Exception:
        logger.exception('Handle renew crashed/ username: %s tg: %s', 
        args.username, args.telegram)
        return Result(
            False,
            error=f"Handle renew crashed/ username: {args.username} Tg: {args.telegram}"
            )

def handle_disable(args):
    try:
        if not args.telegram:
            logger.error("Disable failed: no telegram provided")
            return Result(
                False,
                error="Disable failed: no telegram provided"
            )
        row = None
        if args.telegram:
            row = db.find_by_telegram(args.telegram)

        if row is None:
            logger.warning(
                "User not found: username=%s, telegram=%s",
                args.username, args.telegram
            )
            return Result(
                False,
                error=f"User not found: username={args.username}, telegram={args.telegram}"
            )
        
        disable_result = db.disable_by_uuid(row['uuid'], 'manual')

        server_config = wg_server_config.build_server_config('wireguard/server_base.conf','wireguard/peers')
        server_path_config = wg_server_config.save_wg_server_conf(server_config, 'wg0.conf')

        print(disable_result)
        if not disable_result:
            logger.error("Disable is failed. username: %s, tg: %s", args.username, args.telegram)
            return Result(
                False,
                error=f"Disable failed in DB: username={args.username}, telegram={args.telegram}"
            )
        logger.info('Disabled username: %s, tg: %s', row['username'], row['telegram'])

        updated_result = db.find_by_uuid(row['uuid'])

        return Result(disable_result, data=updated_result)
    
    except Exception:
        logger.exception('Disable gone wrong. username: %s tg: %s',
        args.username, args.telegram)
        return Result(False, error="Unexpected error during disable")