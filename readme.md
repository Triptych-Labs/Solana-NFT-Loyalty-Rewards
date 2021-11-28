# Solana NFT Rewards System

## Intention
Mediate rewards to mint holders of an NFT that is not listed.

The reason why we dont airdrop during our snapshot is because we want to encourage retainment of ducks during a purgatory period.

The time it takes to index can be improved but totally constrained by endpoint rate limits.

Features two stepping - _snapshot_ then _airdrop_ process(es) are understood as means to assure the reward(s) by guaranteeing that mint's entitlement.

This also enables us to restart any one of these two processes should one experience an anomoly/crash/stop/unforeseen type issues.

## Scripts
* `src/snapshot.py` will scan Solana transcations against a(n) a Metaplex Candy Machine Configuration account address.

* `src/magiceden.py` will scan Magic Eden against their Collection Symbol.

* `src/airdrop.py`will call upon `spl-token` binary in `/usr/local/bin` to facilitate rewarding of tokens to unlisted holders.

### Get started

```
git clone --recurse-submodules git@github.com:Triptych-Labs/Solana-NFT-Loyalty-Rewards.git
```

then

```
cd Solana-NFT-Loyalty-Rewards && mkdir records && python3 -m pip install -r requirements.txt
```

then

```bash
pushd ./metaplex_decoder \
    && cargo install --path ./ \
    && cp ./target/release/metaplex-decoder ../ \
    && popd
```

then

```
python3 src/snapshot.py --metaplex_config_address <CONFIG_ADDRESS> --endpoint https://api.mainnet-beta.solana.com --symbol <2 char symbol>

Example:
    python3 src/snapshot.py \
    --metaplex_config_address 4FeKukYzqrE9JBpSRjgiNsYCgPhGjspQSVKsN2hP4AeU \
    --endpoint https://api.mainnet-beta.solana.com \
    --symbol DD
```

then

```
python3 src/magiceden.py -s <Collection Symbol>

Example:
    python3 src/magiceden.py \
    -sdapper_ducks
```

then

```
python3 src/airdrop.py --token-account <TOKEN_ADDRESS> --fee-payer <path_to.json> --config <path_to_config.yml> --exclude <Address> --reward <number>

Example:
    python3 ./src/airdrop.py \
    --token-account 00000000000000000000000000000000000000000000 \
    --fee-payer fee_payer.json \
    --config config.yml \
    --exclude "burner" \
    --exclude "magic eden" \
    --reward 69420
```
