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
import numpy

attr_meta = [
    "Item",
    "Clothes",
    "Skin",
    "Head",
    "Eyes",
    "Mouth",
    "Tier",
    "Tribe",
]

record_meta = [
    "_",
    "owner",
    "mint_address",
    "uri",
]


class Reward:
    def multiplier(self, values: pandas.DataFrame):
        return len(numpy.unique(values[attr_meta]["Tier"])) * 0.1

    def base(self, tier: str):
        tut = 0
        tier = tier.lower()
        if tier == "common":
            tut = 1
        if tier == "uncommon":
            tut = 2
        if tier == "rare":
            tut = 3
        if tier == "epic":
            tut = 4
        if tier == "legendary":
            tut = 5
        if tier == "mythic":
            tut = 6
        if tier == "tribal leader":
            tut = 15
        return tut

    def reward(self, _multiplier: float, _base: int):
        return float((_multiplier + 1) * _base)

    def Init(self, tokens: pandas.DataFrame):
        _base = sum([self.base(token) for token in tokens["Tier"].values])
        _multiplier = self.multiplier(tokens)
        _reward = self.reward(_multiplier, _base)
        print()
        print(f"Multiplier: {_multiplier}, Base: {_base}, Reward: {_reward}")
        print()


def EvaluateTokenMetadata(uri):
    _body = requests.get(uri)
    attrs_df = pandas.json_normalize(json.loads(_body.text)["attributes"])
    return attrs_df.reset_index()


def Load(
    token_account: str,
    fee_payer: str,
    config: str,
):
    df = pandas.DataFrame()
    records = Path("./records/")
    for _file in records.glob("*.json"):
        with open(_file, "r") as _record:
            record = pandas.DataFrame(json.loads(_record.read())).reset_index()
            metas = record["uri"].apply(EvaluateTokenMetadata)
            traits = metas[0]["trait_type"].to_list()
            metas = metas[0][[metas[0].columns[2]]].transpose().reset_index(drop=True)
            record = pandas.concat(
                [record, metas],
                axis=1,
                ignore_index=True,
            )
            record.columns = [
                *record_meta,
                *traits,
            ]
            df = df.append(record)

    error_cmds = []

    holders = df.groupby("owner").size()
    holders.columns = ["owner", "mints"]
    rewardCls = Reward()
    print(df.loc[df["owner"] == holders.index[0]])
    _ = rewardCls.Init(df.loc[df["owner"] == holders.index[0]])

    for holder in df.itertuples():
        _owner = getattr(holder, "owner")

        cmd = f"/usr/local/bin/spl-token transfer {token_account} {1} {_owner} --fee-payer {fee_payer} --config {config} --allow-unfunded-recipient --fund-recipient"

        try:
            # _ = subprocess.check_call(cmd.split(" "))
            _ = ""
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
# _ = (f"Took {end-start} seconds!!!")

