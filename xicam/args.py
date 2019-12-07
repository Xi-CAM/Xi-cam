import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", dest="verbose", action="count", help='increase output verbosity', default=0)
parser.add_argument("--no-cammart", dest="nocammart", action="store_true",
                    help="disable cammart and sandboxed environment features")
parser.add_argument("--no-splash", dest="nosplash", action="store_true", help="skip the Xi-cam splash screen")
args = parser.parse_args()
