#!/usr/bin/env python3
"""Zabbix外部スクリプト。alertscriptsに配置して使用する.

事前に pip install zabbix-googlechat を実行しておく必要がある。
インストール後、このスクリプトをZabbixの AlertScriptsPath ディレクトリに
コピーして使用する。

呼び出し形式:
    zabbix_notify.py {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}

詳細は docs/QUICKSTART.md を参照。
"""

import sys

from zabbix_googlechat.cli import main

if __name__ == "__main__":
    sys.exit(main())
