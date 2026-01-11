import json
import os
import tomllib
from pathlib import Path
from typing import Dict, Mapping, Set, Any, Generator
from zipfile import ZipFile

from paths import PackageFiles, LeagueDir

BotID = str
BotTomlConfig = dict


def fmt_bot_name(name: str) -> BotID:
    return name.replace(" ", "_")


def defmt_bot_name(name: BotID) -> str:
    return name.replace("_", " ")


def scan_dir_for_bot_configs(dir: Path) -> Generator[BotTomlConfig, Any, None]:
    for file in dir.rglob("*bot.toml"):
        with open(file, "rb") as f:
            config = tomllib.load(f)
            config.setdefault("settings", dict())
            config.setdefault("details", dict())
            if config["settings"].get("name") is None or config["settings"].get("agent_id") is None:
                print(f"> Warning: {file} is missing a name or agent_id. Skipping.")
                continue
            config["path"] = str(file)
            yield config


def load_all_unretired_bots(ld: LeagueDir) -> Mapping[BotID, BotTomlConfig]:
    bots = load_all_bots(ld)
    retired = load_retired_bots(ld)
    bots = {bot_id: config for bot_id, config in bots.items() if bot_id not in retired}
    return bots


def load_all_bots(ld: LeagueDir) -> Mapping[BotID, BotTomlConfig]:
    bots = {
        fmt_bot_name(config.get("settings").get("name")): config
        for config in scan_dir_for_bot_configs(ld.bots)
    }

    def add_psyonix_bot(path: Path):
        with open(path, "rb") as f:
            config = tomllib.load(f)
            config["path"] = str(path)
            id = fmt_bot_name(config.get("settings").get("name"))
            bots[id] = config

    add_psyonix_bot(PackageFiles.psyonix_allstar)
    add_psyonix_bot(PackageFiles.psyonix_pro)
    add_psyonix_bot(PackageFiles.psyonix_rookie)

    return bots


def logo(config: BotTomlConfig) -> Path:
    """
    Returns the path to the given bot or None if it does not exists.
    """
    return config.get_logo_file()


def print_details(config: BotTomlConfig):
    """
    Print all details about a bot
    """
    print(f"Bot name:     {config['settings']['name']}")
    print(f"Agent id:     {config['settings']['agent_id']}")
    print(f"Developer:    {config['details'].get('developer', 'N/A')}")
    print(f"Description:  {config['details'].get('description', 'N/A')}")
    print(f"Fun fact:     {config['details'].get('fun_fact', 'N/A')}")
    print(f"Github:       {config['details'].get('source_link', 'N/A')}")
    print(f"Language:     {config['details'].get('language', 'N/A')}")
    print(f"Config path:  {config['path']}")
    print(f"Logo path:    {config['settings'].get('logo_file', 'N/A')}")


def unzip_all_bots(ld: LeagueDir):
    """
    Unzip all zip files in the bot directory
    """
    for root, dirs, files in os.walk(ld.bots, topdown=True):
        dirs[:] = [d for d in dirs]
        for file in files:
            if ".zip" in file:
                path = os.path.join(root, file)
                with ZipFile(path, "r") as zipObj:
                    # Extract all the contents of zip file in current directory
                    print(f"Extracting {path}")
                    folder_name = os.path.splitext(os.path.basename(path))[0]
                    target_dir = os.path.join(root, folder_name)
                    zipObj.extractall(path=target_dir)


def load_retired_bots(ld: LeagueDir) -> Set[BotID]:
    """
    Loads the list of retired bots
    """
    if not ld.retirement.exists():
        return set()
    with open(ld.retirement, 'r') as retirement_file:
        return set(json.load(retirement_file))


def save_retired_bots(ld: LeagueDir, retired: Set[BotID]):
    with open(ld.retirement, 'w') as retirement_file:
        json.dump(list(retired), retirement_file)
