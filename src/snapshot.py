import typing
import simplejson as json
import pandas
import os
import os.path
import getopt
import sys
from solana.rpc.async_api import AsyncClient
import solana
import asyncio
import numpy
import math
import aiofiles as aiof
import time
import aiohttp

CHUNK_SIZE = 5

loop = asyncio.get_event_loop()

pandas.set_option("display.max_rows", 501)
pandas.set_option("display.max_columns", 500)
pandas.set_option("display.width", 100)

metaplex_config_address = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


class getSignaturesForAddress:
    err: typing.Dict
    memo: str
    signature: str
    slot: int
    blockTime: int

    def __init__(self, err, memo, signature, slot, blockTime):
        self.err = err
        self.memo = memo
        self.signature = signature
        self.slot = slot
        self.blockTime = blockTime


class uiTokenAmountCls:
    amount: int
    decimals: int
    uiAmount: float
    uiAmountString: str

    def __init__(
        self,
        amount: int,
        decimals: int,
        uiAmount: float,
        uiAmountString: str,
    ):
        self.amount = amount
        self.decimals = decimals
        self.uiAmount = uiAmount
        self.uiAmountString = uiAmountString


class postTokenbalances:
    accountIndex: int
    mint: str
    uiTokenAmount: uiTokenAmountCls

    def __init__(
        self,
        accountIndex: int,
        mint: str,
        uiTokenAmount: uiTokenAmountCls,
    ):
        self.accountIndex = accountIndex
        self.mint = mint
        self.uiTokenAmount = uiTokenAmountCls(**uiTokenAmount)  # type: ignore


async def EvaluateTokenMetadata(uri: str):
    attributes = {}
    async with aiohttp.ClientSession() as client:
        _body = await client.get(uri)
        attributes = json.loads(await _body.text())["attributes"]

    attrs_df = pandas.json_normalize(attributes)
    return json.dumps(attrs_df.to_dict(orient="records"))


async def GetTokenMeta(program: typing.Tuple[AsyncClient, str], t, symbol: str):
    client, endpoint = program
    if os.path.exists(f"records/{str(getattr(t, 'signature'))}.json"):
        return
    try:
        transaction: dict = await client.get_confirmed_transaction(
            str(getattr(t, "signature"))
        )  # type: ignore
    except:
        print("Retrying...")
        await GetTokenMeta(program, t, symbol)
        return

    try:
        mint_balance = transaction["result"]["meta"]["postTokenBalances"]
    except Exception:
        print("No post token balance ???")
        print(transaction["result"]["meta"])
        return
    if len(mint_balance):
        _mint_balance = [token["mint"] for token in mint_balance]
        _mint_balance = list(set(_mint_balance))
        mint_address = _mint_balance[0]
        metadata = json.loads(
            os.popen(f"metaplex-decoder {mint_address} {endpoint}").read()
        )
        print(metadata["name"])
        if metadata["symbol"] != symbol:
            # must be irrelevant token
            return
        uri = metadata["uri"]

        try:
            owners: dict = await client.get_token_largest_accounts(mint_address)  # type: ignore
        except:
            print("Retrying...")
            await GetTokenMeta(program, t, symbol)
            return
        owner = owners["result"]["value"][0]["address"]

        try:
            owner_meta: dict = await client.get_account_info(owner, encoding="jsonParsed")  # type: ignore
        except:
            print("Retrying...")
            await GetTokenMeta(program, t, symbol)
            return
        _owner: str = owner_meta["result"]["value"]["data"]["parsed"]["info"]["owner"]

        ownership_df = pandas.DataFrame(
            [[_owner, mint_address, uri]],
            columns=["owner", "mint_address", "uri"],
        )

        async with aiof.open(f"records/{str(getattr(t, 'signature'))}.json", "wb") as f:
            await f.write(
                json.dumps(ownership_df.to_dict(orient="records")).encode("utf-8")
            )


async def GetTokenMetas(
    program: typing.Tuple[AsyncClient, str],
    signatures_df: pandas.DataFrame,
    symbol: str,
):
    epochs = numpy.array_split(
        numpy.arange(start=0, stop=len(signatures_df)),
        int(math.ceil(len(signatures_df) / CHUNK_SIZE)),
    )
    for epoch in epochs:
        _min, _max = min(epoch), max(epoch)
        tasks: numpy.ndarray = numpy.array([], dtype=asyncio.Future)

        for t in signatures_df[_min:_max].itertuples():
            tasks = numpy.append(
                tasks, asyncio.ensure_future(GetTokenMeta(program, t, symbol))
            )
        await asyncio.wait(tasks.tolist())


async def GetHistory(
    program: typing.Tuple[AsyncClient, str], public_key, limit=1000, before="", until=""
):
    client, _ = program
    # limit attr is capped at 1000
    if limit > 1000:
        print(
            f"Maximum signatures limit exceeded by {limit-1000}. Setting limit to 1000"
        )
        limit = 1000

    options = {
        "limit": limit,
        # start searching backwards from this transaction signature.
        # If not provided the search starts from the top of the highest max confirmed block.
        "before": before,
        "until": until,
        # "commitment": "finalized",
    }
    history: dict = await client.get_signatures_for_address(public_key, **options)  # type: ignore
    results = history["result"]

    return results if len(results) else []


async def FetchTransactions(
    program: typing.Tuple[AsyncClient, str], public_key, symbol: str
):
    signatures = pandas.DataFrame()

    before = ""
    i = 0
    while True:
        scraped = pandas.DataFrame(
            await GetHistory(program, public_key, 1000, before, "")
        )
        if i > 0:
            break
        i = i + 1
        if len(scraped):
            signatures = signatures.append(scraped)

            _before: pandas.DataFrame = scraped.iloc[scraped["blockTime"].idxmin()]
            before = _before["signature"]
        else:
            break
    signatures = signatures.reset_index()

    valid_mints = signatures[signatures["err"].isin([None])]
    valid_mints = valid_mints.reset_index()
    await GetTokenMetas(program, valid_mints[::-1], symbol)


async def parse_opts(opts, expected_opts) -> typing.Tuple[str, str, str]:
    tap, end, symbol = "", "", ""
    if len(opts) != expected_opts:
        raise getopt.GetoptError(msg="Improper Options!!!")

    for opt, val in opts:
        if opt in ["--metaplex_config_address", "-m"]:
            tap = val
        if opt in ["--endpoint", "-e"]:
            end = val
        if opt in ["--symbol", "-s"]:
            symbol = val

    return tap, end, symbol


async def main():
    start = time.time()
    try:
        opts, _ = getopt.getopt(
            sys.argv[1:], "m:e:s:", ["metaplex_config_address=", "endpoint=", "symbol="]
        )
        metaplex_config_address, endpoint, symbol = await parse_opts(opts, 3)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    client = AsyncClient(endpoint)

    await FetchTransactions(
        (client, endpoint),
        solana.publickey.PublicKey(metaplex_config_address),
        symbol,
    )

    await client.close()
    end = time.time()
    print(f"Took {end-start} seconds!!!")


if __name__ == "__main__":
    loop.run_until_complete(main())
