import simplejson as json
import subprocess

if __name__ == "__main__":
    errors = []
    rectified = []
    with open("errors.log", "r") as elr:
        errors = json.loads(elr.read())

    for error in errors:
        try:
            cmd = error.split(" ")
            _ = subprocess.check_call(cmd)
            rectified.append(cmd[4])
        except:
            print("Still erroneous ----- {error}")


    with open("errors.log", "wb") as elw:
      elw.write(json.dumps([ error for error in errors if error not in rectified ]).encode('utf-8'))

    print(json.dumps(rectified))
