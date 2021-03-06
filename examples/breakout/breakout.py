import numpy as np
from breakout_env.envs.Breakout import Breakout
from breakout_env.wrappers.observation_wrappers import BreakoutFullObservableStateWrapper
from flloat.base.Symbol import Symbol
from flloat.parser.ldlf import LDLfParser
from gym.spaces import Dict, Discrete, Box, Tuple

from rltg.agents.RLAgent import RLAgent
from rltg.agents.TGAgent import TGAgent
from rltg.agents.brains.TDBrain import Sarsa
from rltg.agents.exploration_policies.RandomPolicy import RandomPolicy
from rltg.agents.feature_extraction import FeatureExtractor, RobotFeatureExtractor
from rltg.agents.temporal_evaluator.TemporalEvaluator import TemporalEvaluator
from rltg.trainer import Trainer

conf = {
    "observation": "number_discretized",
    "bricks_rows": 3,
    'bricks_color': [200, 180, 160, 140, 120, 100][:3],
    'bricks_reward': [6, 5, 4, 3, 2, 1][:2:-1],
    "paddle_speed": 3,
    'paddle_width': 50,
    "ball_speed": [1, 2],
    'max_step': 15000,
    'lifes': 1
}

# world state space
breakout_obs_space = Dict({
    "paddle_x": Discrete(161),
    "ball_x": Discrete(161),
    "ball_y": Discrete(211),
    "bricks_status_matrix": Box(low=0, high=1, shape=(3, 18), dtype=np.uint8)
})


class BreakoutRobotFeatureExtractor(RobotFeatureExtractor):
    def __init__(self):  # , automata_states_len:List[int]=[]):
        """
        Build the Robot Feature Extractor for the Breakout Task.
        As main features, are considered only the x component of the paddle position and the ball coordinates.
        Optionally, can be specified the dimensions of the automaton state space, one for each temporal goal. They will
        be combined with the robot feature space by cartesian product, thanks to the TupleFeatureExtractor.

        :param automata_states_len: a list of integers, representing the number of states for each automaton.
                                    (default: [], i.e. no temporal goal)
        """
        # the input space expected by the feature extractor
        obs_space = breakout_obs_space

        # features considered by the robot in this learning task: (paddle_x, ball_x, ball_y)
        robot_feature_space = (
            obs_space.spaces["paddle_x"],
            obs_space.spaces["ball_x"],
            obs_space.spaces["ball_y"]
        )
        output_space = Tuple(robot_feature_space)

        super().__init__(obs_space, output_space)

    def _extract(self, input, **kwargs):
        tuple_state = (
            input["paddle_x"] // 2,
            input["ball_x"] // 2,
            input["ball_y"] // 2,
        )
        return tuple_state


class BreakoutRowBottomUpGoalFeatureExtractor(FeatureExtractor):
    def __init__(self):
        # the input space expected by the feature extractor
        obs_space = breakout_obs_space

        # the output space is just the matrix representing the bricks status
        output_space = obs_space.spaces["bricks_status_matrix"]

        super().__init__(obs_space, output_space)

    def _extract(self, input, **kwargs):
        return input["bricks_status_matrix"]


class BreakoutRowBottomUpTemporalEvaluator(TemporalEvaluator):
    """Breakout temporal evaluator for delete rows from the bottom to the top"""

    def __init__(self, on_the_fly=False):
        self.row_symbols = [Symbol(r) for r in ["r0", "r1", "r2"]]
        rows = self.row_symbols

        parser = LDLfParser()
        f = parser("<(!r0 & !r1 & !r2)*;(r0 & !r1 & !r2)*;(r0 & r1 & !r2)*; r0 & r1 & r2>tt")
        reward = 10000

        super().__init__(BreakoutRowBottomUpGoalFeatureExtractor(), set(rows), f, reward, on_the_fly=on_the_fly)

    def fromFeaturesToPropositional(self, features):
        """map the matrix bricks status to a propositional formula"""
        matrix = features
        row_status = np.all(matrix == 0.0, axis=1)
        result = set()
        for rs, sym in zip(row_status, reversed(self.row_symbols)):
            if rs:
                result.add(sym)

        return frozenset(result)


def normal_goal():
    env = Breakout(conf)
    env = BreakoutFullObservableStateWrapper(env)

    # observation_space = env.observation_space
    # action_space = env.action_space
    # feat_ext = BreakoutRobotFeatureExtractor()
    # feature_space = feat_ext.output_space
    # print(observation_space, action_space, feature_space)

    agent = RLAgent(BreakoutRobotFeatureExtractor(),
                    RandomPolicy(env.action_space, epsilon_start=1.0, epsilon_end=0.01, decaying_steps=1000000),
                    Sarsa(None, env.action_space, alpha=None, gamma=0.99, nsteps=100))

    return env, agent


def temporal_goal():
    env = Breakout(conf)
    env = BreakoutFullObservableStateWrapper(env)

    # observation_space = env.observation_space
    # action_space = env.action_space
    # robot_feat_ext = BreakoutRobotFeatureExtractor()
    # feature_space = robot_feat_ext.output_space
    # print(observation_space, action_space, feature_space)

    agent = TGAgent(BreakoutRobotFeatureExtractor(),
                    RandomPolicy(env.action_space, epsilon_start=1.0, epsilon_end=0.01, decaying_steps=7500000),
                    Sarsa(None, env.action_space, alpha=None, gamma=0.99, nsteps=200),
                    [BreakoutRowBottomUpTemporalEvaluator()])

    return env, agent


def main():
    env, agent = normal_goal()
    # env, agent = temporal_goal()
    tr = Trainer(
        env, agent,
        n_episodes=20001,
        resume=False,
        eval=False,
        # renderer=Renderer(skip_frame=5),
    )
    tr.main()


main()
