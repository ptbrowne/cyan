import pprint
import json

def ls(filename):
	with open(filename) as f:
		return json.load(f)

if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('glob')
    parser.add_argument('port')
    args = parser.parse_args()
    pprint.pprint(ls(args.glob, args.port))
