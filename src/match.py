import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, List, Dict, Optional

from rlbot.config import load_match_config, load_player_config, load_player_loadout
from rlbot.flat import MatchConfiguration, PlayerConfiguration, PsyonixBot
from rlbot_flatbuffers import PsyonixSkill

from bots import BotID, BotTomlConfig
from paths import PackageFiles, LeagueDir


class Team:
    BLUE = 0
    ORANGE = 1


@dataclass
class PlayerScore:
    """
    Object that contains info about a player's points, goals, shots, saves, and assists from a match
    """
    points: int = 0
    goals: int = 0
    shots: int = 0
    saves: int = 0
    assists: int = 0
    demolitions: int = 0
    own_goals: int = 0


@dataclass
class MatchResult:
    """
    Object that contains relevant info about a match result
    """

    blue_goals: int = 0
    orange_goals: int = 0
    player_scores: Dict[BotID, PlayerScore] = field(default_factory=dict)


@dataclass
class MatchDetails:
    time_stamp: str = ""
    name: str = ""
    blue: List[BotID] = field(default_factory=list)
    orange: List[BotID] = field(default_factory=list)
    map: str = ""
    result: Optional[MatchResult] = None
    replay_id: Optional[str] = None

    def to_config(self, bots: Mapping[BotID, BotTomlConfig]) -> MatchConfiguration:
        match_config = load_match_config(PackageFiles.default_match_config)
        match_config.game_map_upk = self.map
        match_config.player_configurations = [
            self.bot_to_config(bots[self.blue[0]], Team.BLUE),
            self.bot_to_config(bots[self.blue[1]], Team.BLUE),
            self.bot_to_config(bots[self.blue[2]], Team.BLUE),
            self.bot_to_config(bots[self.orange[0]], Team.ORANGE),
            self.bot_to_config(bots[self.orange[1]], Team.ORANGE),
            self.bot_to_config(bots[self.orange[2]], Team.ORANGE),
        ]
        return match_config

    def bot_to_config(self, config: BotTomlConfig, team: int) -> PlayerConfiguration:
        if (skill := config["settings"].get("psyonix_skill")) is not None:
            # Psyonix bot
            loadout = load_player_loadout(PackageFiles.psyonix_loadout, team)
            pcfg = PlayerConfiguration(PsyonixBot(
                name=config["settings"]["name"],
                loadout=loadout,
                bot_skill=PsyonixSkill(skill),
            ), team)
        else:
            pcfg = load_player_config(config["path"], team)
        return pcfg

    def save(self, ld: LeagueDir):
        self.write(ld.matches / f"{self.name}.json")

    def write(self, path: Path):
        """
        Write match details to a specific path
        """
        with open(path, 'w') as f:
            json.dump(self, f, cls=MatchDetailsEncoder, sort_keys=True)

    @staticmethod
    def latest(ld: LeagueDir, count: int) -> List['MatchDetails']:
        """
        Returns the match details of the n latest matches
        """
        # Assume last match file is the newest, since they are prefixed with a time stamp
        return [MatchDetails.read(path) for path in list(ld.matches.iterdir())[-count:]]

    @staticmethod
    def all(ld: LeagueDir) -> List['MatchDetails']:
        """
        Returns a list of all matches played, chronological order
        """
        return [MatchDetails.read(path) for path in list(ld.matches.iterdir())]

    @staticmethod
    def undo(ld: LeagueDir):
        """
        Remove latest match
        """
        if any(ld.matches.iterdir()):
            # Assume last match file is the newest, since they are prefixed with a time stamp
            list(ld.matches.iterdir())[-1].unlink()   # Remove file
        else:
            print("No match to undo.")

    @staticmethod
    def read(path: Path) -> 'MatchDetails':
        """
        Read a specific MatchDetails file
        """
        with open(path) as f:
            return json.load(f, object_hook=as_match_details)


# ====== MatchDetails -> JSON ======

known_types = {
    MatchDetails: "__MatchDetails__",
    MatchResult: "__MatchResult__",
    PlayerScore: "__PlayerScore__",
}


class MatchDetailsEncoder(json.JSONEncoder):
    def default(self, obj):
        for cls, tag in known_types.items():
            if not isinstance(obj, cls):
                continue
            json_obj = obj.__dict__.copy()
            json_obj[tag] = True
            return json_obj
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


# ====== JSON -> MatchDetails ======

def as_match_details(json_obj) -> MatchDetails:
    for cls, tag in known_types.items():
        if not json_obj.get(tag, False):
            continue
        obj = cls()
        del json_obj[tag]
        obj.__dict__ = json_obj
        return obj
    return json_obj
