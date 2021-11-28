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

headers = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://magiceden.io",
    "Accept-Encoding": "gzip, deflate, br",
    "Host": "api-mainnet.magiceden.io",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://magiceden.io/",
    "Connection": "keep-alive",
}


def GetListings(number_of_listings: int, ashift: int):
    """
    Magic Eden allows for a max of 500 listings upon query. If number_of_listings exceed 500,
    consider the difference as the ashift value. If magnitudes greater than 500*2, chunk fn calls.
    """
    if number_of_listings > 500:
        print(
            f"Exceeding maximum listing query depth. Consider ashifting by {number_of_listings-500}"
        )

    # encoded query is json fmt -
    #
    #       {"$match":{"collectionSymbol":"dapper_ducks"},"$sort":{"createdAt":-1},"$skip":40,"$limit":20}
    #
    query = {
        "$match": {
            "collectionSymbol": "dapper_ducks",
        },
        "$sort": {
            "createdAt": -1,
        },
        "$skip": int(ashift),
        "$limit": int(number_of_listings),
    }
    payload = {
        "q": json.dumps(query).replace(" ", ""),
    }
    response: requests.Response = requests.request(
        "GET",
        f"https://api-mainnet.magiceden.io/rpc/getListedNFTsByQuery?{urllib.parse.urlencode(payload)}",
        headers=headers,
    )
    body = json.loads(response.text)["results"]

    df = pandas.DataFrame(body)

    return df["owner"]


def GetNumberOfListings():
    response: requests.Response = requests.request(
        "GET",
        "https://api-mainnet.magiceden.io/rpc/getCollectionEscrowStats/dapper_ducks",
        headers=headers,
    )
    count = json.loads(response.text)["results"]["listedCount"]

    return count


def Load(
    token_account: str,
    fee_payer: str,
    config: str,
    exclusions: typing.List[str],
    reward: int,
):

    bad_people = []
    listings_owners = GetOwners()
    df = pandas.DataFrame()
    records = Path("./records/")
    for _file in records.glob("*.json"):
        with open(_file, "r") as _record:
            record = json.loads(_record.read())
            if record[0]["owner"] in listings_owners:
                print(f'{record[0]["owner"]} is a bad duckie!!!')
                continue
            if record[0]["owner"] in exclusions:
                bad_people.append(record[0]["owner"])
                continue
            df = df.append(pandas.DataFrame(record))
    df = df.reset_index()

    owners = df.groupby("owner").size()
    owners = owners.reset_index()
    owners.columns = ["owner", "count"]

    owners["FLOCK"] = owners["count"] * reward
    owners = owners.sort_values("FLOCK").reset_index()

    error_cmds = []
    for holder in owners.itertuples():
        _owner, flock = getattr(holder, "owner"), getattr(holder, "FLOCK")

        cmd = f"/usr/local/bin/spl-token transfer {token_account} {flock} {_owner} --fee-payer {fee_payer} --config {config} --allow-unfunded-recipient --fund-recipient"

        try:
            _ = subprocess.check_call(cmd.split(" "))
        except:
            print(f"FAILURE ---- {_owner}")
            error_cmds.append(cmd)
            with open("errors.log", "wb") as el:
                el.write(json.dumps(error_cmds).encode('utf-8'))


def GetOwners():
    listers_df = pandas.DataFrame()
    with open("records/.listers", "r") as _listers:
        listers_df = pandas.DataFrame(
            json.loads(_listers.read()), columns=["index", "owner", "listings", "epoch"]
        )

    return listers_df["owner"]


def parse_opts(
    opts, expected_opts
) -> typing.Tuple[str, str, str, typing.List[str], int,]:
    token_account, fee_payer, config, exclusions, reward = "", "", "", [], 0
    if len(opts) <= expected_opts:
        raise getopt.GetoptError(msg="Improper Options!!!")

    for opt, val in opts:
        if opt in ["--token-account", "-t"]:
            token_account = val
        if opt in ["--fee-payer", "-f"]:
            fee_payer = val
        if opt in ["--config", "-c"]:
            config = val
        if opt in ["--exclude", "-e"]:
            exclusions.append(val)
        if opt in ["--reward", "-r"]:
            reward = int(val)

    return token_account, fee_payer, config, exclusions, reward


if __name__ == "__main__":
    start = time.time()
    try:
        opts, _ = getopt.getopt(
            sys.argv[1:],
            "t:f:c:e:r:",
            ["token-account=", "fee-payer=", "config=", "exclude=", "reward="],
        )
        token_account, fee_payer, config, exclusions, reward = parse_opts(opts, 5)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    Load(token_account, fee_payer, config, exclusions, reward)
    
    end = time.time()
    print(f"Took {end-start} seconds!!!")
