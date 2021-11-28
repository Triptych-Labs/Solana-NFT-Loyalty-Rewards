import sys
import getopt
import typing


def parse_opts(opts, expected_opts) -> typing.Tuple[str, str]:
    tap, end = "", ""
    if len(opts) != expected_opts:
        raise getopt.GetoptError(msg="Improper Options!!!")

    for opt, val in opts:
        if opt in ["--token_program_address", "-t"]:
            tap = val
        if opt in ["--endpoint", "-e"]:
            end = val

    return tap, end


if __name__ == "__main__":
    try:
        opts, _ = getopt.getopt(
            sys.argv[1:], "t:e:", ["token_program_address=", "endpoint="]
        )
        token_program_address, endpoint = parse_opts(opts, 2)
    except getopt.GetoptError as err:
        print(err)
        sys.exit(2)

    print(token_program_address, endpoint)

