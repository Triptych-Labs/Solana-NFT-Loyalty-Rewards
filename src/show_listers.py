import simplejson as json
import pandas

pandas.set_option("display.max_rows", 500)
pandas.set_option("display.max_columns", 500)
pandas.set_option("display.width", 100)

if __name__ == "__main__":
    listers_df = pandas.DataFrame()
    with open("records/.listers", "r") as _listers:
        listers_df = pandas.DataFrame(
            json.loads(_listers.read()), columns=["owner", "listings", "epoch"]
        )

    print(listers_df[:5])
    print(listers_df["listings"].sum())
