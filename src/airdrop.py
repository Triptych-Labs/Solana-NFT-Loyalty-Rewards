import typing
import time
import pandas
from pathlib import Path
import simplejson as json
import subprocess
import requests
import urllib.parse
import getopt
import sys


def Load(
    token_account: str,
    fee_payer: str,
    config: str,
):
    df = pandas.DataFrame()
    with open("records/holders.json", "r") as _holders:
        _json = _holders.read()
        holders = json.loads(_json)
        df = pandas.json_normalize(holders)
        df.columns = [
            "holder",
            "mints",
            "turnt_amount",
            "turnt_multiplier",
            "turnt_base",
        ]

    error_cmds = []
    print(df[5:])
    for holder in df.itertuples():
        _owner, reward = getattr(holder, "holder"), getattr(holder, "turnt_amount")

        cmd = f"/usr/local/bin/spl-token transfer {token_account} {reward} {_owner} --fee-payer {fee_payer} --config {config} --allow-unfunded-recipient --fund-recipient"

        try:
            _ = subprocess.check_call(cmd.split(" "))
        except:
            print(f"FAILURE ---- {_owner}")
            error_cmds.append(cmd)
            with open("errors.log", "wb") as el:
                el.write(json.dumps(error_cmds).encode("utf-8"))


def parse_opts(opts, expected_opts) -> typing.Tuple[str, str, str]:
    token_account, fee_payer, config = "", "", ""
    if len(opts) < expected_opts:
        raise getopt.GetoptError(msg="Improper Options!!!")

    for opt, val in opts:
        if opt in ["--token-account", "-t"]:
            token_account = val
        if opt in ["--fee-payer", "-f"]:
            fee_payer = val
        if opt in ["--config", "-c"]:
            config = val

    return token_account, fee_payer, config


if __name__ == "__main__":
    start = time.time()
    try:
        opts, _ = getopt.getopt(
            sys.argv[1:],
            "t:f:c:",
            ["token-account=", "fee-payer=", "config="],
        )
        token_account, fee_payer, config = parse_opts(opts, 3)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    Load(token_account, fee_payer, config)

    end = time.time()
    print(f"Took {end-start} seconds!!!")

