from datetime import datetime, timedelta, UTC
import logging
import db
import uuid
import wg
import wg_config
import wg_server_config
from result import Result
import config


logger = logging.getLogger(__name__)
# Helpers functions

# Helper finder of user by telegram
def get_user_by_telegram(tg: str):
    if not tg:
        logger.error("Telegram is required")
        return Result(False, error="Telegram is required")

    row = db.find_by_telegram(tg)

    if row is None:
        logger.warning("User not found: telegram=%s", tg)
        return Result(False, error=f"User not found: telegram={tg}")

    return Result(True, data=row)


#Helpder function to rebuild configuration of WG server
def rebuild_server_wg_config():
        try:
            server_config = wg_server_config.build_server_config('wireguard/server_base.conf','wireguard/peers')
            path_config = wg_server_config.save_wg_server_conf(server_config, 'wg0.conf')
            return Result(True, data={"srv_path_config": path_config.as_posix()})
        except Exception:
            logger.exception('Cant rebuild WG server config')
            return Result(False, error='Failed to rebuild server config')





#Helper function of mapping from db to real
def map_db_to_config():
    return [
        {"id": row["uuid"], "email": row["telegram"] or row["uuid"]}
        for row in db.get_active_clients()
    ]


def handle_create(args):
    try:
        check_unique = db.find_by_telegram(args.telegram)
        if check_unique:
            logger.error("Users already exists with tg = %s", args.telegram)
            return Result(False, error="Users already exists")
        
        user_uuid = uuid.uuid4()
        wg_keys = wg.gen_wg_keys()
        wg_ip = wg.get_wg_free_ip('10.10.0.0/24', db.get_ip_addresses())

        wg_server_pub = config.get_server_public_key()

        wg_endpoint = config.get_endpoint()

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

        config_result = rebuild_server_wg_config()
        if not config_result:
            return config_result

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
        "srv_path_config": config_result.data["srv_path_config"]
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
        user_result = get_user_by_telegram(args.telegram)
        if not user_result:
            return user_result
        
        row = user_result.data
            
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
        logger.exception('Handle renew crashed username: %s tg: %s', 
        args.username, args.telegram)
        return Result(
            False,
            error=f"Handle renew crashed username: {args.username} Tg: {args.telegram}"
            )

def handle_disable(args):
    try:
        user_result = get_user_by_telegram(args.telegram)
        if not user_result:
            return user_result
        row = user_result.data
        
        disable_result = db.disable_by_uuid(row['uuid'], 'manual')

        if not disable_result:
            logger.error("Disable is failed. username: %s, tg: %s", args.username, args.telegram)
            return Result(
                False,
                error=f"Disable failed in DB: username={args.username}, telegram={args.telegram}"
            )
        logger.info('Disabled username: %s, tg: %s', row['username'], row['telegram'])

        config_result = rebuild_server_wg_config()
        if not config_result:
            return config_result        

        updated_result = db.find_by_uuid(row['uuid'])

        return Result(disable_result, data={**updated_result, "srv_path_config": config_result.data["srv_path_config"]})
    
    except Exception:
        logger.exception('Disable gone wrong. username: %s tg: %s',
        args.username, args.telegram)
        return Result(False, error="Unexpected error during disable")
    

def handle_enable(args):
    try:
        user_result = get_user_by_telegram(args.telegram)
        if not user_result:
            return user_result
        
        row = user_result.data

        enable_result = db.enable_by_uuid(row['uuid'])

        if not enable_result:
            logger.error("Enable is failed. username: %s, tg: %s", args.username, args.telegram)
            return Result(
                False,
                error=f"Enable failed in DB: username={args.username}, telegram={args.telegram}"
            )
        logger.info('Enable username: %s, tg: %s', row['username'], row['telegram'])

        config_result = rebuild_server_wg_config()
        if not config_result:
            return config_result

        updated_result = db.find_by_uuid(row['uuid'])
        
        return Result(enable_result, data={**updated_result, "srv_path_config":config_result.data["srv_path_config"]})

    except Exception:
        logger.exception('Enable gone wrong. username: %s tg: %s',
        args.username, args.telegram)
        return Result(False, error="Unexpected error during enable")
    

def handle_list(args):
    try:
        if args.all:
            users = db.get_all_clients()
        elif args.active:
            users = db.get_all_active_clients()
        elif args.inactive:
            users = db.get_inactive_clients()
        else:
            users = db.get_all_clients()

        if not users:
            logger.info("List returned no users")
            return Result(True, data=[])

        return Result(
            True,
            data=users
        )
    except Exception:
        logger.exception('List gone wrong')
        return Result(False, error="Unexpected error during listing")
    

