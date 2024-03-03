import yaml
import sys


try:
    CONFIG = yaml.load(open("config.yml", "r"), Loader=yaml.FullLoader)
except FileNotFoundError:
    print(
        "The file does not exist! Maybe you forgot to create a config.yml file from template"
    )
    sys.exit(1)
