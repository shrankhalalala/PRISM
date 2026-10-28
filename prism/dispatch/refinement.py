"""Research-only richer tabular policy; frozen production Q/surrogate unchanged."""
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from prism.dispatch.baseline import validate_observation
from prism.dispatch.evaluation import baseline_action
from prism.dispatch.q_learning import QLearningAgent, ACTION_ORDER


def richer_state(observation, valid):
    validate_observation(observation)
    demand=max(observation.demand_mw,1.)
    gap=(observation.demand_mw-observation.generation_mw)/demand
    return (int(np.digitize(gap,[-.2,-.1,-.05,-.02,0,.02,.05,.1,.2])),
            min(4,int(observation.battery_soc*5)),
            int(np.digitize(observation.reserve_mw/demand,[.02,.1,.25,.5])),
            int(np.digitize(observation.renewable_trend,[-.05,.05])),
            int(observation.fault_present),
            sum(1<<i for i,a in enumerate(ACTION_ORDER) if a in valid))


class StateAwareQLearningAgent(QLearningAgent):
    def __init__(self, config, prior=1.):
        super().__init__(config)
        self.rows={}
        self.prior=prior

    def row(self, observation, valid):
        key=richer_state(observation,valid)
        if key not in self.rows:
            row=np.full(len(ACTION_ORDER),-self.prior)
            row[ACTION_ORDER.index(baseline_action(observation,valid))]=0.
            self.rows[key]=row
        return self.rows[key]

    def action(self, observation, valid_actions):
        if not valid_actions:
            raise ValueError('At least one valid action is required')
        key=richer_state(observation,valid_actions)
        if key not in self.rows:
            return baseline_action(observation,valid_actions)
        row=self.rows[key]
        return max(valid_actions,key=lambda a:(row[ACTION_ORDER.index(a)],-ACTION_ORDER.index(a)))

    def _update(self, observation, action, reward, next_observation, next_valid_actions, terminated):
        # train() records the actual current mask; next mask is never substituted.
        row=self.row(observation,self.current_valid)
        target=reward
        if not terminated:
            following=self.row(next_observation,next_valid_actions)
            target+=self.config.gamma*max(following[ACTION_ORDER.index(a)] for a in next_valid_actions)
        i=ACTION_ORDER.index(action)
        row[i]+=self.config.alpha*(target-row[i])

    def _explore_or_exploit(self,observation,valid_actions,epsilon):
        self.current_valid=valid_actions
        self.row(observation,valid_actions)
        return super()._explore_or_exploit(observation,valid_actions,epsilon)

    def save(self,path,metadata=None):
        Path(path).write_text(json.dumps(dict(algorithm='state_aware_q_research',config=asdict(self.config),prior=self.prior,actions=[a.value for a in ACTION_ORDER],rows=[dict(state=list(k),values=v.tolist()) for k,v in sorted(self.rows.items())],metadata=metadata or {},executable=False),indent=2)+'\n')
