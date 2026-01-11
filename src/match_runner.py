import time
from typing import Mapping, Tuple, Optional

from rlbot.managers import MatchManager
from rlbot.flat import MatchPhase

from bots import BotID, BotTomlConfig, fmt_bot_name
from match import MatchDetails, MatchResult, PlayerScore
from paths import LeagueDir
from replays import ReplayMonitor, ReplayData


def run_match(ld: LeagueDir, match_details: MatchDetails, bots: Mapping[BotID, BotTomlConfig],
              get_replay_data: bool) -> Tuple[MatchResult, Optional[ReplayData]]:

    with MatchManager() as man:
        man.start_match(match_details.to_config(bots))

        replay_monitor = ReplayMonitor()
        replay_monitor.ensure_monitoring()

        # Wait for match to end
        while man.packet.match_info.match_phase != MatchPhase.Ended:
            time.sleep(1.0)

        # Extract results
        match_result = MatchResult(
            blue_goals=man.packet.teams[0].score,
            orange_goals=man.packet.teams[1].score,
            player_scores={
                fmt_bot_name(pl.name): PlayerScore(
                    points=pl.score_info.score,
                    goals=pl.score_info.goals,
                    shots=pl.score_info.shots,
                    saves=pl.score_info.saves,
                    assists=pl.score_info.assists,
                    demolitions=pl.score_info.demolitions,
                    own_goals=pl.score_info.own_goals,
                )
                for pl in man.packet.players
            }
        )

        print(f"Detected match end. Result: {match_result.blue_goals}-{match_result.orange_goals}")

        # Handles replays
        replay_data = None
        if get_replay_data:
            print("Grabbing replay file... ", end="", flush=True)
            # Use up to 30 seconds to detect replay file
            game_end_time = time.time()
            seconds_since_game_end = 0
            while seconds_since_game_end < 30:
                seconds_since_game_end = time.time() - game_end_time
                if replay_monitor.replay_id:
                    replay_data = ReplayData(replay_monitor.replay_path, replay_monitor.replay_id)
                    break
            replay_monitor.stop_monitoring()

            if replay_data:
                print("Got it:", replay_data.replay_path.name)
            else:
                print("Timeout")

        return match_result, replay_data