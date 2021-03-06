from flloat.flloat import DFAOTF
from typing import Set, List

from flloat.semantics.pl import PLInterpretation
from flloat.utils import powerset
from pythomata.base.Alphabet import Alphabet
from pythomata.base.DFA import DFA
from pythomata.base.Symbol import Symbol

from rltg.logic.RewardAutomaton import RewardAutomaton
from rltg.logic.RewardAutomatonSimulator import RewardSimulator


class PartialAutomatonSimulator(RewardSimulator):

    def __init__(self, dfaotf:DFAOTF, alphabet:Alphabet, reward, gamma=0.99):

        self.dfaotf   = dfaotf
        self.alphabet = Alphabet({PLInterpretation(set(sym)) for sym in powerset(alphabet.symbols)})
        self.reward   = reward
        self.gamma    = gamma
        self.dfaotf.reset()
        initial_state = self.dfaotf.cur_state

        self.id2state = {0: initial_state}
        self.state2id = {initial_state: 0}

        self.states = {0}
        self.initial_state = 0
        self.transition_function = {}
        self.final_states = set()
        self.failure_states = set()

        # a list of (old_state, label, new_state) to keep track of the sequence of states and labels
        self.trace = []
        self.changed = False

        dfa = DFA(alphabet, frozenset(self.states), self.initial_state, frozenset(self.final_states), self.transition_function)
        self._automaton = RewardAutomaton(dfa, alphabet, dfaotf.f, reward, gamma=gamma)


    def reset(self):
        self.dfaotf.reset()

        # (old state, label, new state) triple
        # for o, i, n in self.trace:
        #     self._update_from_transition(o, i, n)
        # self.trace = []


    def make_transition(self, s:Set[Symbol]):
        i = PLInterpretation(s)
        old_state = self.dfaotf.cur_state
        self.dfaotf.make_transition(i)

        new_state = self.dfaotf.cur_state
        self._update_from_transition(old_state, i, new_state)

        if len(self._automaton.accepting_states) > 0:
            reward = self._automaton.get_immediate_reward(self.state2id[old_state], self.state2id[self.dfaotf.cur_state])
        else:
            if self.is_failed():
                reward = -self.reward
            elif old_state!=new_state:
                # give an optimistic reward to help exploration
                reward = self.reward * 10e-4
            else:
                reward = 0


        return reward

    def get_immediate_reward(self, q, q_prime):
        # q_id = self.id2state[q]
        # q_prime_id = self.id2state[q_prime]
        # return self._automaton.get_immediate_reward(q_id, q_prime_id)
        return self._automaton.get_immediate_reward(q, q_prime)

    def is_failed(self):
        return self.dfaotf.cur_state == frozenset()

    def is_true(self):
        return self.dfaotf.is_true()

    def word_acceptance(self, word: List[Symbol]):
        return self.dfaotf.word_acceptance([PLInterpretation(c) for c in word])

    def _update_from_transition(self, old_state, label, new_state):
        old_state_id = self._add_state(old_state)
        new_state_id = self._add_state(new_state)

        self.transition_function.setdefault(old_state_id, {})[label] = new_state_id
        if self.is_failed():
            self.failure_states.add(new_state_id)
        elif self.is_true():
            self.final_states.add(new_state_id)

        dfa = DFA(self.alphabet, frozenset(self.states), self.initial_state, frozenset(self.final_states),
                  self.transition_function)
        self._automaton = RewardAutomaton(dfa, self.alphabet, self.dfaotf.f, self.reward, gamma=self.gamma)
        # k = len(self._automaton.failure_states)
        # s = self._automaton.failure_states.difference(self.states.difference(self.failure_states))
        # self._automaton.failure_states = s
        # cc = len(self._automaton.failure_states)
        # if k != cc:
        #     pass
        #     print("HAHA", k, cc)

    def _add_state(self, new_state):
        new_state_id = self.state2id.get(new_state, None)
        if new_state_id is None:
            new_state_id = len(self.states)
            self.states.add(new_state_id)
            self.id2state[new_state_id] = new_state
            self.state2id[new_state] = new_state_id

        return new_state_id

    def get_cur_state(self):
        return self.state2id[self.dfaotf.cur_state]
