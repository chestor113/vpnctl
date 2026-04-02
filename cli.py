import argparse
import services

def build_parser():
    parser = argparse.ArgumentParser(prog="vpnctl", description="Управление VPN")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create command
    create_parser = subparsers.add_parser("create", help="Создать пользователя")

    create_parser.add_argument("-u", "--username", required=True, help="Имя пользователя")
    create_parser.add_argument("-t", "--telegram", required=True, help="Telegram username")
    create_parser.add_argument("-d", "--days", type=int, default=180, help="Количество дней")
    create_parser.add_argument("--tag", default="regular", help="Тип доступа")

    create_parser.set_defaults(handler=services.handle_create)

    #renew command
    renew_parser = subparsers.add_parser("renew", help = 'Продлить доступ')

    # renew_parser.add_argument("-u", "--username", help="Имя пользователя")
    renew_parser.add_argument("-t", "--telegram", help="Telegram username")
    renew_parser.add_argument("-d", "--days", type=int, default=180, help="Количество дней")

    renew_parser.set_defaults(handler=services.handle_renew)

    #disable user
    disable_parser = subparsers.add_parser("disable", help = "Выключить юзера")

    # disable_parser.add_argument("-u", "--username", help="Имя пользователя")
    disable_parser.add_argument("-t", "--telegram", help="Telegram username")

    disable_parser.set_defaults(handler=services.handle_disable)

    return parser