# app/domains/game/logic.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from app.shared.schemas.events import GamePhaseChanged


class Role(str, Enum):
    CITIZEN = "citizen"
    MAFIA = "mafia"
    DOCTOR = "doctor"
    DETECTIVE = "detective"
    PROSTITUTE = "prostitute"


class GamePhase(str, Enum):
    LOBBY = "lobby"
    ROLE_ASSIGNMENT = "role_assignment"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTING = "day_voting"
    DAY_EXECUTION = "day_execution"
    NIGHT_START = "night_start"
    NIGHT_MAFIA = "night_mafia"
    NIGHT_DOCTOR = "night_doctor"
    NIGHT_PROSTITUTE = "night_prostitute"
    NIGHT_DETECTIVE = "night_detective"
    NIGHT_RESULTS = "night_results"
    GAME_ENDED = "game_ended"


@dataclass
class PhaseConfig:
    duration_seconds: int
    allowed_roles: List[Role]
    voice_config: Dict[str, bool]  # role -> can_speak


PHASE_CONFIGS = {
    GamePhase.LOBBY: PhaseConfig(
        duration_seconds=60, allowed_roles=[], voice_config={}
    ),
    GamePhase.DAY_DISCUSSION: PhaseConfig(
        duration_seconds=180,
        allowed_roles=list(Role),
        voice_config={role.value: True for role in Role},  # Все говорят
    ),
    GamePhase.DAY_VOTING: PhaseConfig(
        duration_seconds=60,
        allowed_roles=list(Role),
        voice_config={role.value: True for role in Role},
    ),
    GamePhase.NIGHT_MAFIA: PhaseConfig(
        duration_seconds=30,
        allowed_roles=[Role.MAFIA],
        voice_config={
            Role.MAFIA.value: True,  # Только мафия говорит
            Role.CITIZEN.value: False,
            Role.DOCTOR.value: False,
            Role.DETECTIVE.value: False,
            Role.PROSTITUTE.value: False,
        },
    ),
    GamePhase.NIGHT_DOCTOR: PhaseConfig(
        duration_seconds=15,
        allowed_roles=[Role.DOCTOR],
        voice_config={role.value: False for role in Role},  # Никто не говорит
    ),
    GamePhase.NIGHT_PROSTITUTE: PhaseConfig(
        duration_seconds=15,
        allowed_roles=[Role.PROSTITUTE],
        voice_config={role.value: False for role in Role},
    ),
    GamePhase.NIGHT_DETECTIVE: PhaseConfig(
        duration_seconds=15,
        allowed_roles=[Role.DETECTIVE],
        voice_config={role.value: False for role in Role},
    ),
}


class GameLogic:
    def __init__(self):
        self.game_states: Dict[str, Dict] = {}

    def create_game(self, game_id: str, players: List[str]) -> Dict:
        """Создание новой игры"""
        self.game_states[game_id] = {
            "phase": GamePhase.LOBBY,
            "players": players,
            "alive_players": set(players),
            "roles": {},
            "day_count": 0,
            "night_actions": {},
            "vote_results": {},
        }
        return self.game_states[game_id]

    def assign_roles(self, game_id: str) -> Dict[str, Role]:
        """Распределение ролей"""
        state = self.game_states.get(game_id)
        if not state:
            raise ValueError(f"Game {game_id} not found")

        players = state["players"]
        num_players = len(players)

        # Стандартное распределение ролей
        if num_players < 6:
            role_distribution = {
                Role.MAFIA: 1,
                Role.DOCTOR: 1,
                Role.CITIZEN: num_players - 2,
            }
        elif num_players < 10:
            role_distribution = {
                Role.MAFIA: 2,
                Role.DOCTOR: 1,
                Role.DETECTIVE: 1,
                Role.CITIZEN: num_players - 4,
            }
        else:
            role_distribution = {
                Role.MAFIA: 3,
                Role.DOCTOR: 1,
                Role.DETECTIVE: 1,
                Role.PROSTITUTE: 1,
                Role.CITIZEN: num_players - 6,
            }

        # Присваиваем роли случайным образом
        import random

        shuffled_players = random.sample(players, len(players))

        roles = {}
        idx = 0
        for role, count in role_distribution.items():
            for _ in range(count):
                if idx < len(shuffled_players):
                    roles[shuffled_players[idx]] = role
                    idx += 1

        state["roles"] = roles
        return roles

    def get_phase_sequence(self, current_phase: GamePhase) -> GamePhase:
        """Получение следующей фазы"""
        transitions = {
            GamePhase.LOBBY: GamePhase.ROLE_ASSIGNMENT,
            GamePhase.ROLE_ASSIGNMENT: GamePhase.DAY_DISCUSSION,
            GamePhase.DAY_DISCUSSION: GamePhase.DAY_VOTING,
            GamePhase.DAY_VOTING: GamePhase.DAY_EXECUTION,
            GamePhase.DAY_EXECUTION: GamePhase.NIGHT_START,
            GamePhase.NIGHT_START: GamePhase.NIGHT_MAFIA,
            GamePhase.NIGHT_MAFIA: GamePhase.NIGHT_DOCTOR,
            GamePhase.NIGHT_DOCTOR: GamePhase.NIGHT_PROSTITUTE,
            GamePhase.NIGHT_PROSTITUTE: GamePhase.NIGHT_DETECTIVE,
            GamePhase.NIGHT_DETECTIVE: GamePhase.NIGHT_RESULTS,
            GamePhase.NIGHT_RESULTS: GamePhase.DAY_DISCUSSION,
            GamePhase.GAME_ENDED: GamePhase.GAME_ENDED,
        }
        return transitions.get(current_phase, GamePhase.GAME_ENDED)

    def advance_phase(self, game_id: str) -> GamePhase:
        """Переход к следующей фазе"""
        state = self.game_states.get(game_id)
        if not state:
            raise ValueError(f"Game {game_id} not found")

        current_phase = state["phase"]
        next_phase = self.get_phase_sequence(current_phase)

        # Проверка условий окончания игры
        if self._check_win_conditions(game_id):
            next_phase = GamePhase.GAME_ENDED

        state["phase"] = next_phase

        # Увеличиваем счетчик дней
        if next_phase == GamePhase.DAY_DISCUSSION:
            state["day_count"] += 1

        return next_phase

    def _check_win_conditions(self, game_id: str) -> bool:
        """Проверка условий победы"""
        state = self.game_states.get(game_id)
        if not state:
            return False

        alive_players = state["alive_players"]
        roles = state["roles"]

        alive_mafia = sum(1 for p in alive_players if roles.get(p) == Role.MAFIA)
        alive_citizens = len(alive_players) - alive_mafia

        # Мафия победила
        if alive_mafia >= alive_citizens:
            return True

        # Мирные победили
        if alive_mafia == 0:
            return True

        return False

    def process_night_action(
        self, game_id: str, player_id: str, action: str, target_id: str
    ) -> bool:
        """Обработка ночных действий"""
        state = self.game_states.get(game_id)
        if not state:
            return False

        phase = state["phase"]
        player_role = state["roles"].get(player_id)

        # Проверка, может ли игрок действовать в этой фазе
        phase_config = PHASE_CONFIGS.get(phase)
        if not phase_config or player_role not in phase_config.allowed_roles:
            return False

        # Сохраняем действие
        if "night_actions" not in state:
            state["night_actions"] = {}

        state["night_actions"][player_id] = {
            "action": action,
            "target": target_id,
            "role": player_role,
        }

        return True

    def resolve_night_actions(self, game_id: str) -> Dict:
        """Разрешение всех ночных действий"""
        state = self.game_states.get(game_id)
        if not state:
            return {}

        actions = state.get("night_actions", {})
        results = {
            "killed": None,
            "healed": None,
            "blocked": None,
            "investigated": None,
        }

        # Проститутка блокирует первой
        for player_id, action_data in actions.items():
            if action_data["role"] == Role.PROSTITUTE:
                blocked_player = action_data["target"]
                results["blocked"] = blocked_player
                # Удаляем действие заблокированного игрока
                if blocked_player in actions:
                    del actions[blocked_player]

        # Мафия убивает
        mafia_targets = []
        for player_id, action_data in actions.items():
            if action_data["role"] == Role.MAFIA:
                mafia_targets.append(action_data["target"])

        # Выбираем цель большинством голосов мафии
        if mafia_targets:
            from collections import Counter

            target_counts = Counter(mafia_targets)
            killed_player = target_counts.most_common(1)[0][0]
            results["killed"] = killed_player

        # Доктор лечит
        for player_id, action_data in actions.items():
            if action_data["role"] == Role.DOCTOR:
                healed_player = action_data["target"]
                results["healed"] = healed_player
                # Если доктор вылечил убитого, тот выживает
                if results["killed"] == healed_player:
                    results["killed"] = None

        # Детектив проверяет
        for player_id, action_data in actions.items():
            if action_data["role"] == Role.DETECTIVE:
                checked_player = action_data["target"]
                checked_role = state["roles"].get(checked_player)
                results["investigated"] = {
                    "player": checked_player,
                    "is_mafia": checked_role == Role.MAFIA,
                }

        # Применяем результаты
        if results["killed"]:
            state["alive_players"].discard(results["killed"])

        # Очищаем ночные действия
        state["night_actions"] = {}

        return results


class PhaseManager:
    def __init__(self, logic: GameLogic):
        self.logic = logic
        self.phase_timers: Dict[str, any] = {}  # game_id -> timer

    async def start_game(self, game_id: str, players: List[str]) -> GamePhaseChanged:
        """Начало новой игры"""
        self.logic.create_game(game_id, players)
        return GamePhaseChanged(game_id=game_id, phase=GamePhase.LOBBY.value)

    async def advance_phase(self, game_id: str) -> GamePhaseChanged:
        """Переход к следующей фазе"""
        new_phase = self.logic.advance_phase(game_id)

        # Если это фаза распределения ролей, автоматически распределяем
        if new_phase == GamePhase.ROLE_ASSIGNMENT:
            roles = self.logic.assign_roles(game_id)
            # Здесь должна быть отправка ролей игрокам

        return GamePhaseChanged(game_id=game_id, phase=new_phase.value)

    def get_voice_config(self, game_id: str) -> Dict[str, bool]:
        """Получение конфигурации голоса для текущей фазы"""
        state = self.logic.game_states.get(game_id)
        if not state:
            return {}

        phase = state["phase"]
        phase_config = PHASE_CONFIGS.get(phase)
        if not phase_config:
            return {}

        # Создаем конфигурацию для каждого игрока
        voice_config = {}
        for player_id in state["players"]:
            player_role = state["roles"].get(player_id)
            if player_role:
                can_speak = phase_config.voice_config.get(player_role.value, False)
                voice_config[player_id] = can_speak

        return voice_config
