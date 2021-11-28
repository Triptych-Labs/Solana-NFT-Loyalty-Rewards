import time
import urllib.parse
import requests
import simplejson as json
import pandas
import numpy
import math
import getopt
import sys

pandas.set_option("display.max_rows", 500)
pandas.set_option("display.max_columns", 500)
pandas.set_option("display.width", 100)

# TOKEN_PROGRAM_ADDRESS = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://magiceden.io",
    "Accept-Encoding": "gzip, deflate, br",
    "Host": "api-mainnet.magiceden.io",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://magiceden.io/",
    "Connection": "keep-alive",
}


def GetListings(collection_symbol: str, number_of_listings: int, ashift: int):
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
            "collectionSymbol": collection_symbol,
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


def GetNumberOfListings(collection_symbol: str):
    response: requests.Response = requests.request(
        "GET",
        f"https://api-mainnet.magiceden.io/rpc/getCollectionEscrowStats/{collection_symbol}",
        headers=headers,
    )
    count = json.loads(response.text)["results"]["listedCount"]

    return count


def GetOwners(collection_symbol: str):
    listings_count = GetNumberOfListings(collection_symbol)

    owners = numpy.array([], dtype=object)
    epochs = numpy.array_split(
        numpy.arange(start=0, stop=listings_count), int(math.ceil(listings_count / 500))
    )

    for epoch in epochs:
        _owners = GetListings(collection_symbol, len(epoch), min(epoch))
        owners = numpy.append(owners, _owners)

    owners_df = pandas.DataFrame(owners, columns=["owner"])
    owners = owners_df.groupby("owner").size()
    owners = owners.reset_index()
    owners.columns = ["owner", "listings"]
    owners["epoch"] = int(time.time())
    print(owners.sort_values("listings")[::-1].reset_index())
    print(len(owners))
    with open("records/.listers", "wb") as f:
        f.write(json.dumps(owners.to_dict(orient="records")).encode("utf-8"))


def parse_opts(opts, expected_opts) -> str:
    collection_symbol = ""
    if len(opts) != expected_opts:
        raise getopt.GetoptError(msg="Improper Options!!!")

    for opt, val in opts:
        if opt in ["--collection_symbol", "-s"]:
            collection_symbol = val

    return collection_symbol


if __name__ == "__main__":
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "s:", ["collection_symbol="])
        collection_symbol = parse_opts(opts, 1)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    GetOwners(collection_symbol)
